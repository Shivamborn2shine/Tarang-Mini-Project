# TARANG — Next Steps

## Immediate Action to Close Sprint 0 Gate
1. **Verify Android Probe on Physical Hardware:**
   - Open `apps/android/` in Android Studio (or install JDK 17 + Android SDK + `adb`) and run the `TARANG Probe` app on your Android phone.
   - Grant location/phone/nearby-Wi-Fi permissions, tap **Run Probe**, and record the observed Wi-Fi and LTE/5G NR fields in `docs/CAPABILITY_MATRIX.md`.
2. **Confirm Open Discovery Questions (PRD Section 18):**
   - Android model/OS version and SIM operator(s) (e.g., Jio/Airtel LTE/NR support).
   - Primary first survey location (home vs college floor plan).
   - Sync preference (LAN-local pairing vs USB manual export fallback).

## Sprint 1 Preview (Backend & Persistence)
- Create `infra/docker-compose.yml` with PostgreSQL 16 + PostGIS.
- Implement `services/api/` (FastAPI + SQLAlchemy 2 + Alembic) for projects, floorplans, devices, sessions, and idempotent `POST /api/v1/observations/batch` (up to 500 observations, zero duplicates on retry).
- Add Pytest integration suite and OpenAPI spec export.
