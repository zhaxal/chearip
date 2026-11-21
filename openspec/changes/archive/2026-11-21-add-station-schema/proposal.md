# Proposal

## Why

The app needs somewhere to keep michi-no-eki stations before it can scrape, search, or show them. Defining the station data model now gives the scraper (the next change) a fixed target to fill.

## What Changes

- Add a `stations` table and its first Alembic migration. Each row is one michi-no-eki with its own UUID. The numeric id in its official URL (`/stations/views/{id}`) is kept as a unique source id so the same station is never stored twice.
- Store the fields shown on the station page (for example, [19949](https://www.michi-no-eki.jp/stations/views/19949)):
  - name
  - prefecture
  - description
  - postal code, address, and location (a PostGIS geographic point)
  - phone number
  - parking
  - opening hours
  - websites
  - map code
  - image URLs
  - facilities that are available
- Add optional English columns (`_en`) for name, prefecture, description, address, parking, and opening hours. The official site has no English version, so these stay empty until a later translation change fills them.
- Enable the PostGIS extension in the database so stations can be found by distance from a point.
- Define the site's 18 facility types as a fixed set with stable English codes, such as `atm`, `restaurant`, and `ev_charging`.
- Add a Pydantic `StationOut` schema that matches the table. A later API change will return it.

Out of scope:
- The scraper.
- Producing the English translations.
- API endpoints.
- Downloading images.
- The optional page sections (bean, ice cream, and noodle collections, notices, and related articles).

## Capabilities

### New Capabilities
- `station-catalog`: the stored record for a michi-no-eki station, covering its identity, location, contact details, facilities, and images.

### Modified Capabilities
None.

## Impact

- `backend/app/models.py` gets the `Station` model, and `backend/app/schemas.py` gets `StationOut` and the facility enum.
- `backend/alembic/versions/` gets its first migration, which enables the `postgis` extension.
- New dependency: `geoalchemy2`. `backend/alembic/env.py` gets its autogenerate helpers.
