# TARANG — Architecture & Design Decisions

## 1. Core Principles

1. **Local-First & Offline-Capable:** Collectors (Android Room queue, Windows SQLite spool) persist immutable UUID observations locally and sync via idempotent batch uploads when a backend is reachable.
2. **Honest Telemetry:** Never fabricate missing metrics, never convert Windows `quality_percent` (`%`) into `rssi_dbm` (`dBm`), and never blend incompatible technologies or coordinate systems on the same scale.
3. **Freshness Separation:** Every observation distinguishes `observed_at` (when the radio/OS actually measured the signal), `recorded_at` (when the collector sampled it), and `freshness_ms` (`recorded_at - observed_at`, or scan age).
4. **Separate Coordinate Systems:**
   - **Outdoor:** WGS84 (`lat`, `lon`, `gps_accuracy_m`), stored as PostGIS `geography(Point, 4326)`.
   - **Indoor:** Floor-plan normalized coordinates (`floorplan_id`, `x_norm`, `y_norm` in `[0, 1]`).
   - **Unknown:** `location.kind = "unknown"` — preserved in session lists, excluded from spatial heatmaps until placed.
5. **Privacy by Default:** BSSIDs are hashed with a per-project salt (`bssid_hash`) for AP grouping without exposing raw MAC addresses in exports or routine logs.

## 2. System Data Flow

```text
Android Collector (Kotlin/Compose/Room) ──┐
                                          ├──► FastAPI Batch Ingest ──► PostgreSQL + PostGIS
Windows Collector (Python/SQLite) ────────┘                                     │
                                                                                ▼
                                                                 React + TypeScript Dashboard
```

## 3. Architecture Decision Records (ADRs)

### ADR-001: Single FastAPI Monolith + PostgreSQL/PostGIS
- **Decision:** Use a modular FastAPI backend with PostgreSQL 16+ and PostGIS instead of microservices or Supabase for M1.
- **Rationale:** Keeps local-first deployment (`docker compose up`) simple, testable, and free of external cloud dependencies.

### ADR-002: Canonical Observation Schema (`schema_version = 1`)
- **Decision:** Pin a single JSON Schema (`packages/contracts/observation.schema.json`) shared across Python, TypeScript, and Kotlin DTOs.
- **Rationale:** Prevents silent unit drift (e.g., `%` vs `dBm`), enforces UUIDs and ISO-8601 UTC timestamps, and normalizes Android `CellInfo.UNAVAILABLE` sentinels to `null` with explicit `flags`.

### ADR-003: Windows WLAN Adapter Isolation
- **Decision:** Start with `netsh wlan` parsing behind an adapter interface (`WlanScanner`), keeping Native Wi-Fi (`wlanapi.dll` via `ctypes`) as a drop-in replacement.
- **Rationale:** Enables immediate Sprint 0 hardware probing with zero C/C++ build friction while isolating locale-dependent `netsh` parsing.
