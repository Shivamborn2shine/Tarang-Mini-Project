# TARANG — API Contract (v1)

All endpoints are prefixed with `/api/v1` (except `/health`). All timestamps are ISO-8601 UTC (`Z`). All entity IDs are UUIDv4 strings.

## Endpoints

| Verb + Path | Behavior |
|---|---|
| `GET /health` | Process and PostgreSQL/PostGIS health status |
| `POST /api/v1/projects` | Create project (`name`, `map_mode` in `indoor \| outdoor`) |
| `GET /api/v1/projects` | List projects |
| `POST /api/v1/projects/{id}/floorplans` | Upload floor-plan image, dimensions, optional calibration |
| `POST /api/v1/devices/register` | Register random device UUID and capability matrix |
| `POST /api/v1/sessions` | Create survey session and collection settings |
| `PATCH /api/v1/sessions/{id}` | End session or update status |
| `POST /api/v1/observations/batch` | Validate and idempotently ingest up to 500 observations |
| `GET /api/v1/sessions/{id}/observations` | Paginated filtered observations |
| `GET /api/v1/projects/{id}/summary` | Per-metric quality distributions, sample counts, freshness, coverage stats |
| `GET /api/v1/projects/{id}/export?format=csv` | CSV export with units, source, timestamps, location kind, and privacy redaction |

## Canonical Observation Schema (`schema_version = 1`)

Defined formally in `packages/contracts/observation.schema.json`.

Key invariants:
- `id`, `session_id`, `device_id` must be valid UUIDs.
- `observed_at` and `recorded_at` must be ISO-8601 UTC timestamps.
- `kind` is `"wifi"` or `"cellular"`.
- `location.kind` is `"indoor"` (`floorplan_id` UUID, `x_norm`, `y_norm` in `[0, 1]`), `"outdoor"` (`lat`, `lon`, `gps_accuracy_m`), or `"unknown"`.
- Missing or `CellInfo.UNAVAILABLE` metrics are `null` with an explanatory entry in `flags` (e.g. `"unavailable"`, `"unsupported"`, `"stale_scan"`, `"permission_denied"`).
- Windows `quality_percent` (`0..100`) is stored separately from `rssi_dbm` and must never be converted into `dBm`.
