"""Pure-Python parser for Windows `netsh wlan` outputs.

Preserves exact units: Windows `Signal : <N>%` is stored as `quality_percent`
and `Rssi : <-N>` is stored as `rssi_dbm` ONLY when explicitly reported.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class WifiInterfaceSnapshot:
    """Parsed snapshot from `netsh wlan show interfaces`."""

    name: str
    description: str | None = None
    state: str = "unknown"
    ssid: str | None = None
    bssid: str | None = None
    band: str | None = None
    channel: int | None = None
    radio_type: str | None = None
    rx_mbps: float | None = None
    tx_mbps: float | None = None
    quality_percent: int | None = None
    rssi_dbm: int | None = None


@dataclass(slots=True)
class NearbyNetworkSnapshot:
    """Parsed entry from `netsh wlan show networks mode=bssid`."""

    ssid: str | None
    bssid: str | None = None
    quality_percent: int | None = None
    band: str | None = None
    channel: int | None = None
    radio_type: str | None = None
    authentication: str | None = None
    encryption: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


def hash_bssid(bssid: str | None, project_salt: str = "tarang-local-sprint0") -> str | None:
    """Return a 16-char project-scoped SHA-256 prefix for a BSSID, or None."""
    if not bssid:
        return None
    normalized = bssid.strip().lower()
    digest = hashlib.sha256(f"{project_salt}:{normalized}".encode("utf-8")).hexdigest()
    return digest[:16]


def map_band_to_technology(band: str | None, channel: int | None = None) -> str:
    """Map Windows band string or channel number to canonical technology enum."""
    if band:
        b = band.lower().replace(" ", "")
        if "2.4" in b:
            return "wifi_2_4ghz"
        if "6ghz" in b:
            return "wifi_6ghz"
        if "5ghz" in b:
            return "wifi_5ghz"
    if channel is not None:
        if 1 <= channel <= 14:
            return "wifi_2_4ghz"
        if 32 <= channel <= 177:
            return "wifi_5ghz"
    return "wifi_unknown"


def _parse_int(val: str) -> int | None:
    m = re.search(r"-?\d+", val)
    return int(m.group(0)) if m else None


def _parse_float(val: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", val)
    return float(m.group(0)) if m else None


def parse_netsh_interfaces(raw_output: str) -> list[WifiInterfaceSnapshot]:
    """Parse `netsh wlan show interfaces` output into interface snapshots."""
    interfaces: list[WifiInterfaceSnapshot] = []
    current: WifiInterfaceSnapshot | None = None

    for line in raw_output.splitlines():
        if ":" not in line:
            continue
        key_part, val_part = line.split(":", 1)
        key = key_part.strip().lower()
        val = val_part.strip()

        if key == "name":
            if current is not None:
                interfaces.append(current)
            current = WifiInterfaceSnapshot(name=val)
            continue

        if current is None:
            continue

        if key == "description":
            current.description = val
        elif key == "state":
            current.state = val.lower()
        elif key == "ssid":
            current.ssid = val or None
        elif key in ("ap bssid", "bssid"):
            current.bssid = val or None
        elif key == "band":
            current.band = val or None
        elif key == "channel":
            current.channel = _parse_int(val)
        elif key == "radio type":
            current.radio_type = val or None
        elif key.startswith("receive rate"):
            current.rx_mbps = _parse_float(val)
        elif key.startswith("transmit rate"):
            current.tx_mbps = _parse_float(val)
        elif key == "signal":
            current.quality_percent = _parse_int(val)
        elif key == "rssi":
            current.rssi_dbm = _parse_int(val)

    if current is not None:
        interfaces.append(current)

    return interfaces


def parse_netsh_networks(raw_output: str) -> list[NearbyNetworkSnapshot]:
    """Parse `netsh wlan show networks mode=bssid` output."""
    results: list[NearbyNetworkSnapshot] = []
    current_ssid: str | None = None
    current_auth: str | None = None
    current_enc: str | None = None
    current_bssid_entry: NearbyNetworkSnapshot | None = None

    def flush_ssid_only() -> None:
        if current_ssid is not None and current_bssid_entry is None:
            results.append(
                NearbyNetworkSnapshot(
                    ssid=current_ssid or None,
                    authentication=current_auth,
                    encryption=current_enc,
                )
            )

    for line in raw_output.splitlines():
        if ":" not in line:
            continue
        key_part, val_part = line.split(":", 1)
        key = key_part.strip().lower()
        val = val_part.strip()

        if re.match(r"^ssid\s+\d+$", key):
            if current_bssid_entry is not None:
                results.append(current_bssid_entry)
                current_bssid_entry = None
            else:
                flush_ssid_only()
            current_ssid = val or None
            current_auth = None
            current_enc = None
        elif key == "authentication":
            current_auth = val
        elif key == "encryption":
            current_enc = val
        elif re.match(r"^bssid\s+\d+$", key):
            if current_bssid_entry is not None:
                results.append(current_bssid_entry)
            current_bssid_entry = NearbyNetworkSnapshot(
                ssid=current_ssid,
                bssid=val or None,
                authentication=current_auth,
                encryption=current_enc,
            )
        elif current_bssid_entry is not None:
            if key == "signal":
                current_bssid_entry.quality_percent = _parse_int(val)
            elif key == "band":
                current_bssid_entry.band = val
            elif key == "channel":
                current_bssid_entry.channel = _parse_int(val)
            elif key == "radio type":
                current_bssid_entry.radio_type = val

    if current_bssid_entry is not None:
        results.append(current_bssid_entry)
    else:
        flush_ssid_only()

    return results
