# TARANG — Implementation Log

## Sprint 0 — Discovery & Instrumentation (2026-11-16)

### Completed
1. **Mono-repo Scaffold & Docs:**
   - Initialized repository structure (`docs/`, `apps/android/`, `apps/windows-collector/`, `apps/web/`, `services/api/`, `packages/contracts/`, `infra/`, `samples/`, `scripts/`).
   - Authored `README.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/API_CONTRACT.md`, and `docs/CAPABILITY_MATRIX.md`.
2. **Canonical Observation Schema (`schema_version = 1`):**
   - Created `packages/contracts/observation.schema.json` enforcing UUIDs, UTC ISO-8601 timestamps, separated `observed_at`/`recorded_at`/`freshness_ms`, discriminated `indoor`/`outdoor`/`unknown` locations, and explicit `flags`.
   - Added `samples/canonical_observations.json` and `scripts/validate_contracts.py` (3/3 samples pass).
3. **Windows WLAN Probe (`apps/windows-collector/`):**
   - Implemented `tarang_win.netsh_parser` and `tarang_win.probe` (`tarang-win-probe`).
   - Verified live on Windows 11 Build 26300 (`MediaTek MT7921 Wi-Fi 6 802.11ax PCIe Adapter`): exposes `Signal` (`63%`), `Rssi` (`-72 dBm`), `Band` (`5 GHz`), `Channel` (`161`), link rates, and 23 nearby networks with BSSIDs.
   - Unit tests (`4/4` passing) verify `%` vs `dBm` separation and no dBm fabrication when `Rssi` is absent.
4. **Android Sensor Feasibility Probe (`apps/android/`):**
   - Created Kotlin + Jetpack Compose project (`CapabilityProbeScreen`, `RadioCapabilityProbe`, `SentinelNormalizer`) with scoped permission requests (`ACCESS_FINE_LOCATION`, `NEARBY_WIFI_DEVICES`, `READ_PHONE_STATE`), `WifiManager` scan freshness, `TelephonyManager` LTE/5G NR cell mapping, and `SentinelNormalizerTest`.

### Known Limitations & Blockers at End of Sprint 0
- **Android Hardware Gate Pending:** `java`, `adb`, and Android SDK are not currently installed on this Windows host, so the Android APK could not be compiled or run on a physical Android phone in this session.
- **Docker / Postgres:** Sprint 1 backend (`services/api/`, `infra/`) is scaffolded as placeholders and intentionally deferred until Sprint 0 Android hardware gate is verified.
