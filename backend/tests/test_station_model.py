from datetime import UTC, datetime
from uuid import UUID

import pytest
from geoalchemy2 import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.models import Station
from app.schemas import Facility, StationOut

IMAGES_19949 = [
    "https://www.michi-no-eki.jp/sites/default/files/styles/stations_main/public/stations/%E9%95%B7%E5%B2%A1%E8%8A%B1%E7%81%AB%E3%83%9F%E3%83%A5%E3%83%BC%E3%82%B8%E3%82%A2%E3%83%A0_%E3%83%89%E3%83%BC%E3%83%A0%E3%82%B7%E3%82%A2%E3%82%BF%E3%83%BC%EF%BC%92_0.jpg?itok=NujrDTgb",
    "https://www.michi-no-eki.jp/sites/default/files/styles/stations_main/public/stations/%E5%A4%A7%E3%81%AF%E3%81%AA%E3%83%93%E3%82%B8%E3%83%A7%E3%83%B3%EF%BC%9A%E9%95%B7%E5%B3%B0%E5%B9%BC%E7%A8%9A%E5%9C%92%E3%81%AE%E9%81%8A%E3%81%B3%E9%A2%A8%E6%99%AF.jpg?itok=DL6JWaFk",
    "https://www.michi-no-eki.jp/sites/default/files/styles/stations_main/public/stations/R8.2%E6%9C%88%E6%92%AE%E5%BD%B1%E3%80%80%E3%83%95%E3%83%BC%E3%83%89%E3%82%B3%E3%83%BC%E3%83%88%EF%BC%88%E5%A4%96%E9%83%A8%E6%8F%90%E4%BE%9B%E7%94%A8%EF%BC%89_0.jpg?itok=H_Q3cvk4",
]
WEBSITES_19949 = [
    "https://nagaoka-hanabikan.niigata.jp/",
    "https://www.instagram.com/nagaoka_hanabikan/",
]
# Available on page 19949 (ATM is shown as unavailable).
FACILITIES_19949 = [
    Facility.baby_bed,
    Facility.restaurant,
    Facility.cafe,
    Facility.ev_charging,
    Facility.wifi,
    Facility.activities,
    Facility.tourist_info,
    Facility.accessible_toilet,
    Facility.shop,
]
TOKYO_STATION = (35.6812, 139.7671)


def point(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def station_19949(**overrides) -> Station:
    fields = {
        "source_id": 19949,
        "name": "ながおか花火館",
        "prefecture": "新潟県",
        "description": "長岡花火を一年中体感できるドームシアターや、花火のゲームが楽しめる展示室など長岡花火の魅力が満載の施設です。",
        "postal_code": "940-2121",
        "address": "新潟県長岡市喜多町707番地",
        "location": point(37.455106, 138.80447),
        "tel": "0258-86-7766",
        "parking": "大型：18台　普通車：264台",
        "opening_hours": "長岡花火ミュージアム10：00～17：30",
        "map_code": None,
        "websites": WEBSITES_19949,
        "images": IMAGES_19949,
        "facilities": FACILITIES_19949,
    }
    return Station(**(fields | overrides))


def minimal_station(source_id: int, **overrides) -> Station:
    return Station(**({"source_id": source_id, "name": "テスト", "prefecture": "東京都"} | overrides))


def save(db: Session, station: Station) -> Station:
    db.add(station)
    db.flush()
    db.refresh(station)
    return station


def nearby(db: Session, lat: float, lng: float, radius_m: float) -> list[int]:
    origin = func.ST_GeogFromText(f"SRID=4326;POINT({lng} {lat})")
    query = select(Station.source_id).where(func.ST_DWithin(Station.location, origin, radius_m))
    return list(db.scalars(query))


# Station identity


def test_own_uuid_assigned_and_source_id_kept(db):
    station = save(db, station_19949())

    assert station.source_id == 19949
    assert isinstance(station.id, UUID)
    assert station.id.version == 7


def test_duplicate_source_id_is_rejected(db):
    save(db, station_19949())
    db.commit()  # releases the test savepoint; the outer transaction still rolls back

    db.add(minimal_station(19949))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    assert db.scalar(select(func.count()).where(Station.source_id == 19949)) == 1


# Required station fields


def test_name_and_prefecture_are_stored(db):
    station = save(db, station_19949())

    assert station.name == "ながおか花火館"
    assert station.prefecture == "新潟県"


def test_missing_name_is_rejected(db):
    db.add(Station(source_id=1, prefecture="新潟県"))

    with pytest.raises(IntegrityError):
        db.flush()


# English translations


def test_untranslated_station_has_null_english_fields(db):
    station = save(db, station_19949())

    assert station.name_en is None
    assert station.prefecture_en is None
    assert station.description_en is None
    assert station.address_en is None
    assert station.parking_en is None
    assert station.opening_hours_en is None
    assert station.name == "ながおか花火館"


def test_translation_is_stored_alongside_japanese(db):
    station = save(db, station_19949())

    station.name_en = "Nagaoka Hanabi-kan"
    station.prefecture_en = "Niigata"
    db.flush()
    db.refresh(station)

    assert station.name_en == "Nagaoka Hanabi-kan"
    assert station.prefecture_en == "Niigata"
    assert station.name == "ながおか花火館"
    assert station.prefecture == "新潟県"


# Optional detail fields


def test_location_is_split_into_postal_code_address_and_point(db):
    station = save(db, station_19949())

    assert station.postal_code == "940-2121"
    assert station.address == "新潟県長岡市喜多町707番地"
    assert station.latitude == pytest.approx(37.455106)
    assert station.longitude == pytest.approx(138.80447)


def test_blank_map_code_is_stored_as_null(db):
    station = save(db, station_19949(map_code=None))

    assert station.map_code is None


def test_parking_and_tel_are_kept_as_shown(db):
    station = save(db, station_19949())

    assert station.parking == "大型：18台　普通車：264台"
    assert station.tel == "0258-86-7766"


# Nearby lookup


def test_station_within_radius_is_found(db):
    save(db, station_19949())

    assert 19949 in nearby(db, 37.4551, 138.8045, 1000)


def test_station_outside_radius_is_not_found(db):
    save(db, station_19949())

    assert 19949 not in nearby(db, *TOKYO_STATION, 1000)


def test_station_without_location_never_matches(db):
    station = save(db, minimal_station(1))

    assert station.latitude is None
    assert 1 not in nearby(db, 37.4551, 138.8045, 20_000_000)  # radius larger than Earth


# Facilities


def test_only_available_facilities_are_listed(db):
    station = save(db, station_19949())

    assert station.facilities == FACILITIES_19949
    assert all(isinstance(facility, Facility) for facility in station.facilities)
    assert Facility.atm not in station.facilities


def test_unknown_facility_code_is_rejected(db):
    with pytest.raises(DataError):
        db.execute(
            text(
                "INSERT INTO stations (source_id, name, prefecture, facilities) "
                "VALUES (1, 'テスト', '東京都', '{helipad}')"
            )
        )


def test_station_can_be_found_by_facility(db):
    save(db, station_19949())
    save(db, minimal_station(1, facilities=[Facility.atm, Facility.park]))
    save(db, minimal_station(2))

    query = select(Station.source_id).where(Station.facilities.contains([Facility.ev_charging]))

    assert list(db.scalars(query)) == [19949]


# Images and websites


def test_image_order_is_preserved(db):
    station = save(db, station_19949())

    assert station.images == IMAGES_19949


def test_multiple_websites_are_kept_in_order(db):
    station = save(db, station_19949())

    assert station.websites == WEBSITES_19949


def test_station_without_images_has_empty_list(db):
    station = save(db, minimal_station(1))

    assert station.images == []
    assert station.websites == []
    assert station.facilities == []


# Last updated time


def test_updated_at_is_set_on_insert_and_refreshed_on_update(db):
    station = save(db, station_19949())
    assert station.updated_at is not None

    long_ago = datetime(2000, 1, 1, tzinfo=UTC)
    station.updated_at = long_ago
    db.flush()
    db.refresh(station)
    assert station.updated_at == long_ago

    station.parking = "大型：20台　普通車：264台"
    db.flush()
    db.refresh(station)

    assert station.updated_at > long_ago


# Output schema against a real row


def test_station_out_reads_a_stored_station(db):
    station = save(db, station_19949())

    out = StationOut.model_validate(station)

    assert out.id == station.id
    assert out.source_id == 19949
    assert out.latitude == pytest.approx(37.455106)
    assert out.facilities == FACILITIES_19949
