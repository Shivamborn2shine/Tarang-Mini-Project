# TARANG — Implementation Log

## Sprint 0 — Discovery & Instrumentation (2026-11-16)
- Mono-repo scaffold, PRD, Architecture, API Contract, Capability Matrix.
- Canonical Observation Schema v1 (`packages/contracts/observation.schema.json`) and `samples/canonical_observations.json` (3/3 passing).
- Windows WLAN probe (`apps/windows-collector/`) verified live on Windows 11 Build 26300 (`MediaTek MT7921`: `-72 dBm`, `63%`, Channel `161`, 23 nearby networks); 4/4 unit tests passing.
- Android Kotlin + Compose feasibility probe (`apps/android/`) written; physical device run pending JDK/Android SDK/ADB installation.

## Sprint 1 — Backend & Persistence (2026-11-16)
### Completed
- **Infrastructure (`infra/docker-compose.yml`, `.env.example`, `services/api/Dockerfile`):**
  - Configured PostgreSQL 16 + PostGIS (`postgis/postgis:16-3.4`) and FastAPI container services.
- **FastAPI Backend (`services/api/app/`):**
  - SQLAlchemy 2 ORM models (`Project`, `Floorplan`, `Device`, `SurveySession`, `Observation`, `WifiObservation`, `CellObservation`, `SyncBatch`) with coordinate and kind CHECK constraints.
  - Pydantic v2 contract validation (`CanonicalObservationIn`, `BatchIngestRequest`, up to 500 observations/batch).
  - Implemented `/health`, `/api/v1/projects`, `/api/v1/projects/{id}/floorplans`, `/api/v1/devices/register`, `/api/v1/sessions`, `/api/v1/sessions/{id}`, `/api/v1/observations/batch`, `/api/v1/sessions/{id}/observations`, `/api/v1/projects/{id}/summary`, and `/api/v1/projects/{id}/export?format=csv` (with default SSID redaction).
- **Integration Tests (`services/api/tests/test_api_sprint1.py`):**
  - `2/2` pytest integration tests passing:
    - **Sprint 1 Gate:** 500 synthetic observations ingested, retried with identical `batch_id` and observation UUIDs, returning `accepted_count=0`, `duplicate_count=500`, zero duplicate DB rows.
    - Partial batch rejection verified without dropping valid items.

### Limitations
- Integration tests ran against isolated SQLite (`TARANG_DATABASE_URL`) because Docker is not installed on this Windows host; PostgreSQL/PostGIS verification awaits Docker Desktop.
