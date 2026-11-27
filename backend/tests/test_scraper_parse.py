from collections.abc import Callable
from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from app.schemas import Facility
from app.scraper import ScrapeError, parse_station
from tests.test_station_model import FACILITIES_19949, IMAGES_19949, WEBSITES_19949

FIXTURE = Path(__file__).parent / "fixtures" / "station_19949.html"


def page_19949() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def edited_page(edit: Callable[[BeautifulSoup], object]) -> str:
    """Page 19949 with `edit` applied to its parsed tree."""
    soup = BeautifulSoup(page_19949(), "html.parser")
    edit(soup)
    return str(soup)


def one(tag: Tag, selector: str) -> Tag:
    found = tag.select_one(selector)
    assert found is not None, selector
    return found


def info_dd(soup: BeautifulSoup, label: str) -> Tag:
    for row in soup.select(".viewContent .info dl"):
        if one(row, "dt").get_text() == label:
            return one(row, "dd")
    raise AssertionError(label)


def add_helipad(soup: BeautifulSoup) -> None:
    """Add an available facility with a label outside the 18 known types."""
    item = soup.new_tag("li")
    label = soup.new_tag("span")
    label.string = "ヘリポート"
    item.append(label)
    one(soup, ".viewFacility ul").append(item)


def test_info_table_and_map():
    station = parse_station(page_19949(), 19949)

    assert station.source_id == 19949
    assert station.name == "ながおか花火館"
    assert station.prefecture == "新潟県"
    assert station.postal_code == "940-2121"
    assert station.address == "新潟県長岡市喜多町707番地"
    assert station.tel == "0258-86-7766"
    assert station.parking == "大型：18台　普通車：264台"
    assert station.latitude == 37.455106
    assert station.longitude == 138.80447


def test_full_opening_hours():
    station = parse_station(page_19949(), 19949)

    assert station.opening_hours is not None
    assert station.opening_hours.startswith("長岡花火ミュージアム10：00～17：30")
    assert station.opening_hours.endswith("とれたて・できたて直売所(農産物販売)10：00～17：30")


def test_websites_in_page_order():
    station = parse_station(page_19949(), 19949)

    assert station.websites == WEBSITES_19949


def test_only_available_facilities():
    station = parse_station(page_19949(), 19949)

    assert station.facilities == FACILITIES_19949
    assert Facility.atm not in station.facilities


def test_description_keeps_three_lines():
    station = parse_station(page_19949(), 19949)

    assert station.description is not None
    lines = station.description.split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("長岡花火を一年中体感できる")
    assert lines[2] == "観光発信の機能も充実しており、最新の市内イベント情報や観光情報が手に入ります。"
    assert "<br" not in station.description


def test_gallery_images_stored_once():
    station = parse_station(page_19949(), 19949)

    assert station.images == IMAGES_19949
    assert len(set(station.images)) == 3


def test_page_without_gallery_has_no_images():
    html = edited_page(lambda soup: one(soup, ".viewGallery").decompose())

    assert parse_station(html, 19949).images == []


def test_blank_map_code_is_null():
    station = parse_station(page_19949(), 19949)

    assert station.map_code is None


def test_address_without_postal_code():
    def drop_postal_code(soup: BeautifulSoup) -> None:
        info_dd(soup, "所在地").string = "新潟県長岡市喜多町707番地"

    html = edited_page(drop_postal_code)

    station = parse_station(html, 19949)

    assert station.postal_code is None
    assert station.address == "新潟県長岡市喜多町707番地"


def test_page_without_map_has_no_location():
    html = edited_page(lambda soup: one(soup, ".viewMap").decompose())

    station = parse_station(html, 19949)

    assert station.latitude is None
    assert station.longitude is None


def test_page_without_title_is_rejected():
    html = edited_page(lambda soup: one(soup, ".viewTitle h2").decompose())

    with pytest.raises(ValidationError):
        parse_station(html, 19949)


def test_unknown_facility_label_is_rejected():
    with pytest.raises(ScrapeError, match="ヘリポート"):
        parse_station(edited_page(add_helipad), 19949)
