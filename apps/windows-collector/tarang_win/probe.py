"""Sprint 0 Windows WLAN probe CLI.

Runs `netsh wlan show interfaces` and `netsh wlan show networks mode=bssid`,
emitting canonical `schema_version = 1` observations without fabricating dBm.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from datetime import datetime, timezone

from tarang_win.netsh_parser import (
    WifiInterfaceSnapshot,
    hash_bssid,
    map_band_to_technology,
    parse_netsh_interfaces,
    parse_netsh_networks,
)

DEFAULT_DEVICE_UUID = "71f1a0e8-2b6b-4d40-a205-2df4d47c18a1"
DEFAULT_SESSION_UUID = "d31b5be0-c51b-4b39-bb95-18edc8d85df4"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def interface_to_observation(
    iface: WifiInterfaceSnapshot,
    *,
    session_id: str = DEFAULT_SESSION_UUID,
    device_id: str = DEFAULT_DEVICE_UUID,
    sanitize: bool = True,
    project_salt: str = "tarang-local-sprint0",
) -> dict:
    """Convert a parsed Windows interface snapshot into a canonical v1 observation."""
    now_iso = _utc_now_iso()
    flags: list[str] = []
    if iface.rssi_dbm is None:
        flags.append("rssi_unavailable")
    if sanitize:
        flags.append("sanitized")

    ssid_value = "<REDACTED>" if (sanitize and iface.ssid) else iface.ssid

    return {
        "schema_version": 1,
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "device_id": device_id,
        "kind": "wifi",
        "technology": map_band_to_technology(iface.band, iface.channel),
        "source": "windows_netsh",
        "observed_at": now_iso,
        "recorded_at": now_iso,
        "freshness_ms": 0,
        "location": {"kind": "unknown"},
        "metrics": {
            "rssi_dbm": iface.rssi_dbm,
            "quality_percent": iface.quality_percent,
            "frequency_mhz": None,
            "channel": iface.channel,
            "rx_link_mbps": iface.rx_mbps,
            "tx_link_mbps": iface.tx_mbps,
        },
        "network": {
            "ssid": ssid_value,
            "bssid_hash": hash_bssid(iface.bssid, project_salt=project_salt),
            "is_connected": iface.state == "connected",
        },
        "flags": flags,
    }


def _run_netsh(args: list[str]) -> str:
    proc = subprocess.run(
        ["netsh", "wlan", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.stdout


def run_probe(*, sanitize: bool = True) -> dict:
    """Execute the Sprint 0 Windows WLAN probe and return a structured report."""
    iface_raw = _run_netsh(["show", "interfaces"])
    net_raw = _run_netsh(["show", "networks", "mode=bssid"])

    interfaces = parse_netsh_interfaces(iface_raw)
    nearby = parse_netsh_networks(net_raw)

    observations = [
        interface_to_observation(iface, sanitize=sanitize)
        for iface in interfaces
        if iface.state == "connected"
    ]

    return {
        "probe_timestamp": _utc_now_iso(),
        "interfaces_detected": len(interfaces),
        "nearby_networks_detected": len(nearby),
        "nearby_bssid_exposed": any(n.bssid is not None for n in nearby),
        "observations": observations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TARANG Windows WLAN Sprint 0 Probe")
    parser.add_argument(
        "--no-sanitize",
        action="store_true",
        help="Include raw SSID in output (disabled by default for privacy)",
    )
    args = parser.parse_args(argv)
    report = run_probe(sanitize=not args.no_sanitize)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
