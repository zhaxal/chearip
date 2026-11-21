# Design

## Context

The backend already has SQLAlchemy 2, Alembic, and PostgreSQL. `app/models.py` is empty and there are no migrations yet. Local PostgreSQL 18.7 has PostGIS 3.7 available, but the extension isn't enabled in `chearip` yet. Station pages (see the proposal) show:
- a fixed facility strip with 18 icons, each marked on or off
- a gallery with 0 to n images
- an info table (名, 所在地, TEL, 駐車場, 営業時間, ホームページ…, マップコード)
- a Google Maps embed that contains `lat,lng`

The site has no English version: `/stations/english` returns 404, and no page links to English station data.

## Goals / Non-Goals

**Goals:**
- One flat `stations` table that the scraper can fill with a single upsert per page.
- Facility filtering and distance lookups that both run on an index.

**Non-Goals:**
- Parsing parking counts or opening hours into structured values.
- A nearby-search API endpoint. The lookup is a query that a later API change will use.

## Decisions

### Table `stations`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | uuid PK | no | Server default `uuidv7()` (built into PostgreSQL 18). |
| `source_id` | integer, UNIQUE | no | Site id from `/stations/views/{id}`. Upsert key. |
| `name` | text | no | |
| `prefecture` | text | no | For example `新潟県`. |
| `description` | text | yes | |
| `postal_code` | text | yes | `940-2121` |
| `address` | text | yes | Without the postal code. |
| `location` | geography(Point, 4326) | yes | GiST index. Built from the map embed's `lat,lng`. |
| `tel` | text | yes | |
| `parking` | text | yes | Raw text. |
| `opening_hours` | text | yes | Raw text. |
| `map_code` | text | yes | |
| `name_en`, `prefecture_en`, `description_en`, `address_en`, `parking_en`, `opening_hours_en` | text | yes | English versions. Null until translated. |
| `websites` | text[] | no, default `{}` | |
| `images` | text[] | no, default `{}` | Full URLs, including `?itok=`. |
| `facilities` | facility[] | no, default `{}` | Native enum `facility` with the 18 codes. GIN index. |
| `updated_at` | timestamptz | no, default `now()` | ORM `onupdate=now()` |

- **Own UUID as primary key, site id kept as a unique `source_id`.** Our ids and API URLs don't depend on the site's numbering, so a renumbering on the site or a second data source changes nothing for us. The unique constraint still blocks duplicates and gives the scraper its upsert target (`ON CONFLICT (source_id)`).
  - Rejected: the site id as primary key. It would tie our ids to an external system.
  - Rejected: `bigint` identity. The user chose UUID.
  - UUIDv7 rather than v4. It is time-ordered, so B-tree inserts stay local. The database generates it with `uuidv7()`, so the app needs no UUID library.
- **Facilities as an array of the native PostgreSQL enum `facility`, with a GIN index.** The type rejects unknown codes, each value takes 4 bytes, and the schema itself shows the allowed values. Lookups use `facilities @> ARRAY['ev_charging']::facility[]`, and SQLAlchemy adds the cast. A rolled-back test on this stack (SQLAlchemy 2.1.9, psycopg 3.3.9, PostgreSQL 18.7) confirmed three things: values read back as `Facility` members, `contains()` filtering works, and an unknown value is rejected.
  - Rejected: `text[]` with a CHECK constraint. It enforces the same rule, but the code list has to be kept by hand and each element takes more space. Its one advantage is that removing a value is easy, which isn't expected here.
  - Rejected: 18 boolean columns. They make the table wide, and filtering on any combination of facilities is clumsy.
  - Rejected: a lookup table plus a join table. That is a join for no gain, because the set of types is fixed.
  - A Python `Facility(StrEnum)` is the single source of truth for the codes. Both the database enum (`ENUM(Facility, name="facility", values_callable=…)`, which stores values rather than member names) and the Pydantic schema are built from it.
- **Images and websites as arrays on the row, not as child tables.** Images carry no metadata (`alt` is empty) and are always read together with the station.
- **Location as a PostGIS `geography(Point, 4326)` with a GiST index.** Distances come out in metres anywhere in Japan without choosing a projection. A nearby lookup is `ST_DWithin(location, point, radius_m)`, which uses the index.
  - Rejected: two float columns. Distance searches can't use an index, and switching later would mean another migration.
  - Rejected: `geometry(Point, 4326)`. It measures in degrees unless cast to `geography`. With about 1,200 rows, `geography` costs nothing noticeable in speed.
  - The column type comes from GeoAlchemy2. Its Alembic helpers (`include_object`, `render_item`, `writer`) go into `env.py` so autogenerate renders the type and doesn't create the spatial index twice.
- **English as `_en` columns.** Only English is planned. Plain nullable columns are typed, easy to query, and show up clearly in the API and the orval-generated types.
  - Rejected: one `translations` JSONB column keyed by language. The database would check less and the API types would be looser. Revisit if a third language is ever needed.
  - Rejected: a separate translations table. Every read would need a join.
- **Parking and hours kept as raw text.** Their formats vary between stations, so parsing them belongs with the scraper or a later change.
- **`StationOut` (Pydantic, `from_attributes=True`).** It mirrors the table, with `id: UUID`, `source_id: int` (so clients can link to the official page), and `facilities: list[Facility]`. Instead of the raw point it exposes `latitude` and `longitude` floats, which the model reads as `column_property(ST_Y(...))` and `column_property(ST_X(...))`. API clients never handle map-geometry formats. A scraper input schema will be added in that change if it is needed.

### Facility codes

The icon number is the `facilityNN.svg` number on the page.

| # | Site label | Code |
|---|---|---|
| 01 | ATM | `atm` |
| 02 | ベビーベッド | `baby_bed` |
| 03 | レストラン | `restaurant` |
| 04 | 軽食・喫茶 | `cafe` |
| 05 | 宿泊施設 | `lodging` |
| 06 | 温泉施設 | `hot_spring` |
| 07 | キャンプ場等 | `campground` |
| 08 | 公園 | `park` |
| 09 | 展望台 | `observation_deck` |
| 10 | 美術館・博物館 | `museum` |
| 11 | ガソリンスタンド | `gas_station` |
| 12 | EV充電施設 | `ev_charging` |
| 13 | 無線LAN | `wifi` |
| 14 | シャワー | `shower` |
| 15 | 体験施設 | `activities` |
| 16 | 観光案内 | `tourist_info` |
| 17 | 身障者トイレ | `accessible_toilet` |
| 18 | ショップ | `shop` |

## Risks / Trade-offs

- [The site adds a 19th facility] → Add a `Facility` member, plus a hand-written migration with `ALTER TYPE facility ADD VALUE '…'`, because autogenerate doesn't detect enum changes. Removing a value would mean recreating the type; that isn't expected.
- [`onupdate` doesn't fire for Core `INSERT … ON CONFLICT DO UPDATE`] → The scraper's upsert must set `updated_at` explicitly. Note this in that change.
- [Hotlinked image URLs can break when the site changes them] → Accepted for now. Rescraping refreshes them.
- [PostGIS points are stored longitude first, so latitude and longitude are easy to swap] → A model test checks that the station from page 19949 reads back as lat `37.455106`, lng `138.80447`.
- [A rescrape changes the Japanese text, so the English becomes stale] → The translation change has to retranslate when the source text changes. Not handled here.
- [Autogenerate can create the GiST index twice] → Use the GeoAlchemy2 Alembic helpers, and review the generated migration.

## Migration Plan

The first Alembic revision runs `CREATE EXTENSION IF NOT EXISTS postgis`, then creates the `facility` enum type and `stations` with its GIN and GiST indexes. Rollback is `alembic downgrade base`, which drops the table and the `facility` type and leaves the extension in place.
