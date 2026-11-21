from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography, Geometry, WKBElement
from sqlalchemy import DateTime, Index, Text, cast, func, text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.database import Base
from app.schemas import Facility

# Native PostgreSQL enum built from Facility; stores the codes (values), not member names.
facility_enum = ENUM(
    Facility,
    name="facility",
    values_callable=lambda enum: [member.value for member in enum],
)


class Station(Base):
    """A michi-no-eki station, scraped from https://www.michi-no-eki.jp/stations/views/{source_id}."""

    __tablename__ = "stations"
    __table_args__ = (Index("ix_stations_facilities", "facilities", postgresql_using="gin"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("uuidv7()"))
    source_id: Mapped[int] = mapped_column(unique=True)

    name: Mapped[str] = mapped_column(Text)
    prefecture: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    postal_code: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    # Points are (longitude, latitude); GeoAlchemy2 adds the GiST index.
    location: Mapped[WKBElement | None] = mapped_column(Geography("POINT", srid=4326))
    tel: Mapped[str | None] = mapped_column(Text)
    parking: Mapped[str | None] = mapped_column(Text)
    opening_hours: Mapped[str | None] = mapped_column(Text)
    map_code: Mapped[str | None] = mapped_column(Text)

    name_en: Mapped[str | None] = mapped_column(Text)
    prefecture_en: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    address_en: Mapped[str | None] = mapped_column(Text)
    parking_en: Mapped[str | None] = mapped_column(Text)
    opening_hours_en: Mapped[str | None] = mapped_column(Text)

    websites: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    images: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    facilities: Mapped[list[Facility]] = mapped_column(
        ARRAY(facility_enum), server_default=text("'{}'")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Read-only coordinates for StationOut, so API clients never handle geometry formats.
    # Plain `location::geometry` (no typmod) keeps the point's SRID 4326.
    latitude: Mapped[float | None] = column_property(
        func.ST_Y(cast(location, Geometry(geometry_type=None)))
    )
    longitude: Mapped[float | None] = column_property(
        func.ST_X(cast(location, Geometry(geometry_type=None)))
    )
