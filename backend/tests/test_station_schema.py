from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import FACILITY_LABELS, Facility, StationIn, StationOut


def station_19949(**overrides):
    data = {
        "id": uuid4(),
        "source_id": 19949,
        "name": "ながおか花火館",
        "prefecture": "新潟県",
        "description": "長岡花火を一年中体感できるドームシアターや、花火のゲームが楽しめる展示室など",
        "postal_code": "940-2121",
        "address": "新潟県長岡市喜多町707番地",
        "latitude": 37.455106,
        "longitude": 138.80447,
        "tel": "0258-86-7766",
        "parking": "大型：18台　普通車：264台",
        "opening_hours": "長岡花火ミュージアム10：00～17：30",
        "map_code": None,
        "name_en": None,
        "prefecture_en": None,
        "description_en": None,
        "address_en": None,
        "parking_en": None,
        "opening_hours_en": None,
        "websites": [
            "https://nagaoka-hanabikan.niigata.jp/",
            "https://www.instagram.com/nagaoka_hanabikan/",
        ],
        "images": [],
        "facilities": ["baby_bed", "restaurant", "ev_charging"],
        "updated_at": datetime.now(UTC),
    }
    return data | overrides


def test_there_are_18_facility_codes():
    assert len(Facility) == 18


def test_every_label_maps_to_a_distinct_code():
    assert len(FACILITY_LABELS) == 18
    assert set(FACILITY_LABELS.values()) == set(Facility)


def test_station_19949_sample_validates():
    station = StationOut.model_validate(station_19949())

    assert station.source_id == 19949
    assert station.name == "ながおか花火館"
    assert station.facilities == [Facility.baby_bed, Facility.restaurant, Facility.ev_charging]


def test_unknown_facility_code_is_rejected():
    with pytest.raises(ValidationError):
        StationOut.model_validate(station_19949(facilities=["helipad"]))


def test_missing_name_is_rejected():
    data = station_19949()
    del data["name"]

    with pytest.raises(ValidationError):
        StationOut.model_validate(data)


def station_in_19949(**overrides):
    data = {
        "source_id": 19949,
        "name": "ながおか花火館",
        "prefecture": "新潟県",
        "description": "長岡花火を一年中体感できるドームシアターや、花火のゲームが楽しめる展示室など",
        "postal_code": "940-2121",
        "address": "新潟県長岡市喜多町707番地",
        "latitude": 37.455106,
        "longitude": 138.80447,
        "tel": "0258-86-7766",
        "parking": "大型：18台　普通車：264台",
        "opening_hours": "長岡花火ミュージアム10：00～17：30",
        "map_code": None,
        "websites": [
            "https://nagaoka-hanabikan.niigata.jp/",
            "https://www.instagram.com/nagaoka_hanabikan/",
        ],
        "images": [],
        "facilities": ["baby_bed", "restaurant", "ev_charging"],
    }
    return data | overrides


def test_station_in_19949_sample_validates():
    station = StationIn.model_validate(station_in_19949())

    assert station.source_id == 19949
    assert station.name == "ながおか花火館"
    assert station.facilities == [Facility.baby_bed, Facility.restaurant, Facility.ev_charging]
    assert not {"id", "updated_at", "name_en"} & set(StationIn.model_fields)


def test_station_in_empty_name_is_rejected():
    with pytest.raises(ValidationError):
        StationIn.model_validate(station_in_19949(name=""))


def test_station_in_unknown_facility_code_is_rejected():
    with pytest.raises(ValidationError):
        StationIn.model_validate(station_in_19949(facilities=["helipad"]))
