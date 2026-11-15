# TARANG

**T**elecommunication **A**nalysis, **R**adio-frequency **A**ssessment, **N**etwork **G**eomapping  
*(PRD v1.0 working name: Network Atlas)*

TARANG is a local-first, modular wireless network surveying and optimization platform that measures, maps, visualizes, and analyzes Wi-Fi and cellular signal strength to identify coverage gaps and improve connectivity—even without an internet connection.

## Repository Structure

```text
tarang/
  README.md
  docs/
    PRD.md                    # Product Requirements Document (v1.0)
    ARCHITECTURE.md           # System architecture, coordinate systems, and ADRs
    API_CONTRACT.md           # v1 REST API & idempotent batch ingest contract
    CAPABILITY_MATRIX.md      # Hardware/OS radio API feasibility matrix (Sprint 0)
    IMPLEMENTATION_LOG.md     # Sprint progress and verification log
    NEXT_STEPS.md             # Upcoming sprint gates and open questions
  apps/
    android/                  # Kotlin + Jetpack Compose + Room collector
    windows-collector/        # Python 3.12+ Windows WLAN probe & collector
    web/                      # React + TypeScript + Vite dashboard (Sprint 3)
  services/
    api/                      # FastAPI + SQLAlchemy 2 + Postgres/PostGIS (Sprint 1)
  packages/
    contracts/                # Canonical JSON Schema (v1) and fixture validators
  infra/                      # Docker Compose for API & PostGIS (Sprint 1)
  samples/                    # Sanitized & synthetic observation fixtures
  scripts/                    # Setup and smoke-test scripts
```

## Current Status: Sprint 0 (Discovery & Instrumentation)

Sprint 0 deliverables:
- Mono-repo scaffold, architecture docs, and capability matrix.
- Canonical Observation Schema v1 (`packages/contracts/observation.schema.json`) with strict unit, freshness, and missing-data semantics.
- Windows WLAN probe (`apps/windows-collector/`) tested on local hardware (`netsh wlan show interfaces` and `netsh wlan show networks mode=bssid`).
- Android sensor feasibility probe (`apps/android/`) with scoped permissions, Wi-Fi & LTE/NR `TelephonyManager` adapters, and sentinel-to-null normalization.

### Quick Start (Windows Probe & Contract Tests)

```powershell
# Run Windows WLAN probe (sanitized output by default)
python -m pip install -e ./apps/windows-collector[dev]
tarang-win-probe --sanitize

# Run Windows collector unit tests
pytest apps/windows-collector/tests

# Validate canonical contracts & sample fixtures
python scripts/validate_contracts.py
```

See `docs/IMPLEMENTATION_LOG.md` and `docs/NEXT_STEPS.md` for full Sprint 0 results and Sprint 1 readiness.
