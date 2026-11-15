# TARANG — Product Requirements Document (v1.0)

> **Project Definition:** **TARANG** (*Telecommunication Analysis, Radio-frequency Assessment, Network Geomapping*) is an intelligent wireless network surveying and optimization platform that measures, maps, visualizes, and analyzes Wi-Fi and cellular signal strength to identify coverage gaps and improve connectivity.  
> *(PRD v1.0 working name: Network Atlas)*

**Version:** 1.0 | **Date:** 16 November 2026 | **Status:** Implementation-ready proposal  
**Owner:** Shivam | **Project category:** Wi-Fi and cellular signal surveying, mapping, and optimization

> **Product promise:** Walk, measure, map, understand, and improve connectivity. Build trustworthy Wi-Fi and cellular coverage maps from real device observations, even without an internet connection.

## 1. Executive Decision

Build a **local-first, modular survey platform** with an Android native collector, Windows Wi-Fi collector, shared FastAPI backend, and React web dashboard. The MVP measures signal and pinpoints coverage gaps; later versions compare operators, track history, and offer evidence-based optimization suggestions. Do not begin with crowdsourcing, accounts, subscriptions, AI chat, or automatic router control.

## 2. Goals & Non-Goals

| Goal | MVP acceptance target |
|---|---|
| Capture | At least 100 timestamped samples in a 10-minute survey on one supported Android device without a crash |
| Offline | Survey remains usable in airplane-mode-style offline conditions wherever the radios still permit sampling; queued observations sync when connectivity returns |
| Map | Indoor floor-plan points and outdoor coordinates rendered correctly with distinct map modes |
| Reliability | Missing, stale, unavailable, and permission-denied metrics are labeled, not replaced with guesses |
| Data | No duplicate server rows when an upload batch is retried |
| Portability | Download CSV + JSON, generate a readable summary report |
| Privacy | Local-first by default, opt-in synchronization, delete session and associated measurements |

**Non-goals for MVP:** Precise indoor location from GPS; locating cell towers from Cell ID alone; forcing a phone onto an operator/band; iPhone cellular radio diagnostics; guaranteed 1-second radio scans; claiming a heatmap depicts areas not sampled.

## 3. Release Plan

- **M0 (Sprint 0 - Instrumentation Spike):** Real device Android permission + Wi-Fi + LTE/5G probe; Windows WLAN proof; capability matrix; canonical sample payloads.
- **M1 (Sprints 1–3 - Usable Local MVP):** Android scan session, manual indoor placement, outdoor GPS, offline Room queue, FastAPI ingestion, PostgreSQL/PostGIS, React maps, CSV export.
- **M2 (Sprint 4 - Survey Intelligence):** Windows collector; floor-plan calibration; repeated-session comparison; packet-loss/latency tests; PDF report; rule-based optimization suggestions.
- **M3/M4:** Multi-device, operator comparisons, confidence-aware heatmaps, optional consent-based community maps.

## 4. Non-Negotiable Platform Realities

- **Android:** `WifiManager` scan results are subject to permissions and OS throttling; track `observed_at` and `freshness_ms` separately from `recorded_at`. `TelephonyManager` (`CellInfo`, `CellSignalStrength`) values can be null or `CellInfo.UNAVAILABLE` sentinels—convert to `null` with explicit flags. Continuous collection requires a user-initiated Foreground Service.
- **Windows:** `netsh wlan show interfaces` and `netsh wlan show networks mode=bssid` for Sprint 0; Native Wi-Fi (`wlanapi.dll`) later. **Never fabricate RSSI dBm from Windows signal quality `%`.**
- **Signal vs Internet:** Signal power (`dBm`), quality (`%`), link rate (`Mbps`), latency (`ms`), jitter (`ms`), packet loss (`%`), and throughput (`Mbps`) are distinct. Active tests are off by default.
- **Location:** Indoor floor-plan coordinates (`x_norm`, `y_norm` in `[0, 1]`) are not WGS84 latitude/longitude.
