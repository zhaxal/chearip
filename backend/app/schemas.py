from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthOut(BaseModel):
    status: Literal["ok"]


class Facility(StrEnum):
    """The 18 facility types on michi-no-eki.jp, in the site's icon order (facility01-18)."""

    atm = "atm"
    baby_bed = "baby_bed"
    restaurant = "restaurant"
    cafe = "cafe"
    lodging = "lodging"
    hot_spring = "hot_spring"
    campground = "campground"
    park = "park"
    observation_deck = "observation_deck"
    museum = "museum"
    gas_station = "gas_station"
    ev_charging = "ev_charging"
    wifi = "wifi"
    shower = "shower"
    activities = "activities"
    tourist_info = "tourist_info"
    accessible_toilet = "accessible_toilet"
    shop = "shop"


# Japanese label shown on the station page -> facility code.
FACILITY_LABELS: dict[str, Facility] = {
    "ATM": Facility.atm,
    "ベビーベッド": Facility.baby_bed,
    "レストラン": Facility.restaurant,
    "軽食・喫茶": Facility.cafe,
    "宿泊施設": Facility.lodging,
    "温泉施設": Facility.hot_spring,
    "キャンプ場等": Facility.campground,
    "公園": Facility.park,
    "展望台": Facility.observation_deck,
    "美術館・博物館": Facility.museum,
    "ガソリンスタンド": Facility.gas_station,
    "EV充電施設": Facility.ev_charging,
    "無線LAN": Facility.wifi,
    "シャワー": Facility.shower,
    "体験施設": Facility.activities,
    "観光案内": Facility.tourist_info,
    "身障者トイレ": Facility.accessible_toilet,
    "ショップ": Facility.shop,
}


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: int
    name: str
    prefecture: str
    description: str | None
    postal_code: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    tel: str | None
    parking: str | None
    opening_hours: str | None
    map_code: str | None
    name_en: str | None
    prefecture_en: str | None
    description_en: str | None
    address_en: str | None
    parking_en: str | None
    opening_hours_en: str | None
    websites: list[str]
    images: list[str]
    facilities: list[Facility]
    updated_at: datetime
