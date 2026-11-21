<!--
Sync Impact Report
==================
Version change: 1.0.0 (uncommitted draft) → 1.0.0 (revised before first commit)
  The earlier 1.0.0 draft was never committed or used by any spec, so this revision is
  treated as the initial ratification rather than a bump.
Modified principles:
  - I. Responsible Scraping → I. Polite Scraping (redefined: sources are scraped in full
    regardless of robots.txt / terms of use; rate limiting and load rules kept)
  - II. Data Provenance & Freshness (added: romanized names stored alongside originals;
    unknown fields shown as unknown)
  - IV. Typed Contracts End-to-End (redefined frontend rules: orval-generated zod schemas
    and TanStack Query hooks with runtime validation; readable operation IDs; TanStack Router)
Added principles:
  - VII. Bilingual & Mobile-First
Added sections: none (Technology Stack & Constraints expanded with audience and new stack)
Removed sections: none
Templates reviewed (not modified by this command):
  - .specify/templates/plan-template.md: ✅ "Constitution Check" gate and
    "Complexity Tracking" table are compatible with these principles
  - .specify/templates/spec-template.md: ✅ no conflicts
  - .specify/templates/tasks-template.md: ✅ no conflicts
Deferred TODOs: none
-->

# Chearip Constitution

## Core Principles

### I. Polite Scraping

Chearip's data comes from third-party sites that offer no API (michi-no-eki.jp,
weekly.at-parking.jp, toku-p.earth-car.com, and any added later). The project has decided to
scrape these sources in full, including paths disallowed by `robots.txt` and regardless of
their terms of use. In return, every scraper MUST keep its load on the source low:

- Send requests to a host one at a time, never in parallel, with a delay between them that is
  configurable per source and defaults to at least 3 seconds.
- Back off on HTTP 429 or 5xx responses, and abort the run after repeated consecutive failures
  rather than retrying in a tight loop.
- Send a descriptive `User-Agent` that names the project.
- Run as a scheduled or manually triggered batch job, never on the path of a user request.
- Re-fetch a page no more often than its data plausibly changes, and prefer incremental runs
  over full re-crawls.

Rationale: heavy load is what gets a scraper blocked or reported. In Japan, a crawler's load
on a public site has led to a police case (Okazaki City Library, 2010). The data only needs
refreshing daily, so slow scraping costs nothing.

### II. Data Provenance & Freshness

- Every stored record MUST carry its `source`, the `source_url` it was scraped from, and a
  `scraped_at` timestamp (UTC).
- Prices MUST be stored as integer JPY together with their unit and period (e.g. per hour,
  overnight maximum, per day). Coordinates MUST be WGS84 latitude/longitude.
- Original Japanese names and addresses MUST be stored as scraped. Normalized, romanized, or
  translated forms are stored alongside them, never in place of them.
- The UI MUST show when data was last updated and link to the source listing.
- A field that no source provides (e.g. whether overnight car sleeping is tolerated at a
  michi-no-eki) MUST be shown as unknown, never guessed or implied.
- A scrape that fails or returns implausible data (e.g. zero results from a source that had
  hundreds) MUST NOT delete or overwrite the last good data.

Rationale: users pick where to spend the night based on this data. Stale or wrong data with no
timestamp or source link sends people to the wrong place after dark.

### III. Source-Isolated Ingestion

- Each data source MUST be a separate scraper module behind a common interface that yields
  validated Pydantic objects in the shared domain schema.
- Fetching (HTTP), parsing (HTML/JSON → objects), and persisting (objects → database) MUST be
  separate steps so each one can be run and tested on its own.
- A failure in one source MUST NOT stop the other sources from ingesting.
- Adding a source or a new feature domain (beyond parking and michi-no-eki) MUST NOT require
  changing existing scrapers.

Rationale: the product is expected to grow beyond its first three sources. Isolation keeps one
site's layout change from breaking the rest.

### IV. Typed Contracts End-to-End

- Backend request and response bodies MUST be declared as Pydantic schemas. The generated
  OpenAPI document is the API contract.
- FastAPI operation IDs MUST be stable and readable (derived from the route function name),
  because they become the names of generated frontend hooks.
- The frontend's API client, TanStack Query hooks, and zod schemas MUST be generated from the
  OpenAPI document with orval, with runtime response validation enabled. Generated files MUST
  NOT be edited by hand; change the backend and regenerate.
- Frontend routing MUST use TanStack Router with typed routes; URL search params MUST be
  validated with zod.
- TypeScript MUST run in `strict` mode; `any` requires an inline justification comment.
- Database schema changes MUST go through Alembic migrations committed with the model change.
  Manual DDL against shared databases is prohibited.

Rationale: a scraped data model changes often. Generating the frontend contract from the
backend means a breaking change fails at build or validation time, not in front of users.

### V. Tested Against Fixtures, Not the Live Web

- Every parser MUST have tests that run against saved HTML/JSON fixtures captured from the
  real source and committed to the repository.
- Automated tests MUST NOT make network requests to scraped sites.
- Every API endpoint MUST have at least one test covering its success path and its main error
  path. Database-backed tests run against a real PostgreSQL + PostGIS instance, not SQLite.
- When a source's markup changes, the fix MUST include a refreshed fixture that reproduces the
  new markup.

Rationale: live-site tests are flaky and add load to the sources. Fixtures make parser behavior
reproducible and turn layout changes into failing tests.

### VI. Simplicity First

- Start with the simplest design that meets the current spec. Additional infrastructure (task
  queues, caches, search engines, extra services) MUST be justified by a measured need recorded
  in the plan's Complexity Tracking table.
- Prefer one backend service, one scheduler process, and one PostgreSQL database until a spec
  demonstrates otherwise.
- Do not build abstractions for features that are not yet specified.

Rationale: this is a small project. Unneeded moving parts cost more in maintenance than they
return.

### VII. Bilingual & Mobile-First

- All user-facing UI text MUST come from translation catalogs. English is the default
  language; Japanese MUST be complete for every shipped string. Hard-coded user-facing strings
  are prohibited.
- Scraped Japanese names and addresses MUST be displayed in the original Japanese with a
  romanized form alongside, generated at ingest time and stored (see Principle II).
- Fixed-vocabulary values from sources (facilities, vehicle types, price periods) MUST be
  mapped to translation keys, not shown as raw scraped text.
- The UI MUST be designed for phones first and be fully usable at 360 px width.

Rationale: users are often foreign travellers, and every source site is Japanese-only. They
plan the night's stop from a phone in the car, and keep the Japanese text to enter into a
sat-nav or show to locals.

## Technology Stack & Constraints

- **Audience**: travellers driving Japan's toll-free roads who sleep in their cars (車中泊).
  Features are judged by whether they help such a traveller find tonight's stop.
- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.x (sync, psycopg 3), Alembic,
  pydantic-settings; tests with pytest. Code lives in `backend/`.
- **Database**: PostgreSQL with PostGIS. Locations MUST be stored as PostGIS points in SRID
  4326 with a spatial index, and distance queries MUST use PostGIS rather than application-side
  math.
- **Scraping**: BeautifulSoup for HTML parsing, APScheduler for scheduled runs, and
  normalize-japanese-addresses for address normalization and geocoding. The plan for the first
  feature that needs it decides between the Python port and the JavaScript original.
- **Frontend**: React with TypeScript, TanStack Router, TanStack Query, zod, orval, Tailwind
  CSS, shadcn/ui, MapLibre GL JS via react-map-gl. Code lives in `frontend/`.
- **Configuration**: all environment-specific values (database URL, CORS origins, scraper
  settings) MUST come from environment variables / `.env`. Secrets and `.env` files MUST NOT be
  committed; `.env.example` documents every variable.
- **API**: all routes are served under the `/api` prefix.

## Development Workflow

- Features follow the Spec Kit flow: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. Each feature's plan MUST pass the Constitution Check before
  implementation begins.
- Work happens on feature branches; nothing is merged unless the full test suite passes.
- Commits that change SQLAlchemy models MUST include the matching Alembic migration.
- Commits that change the API MUST include the regenerated orval client.
- New scrapers MUST include, in the same change: parser fixtures and tests (Principle V) and
  their configured request delay (Principle I).

## Governance

- This constitution supersedes conflicting practices, conventions, and templates. Where a
  template or plan disagrees with it, the constitution wins until it is amended.
- Amendments are made by editing this file in a dedicated change that states the reason,
  updates the version, and sets **Last Amended** to the change date.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle in a
  backward-incompatible way, MINOR for adding a principle or section or materially expanding
  guidance, PATCH for clarifications and wording fixes.
- Compliance is checked at the plan's Constitution Check gate and again at code review. Any
  deviation MUST be justified in the plan's Complexity Tracking table or rejected.

**Version**: 1.0.0 | **Ratified**: 2026-11-21 | **Last Amended**: 2026-11-21
