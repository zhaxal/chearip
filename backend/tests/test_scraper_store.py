from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Station
from app.schemas import StationIn
from app.scraper import parse_station, upsert_station
from tests.test_scraper_parse import page_19949
from tests.test_station_model import save, station_19949

ENGLISH_FIELDS = (
    "name_en",
    "prefecture_en",
    "description_en",
    "address_en",
    "parking_en",
    "opening_hours_en",
)
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)


def parsed_19949() -> StationIn:
    return parse_station(page_19949(), 19949)


def stored_19949(db: Session) -> int:
    return db.scalar(select(func.count()).where(Station.source_id == 19949)) or 0


def test_new_station_is_stored_once(db):
    data = parsed_19949()

    station = upsert_station(db, data)

    assert stored_19949(db) == 1
    for field, value in data.model_dump(exclude={"latitude", "longitude"}).items():
        assert getattr(station, field) == value, field
    assert station.latitude == pytest.approx(37.455106)
    assert station.longitude == pytest.approx(138.80447)


def test_rescrape_updates_station_in_place(db):
    existing = save(db, station_19949(parking="大型：20台", updated_at=LONG_AGO))
    existing_id = existing.id

    station = upsert_station(db, parsed_19949())

    assert stored_19949(db) == 1
    assert station.id == existing_id
    assert station.parking == "大型：18台　普通車：264台"
    assert station.updated_at > LONG_AGO


def test_new_station_has_no_english(db):
    station = upsert_station(db, parsed_19949())

    for field in ENGLISH_FIELDS:
        assert getattr(station, field) is None, field


def test_rescrape_keeps_saved_english(db):
    save(db, station_19949(name_en="Nagaoka Hanabi-kan"))

    station = upsert_station(db, parsed_19949())

    assert station.name_en == "Nagaoka Hanabi-kan"
