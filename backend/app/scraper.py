"""Scrape one official michi-no-eki.jp station page into the stations table."""

import argparse
import re
import sys
from collections.abc import Callable, Sequence
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from geoalchemy2 import WKTElement
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Station
from app.schemas import FACILITY_LABELS, Facility, StationIn

STATION_URL = "https://www.michi-no-eki.jp/stations/views/{source_id}"
USER_AGENT = "chearip-scraper/0.1"
TIMEOUT_SECONDS = 30

NAME_PREFIX = "道の駅「"
NAME_SUFFIX = "」"
POSTAL_ADDRESS = re.compile(r"^(\d{3}-\d{4})\s+(.+)$")


class ScrapeError(Exception):
    """The station page can't be turned into a station record."""


class StationNotFound(Exception):
    """The official site has no page for this source id (HTTP 404)."""

    def __init__(self, source_id: int) -> None:
        super().__init__(f"station {source_id} not found: {STATION_URL.format(source_id=source_id)}")
        self.source_id = source_id


def scrape_station(db: Session, source_id: int, client: httpx.Client | None = None) -> Station:
    """Fetch, parse, and store one station, then commit.

    The page is fetched and parsed before anything is written, so any failure leaves
    the DB untouched.
    """
    if client is None:
        with new_client() as own_client:
            html = fetch_page(source_id, own_client)
    else:
        html = fetch_page(source_id, client)
    station = upsert_station(db, parse_station(html, source_id))
    db.commit()
    return station


def new_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """An HTTP client with the scraper's timeout and User-Agent; tests pass a mock transport."""
    return httpx.Client(
        transport=transport,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )


def fetch_page(source_id: int, client: httpx.Client) -> str:
    """The station page's HTML. Raises `StationNotFound` on 404, `httpx.HTTPError` otherwise."""
    response = client.get(STATION_URL.format(source_id=source_id))
    if response.status_code == httpx.codes.NOT_FOUND:
        raise StationNotFound(source_id)
    response.raise_for_status()
    return response.text


def parse_station(html: str, source_id: int) -> StationIn:
    """Parse a station page into a `StationIn`, without any I/O.

    Raises `ScrapeError` for an unknown facility label, and `pydantic.ValidationError`
    when the name or prefecture is missing.
    """
    soup = BeautifulSoup(html, "html.parser")
    info = _info_rows(soup)
    postal_code, address = _split_address(_text(info.get("所在地")))
    latitude, longitude = _map_position(soup)

    # model_validate rather than the constructor: a missing name or prefecture
    # arrives here as None and must fail validation.
    return StationIn.model_validate(
        {
            "source_id": source_id,
            "name": _name(soup),
            "prefecture": _text(soup.select_one(".viewTitle span")),
            "description": _description(soup),
            "postal_code": postal_code,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            # The dd text, never the link: the site's tel: href holds the address.
            "tel": _text(info.get("TEL")),
            "parking": _text(info.get("駐車場")),
            "opening_hours": _text(info.get("営業時間")),
            "map_code": _text(info.get("マップコード")),
            "websites": _websites(info),
            # The thumbnail swiper repeats the same images, so only the main one is read.
            "images": [str(img["src"]) for img in soup.select(".viewGallery__main img[src]")],
            "facilities": _facilities(soup),
        }
    )


def upsert_station(db: Session, data: StationIn) -> Station:
    """Insert the station, or update the stored one with the same source id, in one statement.

    Only the scraped columns are overwritten, so a rescrape keeps the station's id and any
    English values. Nothing is committed.
    """
    values = data.model_dump(exclude={"latitude", "longitude"})
    values["location"] = _point(data.latitude, data.longitude)

    statement = insert(Station).values(**values)
    scraped = {column: statement.excluded[column] for column in values if column != "source_id"}
    statement = statement.on_conflict_do_update(
        index_elements=[Station.source_id],
        # ORM onupdate doesn't fire for a Core upsert, so updated_at is set here.
        set_=scraped | {"updated_at": func.now()},
    ).returning(Station.id)

    station_id = db.execute(statement).scalar_one()
    return db.get_one(Station, station_id, populate_existing=True)


def _point(latitude: float | None, longitude: float | None) -> WKTElement | None:
    if latitude is None or longitude is None:
        return None
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def _text(tag: Tag | None) -> str | None:
    """The tag's text stripped at both ends, or None when it is missing or blank."""
    if tag is None:
        return None
    return tag.get_text().strip() or None


def _info_rows(soup: BeautifulSoup) -> dict[str, Tag]:
    """The info table as dt label -> dd, in page order."""
    rows: dict[str, Tag] = {}
    for row in soup.select(".viewContent .info dl"):
        label, value = row.select_one("dt"), row.select_one("dd")
        if label is not None and value is not None:
            rows[label.get_text().strip()] = value
    return rows


def _name(soup: BeautifulSoup) -> str | None:
    title = _text(soup.select_one(".viewTitle h2"))
    if title is None:
        return None
    return title.removeprefix(NAME_PREFIX).removesuffix(NAME_SUFFIX).strip() or None


def _description(soup: BeautifulSoup) -> str | None:
    tag = soup.select_one(".viewContent .txt")
    if tag is None:
        return None
    for br in tag.select("br"):
        br.replace_with("\n")
    # Each <br /> is followed by a source newline, so empty lines are dropped.
    lines = (line.strip() for line in tag.get_text().split("\n"))
    return "\n".join(line for line in lines if line) or None


def _split_address(text: str | None) -> tuple[str | None, str | None]:
    """所在地 as (postal code, address); without a leading postal code, all of it is the address."""
    if text is None:
        return None, None
    match = POSTAL_ADDRESS.match(text)
    if match is None:
        return None, text
    return match.group(1), match.group(2)


def _websites(info: dict[str, Tag]) -> list[str]:
    websites = []
    for label, value in info.items():
        if not label.startswith("ホームページ"):
            continue
        link = value.select_one("a[href]")
        website = str(link["href"]).strip() if link is not None else _text(value)
        if website:
            websites.append(website)
    return websites


def _facilities(soup: BeautifulSoup) -> list[Facility]:
    """The available facilities; any unknown label in the strip, available or not, is an error."""
    facilities = []
    for item in soup.select(".viewFacility li"):
        label = _text(item.select_one("span"))
        if label is None:
            continue
        facility = FACILITY_LABELS.get(label)
        if facility is None:
            raise ScrapeError(f"unknown facility label: {label}")
        if "off" not in item.get_attribute_list("class"):
            facilities.append(facility)
    return facilities


def _map_position(soup: BeautifulSoup) -> tuple[float | None, float | None]:
    """(latitude, longitude) from the map embed's q=lat,lng; only q is read, never the API key."""
    iframe = soup.select_one(".viewMap iframe[src]")
    if iframe is None:
        return None, None
    query = parse_qs(urlparse(str(iframe["src"])).query).get("q")
    if not query:
        return None, None
    try:
        latitude, longitude = (float(part) for part in query[0].split(","))
    except ValueError:
        return None, None
    return latitude, longitude


def main(
    argv: Sequence[str] | None = None,
    client: httpx.Client | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> int:
    """`python -m app.scraper <source_id>`: scrape one station and print it, or the error."""
    parser = argparse.ArgumentParser(description="Scrape one michi-no-eki.jp station page.")
    parser.add_argument("source_id", type=int, help="the station id in /stations/views/{id}")
    args = parser.parse_args(argv)

    with session_factory() as db:
        try:
            station = scrape_station(db, args.source_id, client=client)
        except (StationNotFound, ScrapeError, ValidationError, httpx.HTTPError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print(f"{station.source_id} {station.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
