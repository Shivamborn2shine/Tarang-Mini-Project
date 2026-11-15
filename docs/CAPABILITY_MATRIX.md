# TARANG — Hardware & OS Capability Matrix (Sprint 0)

## 1. Windows Machine (Verified Live in Sprint 0)

| Property | Observed Value |
|---|---|
| OS | Microsoft Windows 11 Home Single Language (10.0.26300 Build 26300) |
| Wi-Fi Adapter | MediaTek MT7921 Wi-Fi 6 802.11ax PCIe Adapter |
| `netsh wlan show interfaces` | Supported: exposes `SSID`, `AP BSSID`, `Band` (5 GHz), `Channel` (161), `Radio type` (802.11ac), `Receive rate (Mbps)`, `Transmit rate (Mbps)`, `Signal` (`%`), **and** `Rssi` (`dBm`, e.g., `-73`) |
| `netsh wlan show networks mode=bssid` | Supported: detected 23 nearby networks with BSSIDs (`nearby_bssid_exposed: true`) when Location Services are active |
| Cellular Modem | Not present on this machine (`cellular` capability = `false`) |
| Tooling note | Python 3.12.10 & Node v24.13.0 installed; JDK/Android SDK/ADB not yet installed on this host |

### Windows Metric Honesty Rules
- When `Rssi` is present in `netsh wlan show interfaces`, record `rssi_dbm` as integer dBm and `quality_percent` as integer `%`.
- When `Rssi` is absent (common on some drivers/locales), record `rssi_dbm: null` and `quality_percent: <int>`, and add `"rssi_unavailable"` to `flags`. **Never** compute `rssi_dbm` from `quality_percent`.

## 2. Android Target Device (Pending Physical Device / ADB Run)

| Capability | Android API | Expected Behavior & Constraints |
|---|---|---|
| Wi-Fi Connected Info | `WifiManager` / `ConnectivityManager` (`NetworkCapabilities` + `WifiInfo`) | Requires `ACCESS_FINE_LOCATION` (and `NEARBY_WIFI_DEVICES` on Android 13+); provides RSSI (dBm), frequency (MHz), link speed |
| Wi-Fi Nearby Scan | `WifiManager.getScanResults()` | Subject to OS scan throttling (4 scans / 2 min in foreground on Android 9+); `timestamp` (microseconds since boot) used to compute `freshness_ms` |
| Cellular LTE | `TelephonyManager.allCellInfo` -> `CellInfoLte` | `rsrp`, `rsrq`, `rssnr` (dBm/dB); `CellInfo.UNAVAILABLE` (`2147483647`) normalized to `null` + `"unavailable"` flag |
| Cellular 5G NR | `TelephonyManager.allCellInfo` -> `CellInfoNr` | `ssRsrp`, `ssRsrq`, `ssSinr`; availability varies by modem, Android version, and NSA vs SA mode |
| Outdoor Location | `LocationManager` / Fused Location | Requires `ACCESS_FINE_LOCATION`; records `gps_accuracy_m`; low accuracy triggers `"low_gps_accuracy"` flag |
| Continuous Collection | Foreground Service (`location` + `connectedDevice` / `dataSync` as applicable) | Persistent notification required on Android 14+ |

*To complete the Android row of this matrix, run the Sprint 0 `CapabilityProbeScreen` on the target Android phone (see `docs/NEXT_STEPS.md`).*
