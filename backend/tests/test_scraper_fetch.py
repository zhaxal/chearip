from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Station
from app.schemas import StationOut
from app.scraper import ScrapeError, StationNotFound, main, new_client, scrape_station
from tests.test_scraper_parse import add_helipad, edited_page, page_19949
from tests.test_station_model import save, station_19949

Handler = Callable[[httpx.Request], httpx.Response]


def mock_client(handler: Handler) -> httpx.Client:
    return new_client(transport=httpx.MockTransport(handler))


def serving(html: str) -> httpx.Client:
    return mock_client(lambda request: httpx.Response(200, text=html))


def stored(db: Session, source_id: int) -> int:
    return db.scalar(select(func.count()).where(Station.source_id == source_id)) or 0


def test_fetched_page_is_stored(db):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text=page_19949())

    station = scrape_station(db, 19949, client=mock_client(handler))

    assert station.source_id == 19949
    assert station.name == "ながおか花火館"
    assert stored(db, 19949) == 1
    assert str(requests[0].url) == "https://www.michi-no-eki.jp/stations/views/19949"
    assert requests[0].headers["user-agent"] == "chearip-scraper/0.1"


def test_missing_page_raises_not_found(db):
    client = mock_client(lambda request: httpx.Response(404))

    with pytest.raises(StationNotFound, match=r"\b1\b") as error:
        scrape_station(db, 1, client=client)

    assert error.value.source_id == 1
    assert stored(db, 1) == 0


def test_failed_rescrape_keeps_stored_station(db):
    existing = save(
        db,
        station_19949(parking="大型：20台", updated_at=datetime(2000, 1, 1, tzinfo=UTC)),
    )
    before = StationOut.model_validate(existing).model_dump()

    with pytest.raises(ScrapeError, match="ヘリポート"):
        scrape_station(db, 19949, client=serving(edited_page(add_helipad)))

    db.expire_all()
    after = StationOut.model_validate(db.get_one(Station, existing.id)).model_dump()
    assert after == before


# Command line


def test_command_prints_stored_station(db, capsys):
    status = main(["19949"], client=serving(page_19949()), session_factory=lambda: db)

    assert status == 0
    assert capsys.readouterr().out.strip() == "19949 ながおか花火館"
    assert stored(db, 19949) == 1


def test_command_reports_missing_page(db, capsys):
    client = mock_client(lambda request: httpx.Response(404))

    status = main(["1"], client=client, session_factory=lambda: db)

    assert status != 0
    output = capsys.readouterr()
    assert "station 1 not found" in output.err
    assert output.out == ""
