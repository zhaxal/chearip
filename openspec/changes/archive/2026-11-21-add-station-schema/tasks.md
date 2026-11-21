# Tasks

## 1. Setup

- [x] 1.1 Add `geoalchemy2==0.21.0` to `backend/requirements.txt` and install it. Wire GeoAlchemy2's Alembic helpers (`include_object`, `render_item`, `writer`) into `backend/alembic/env.py`. Verify that `python -c "import geoalchemy2"` runs and that `alembic current` still connects.

## 2. Facility codes and output schema

- [x] 2.1 Add `Facility(StrEnum)` with the 18 codes, and a `FACILITY_LABELS` map from Japanese label to code (from the design table), in `backend/app/schemas.py`. Verify that `len(Facility) == 18` and that every label maps to a code.
- [x] 2.2 Add `StationOut` (`from_attributes=True`, `id: UUID`, `source_id: int`, `facilities: list[Facility]`, `latitude` and `longitude` as nullable floats, and the six `_en` fields as nullable strings) and add `backend/tests/test_station_schema.py`. Verify that `pytest tests/test_station_schema.py` passes for three cases: the station 19949 sample validates, an unknown facility code is rejected, and a missing name is rejected.

## 3. Stations table

- [x] 3.1 Add the `Station` model to `backend/app/models.py` following the design table. It needs:
  - a `uuid` primary key with server default `uuidv7()`, and a unique, not-null `source_id`
  - `facilities` as `ARRAY(ENUM(Facility, name="facility", values_callable=…))` with a GIN index
  - a `location` column (GeoAlchemy2 `Geography("POINT", srid=4326)`) with a GiST index
  - read-only `latitude` and `longitude` column properties via `ST_Y`/`ST_X`
  - nullable `name_en`, `prefecture_en`, `description_en`, `address_en`, `parking_en`, and `opening_hours_en`
  - `updated_at` with a server default and `onupdate`

  Verify that `python -c "from app.models import Station"` runs.
- [x] 3.2 Autogenerate the first Alembic revision. Put `CREATE EXTENSION IF NOT EXISTS postgis` at the top of `upgrade()`. Check that the `facility` enum type, the GIN index, exactly one GiST index, and the array defaults are present, and add anything missing by hand. `downgrade()` must drop the `facility` type after the table, because `drop_table` leaves it behind. Verify that `alembic upgrade head`, then `alembic downgrade base` (after which `\dT facility` in psql shows nothing), then `alembic upgrade head` all succeed against the local DB.
- [x] 3.3 Add a `db` fixture to `backend/tests/conftest.py` that yields a session inside a transaction and rolls it back after each test. Verify that the existing `test_health.py` still passes.
- [x] 3.4 Add `backend/tests/test_station_model.py`. It stores station 19949 and covers every spec scenario:
  - fields read back correctly, including the location as lat `37.455106`, lng `138.80447`
  - image and website order is kept
  - a blank map code is stored as null
  - the English fields are null by default, and a saved `name_en` and `prefecture_en` read back without changing `name` and `prefecture`
  - `id` is assigned by the database as a UUID, and a duplicate `source_id` raises `IntegrityError`
  - facilities read back as `Facility` members, and the raw value `helipad` raises `DataError`
  - looking up `ev_charging` with `@>` returns only the matching stations
  - `ST_DWithin` with 1000 m finds 19949 from `37.4551, 138.8045`, does not find it from Tokyo Station, and never returns a station with no location
  - `updated_at` is set on insert and refreshed on update (set it to 2000-01-01 first, then change another field)

  Verify that the full `pytest` run passes.

## Workflow follow-up

- After review, archive this change. Then propose the scraper change, which fills `stations`.
