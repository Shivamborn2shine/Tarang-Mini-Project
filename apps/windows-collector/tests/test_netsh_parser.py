"""Unit tests for TARANG Windows netsh parser and canonical observation builder."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

COLLECTOR_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(COLLECTOR_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from tarang_win.netsh_parser import (  # noqa: E402
    map_band_to_technology,
    parse_netsh_interfaces,
    parse_netsh_networks,
)
from tarang_win.probe import interface_to_observation  # noqa: E402
from validate_contracts import validate_observation_structural  # noqa: E402

SAMPLE_WITH_RSSI = """
There is 1 interface on the system:

    Name                   : Wi-Fi
    Description            : MediaTek MT7921 Wi-Fi 6 802.11ax PCIe Adapter
    State                  : connected
    SSID                   : TestHomeNet
    AP BSSID               : aa:bb:cc:dd:ee:ff
    Band                   : 5 GHz
    Channel                : 161
    Radio type             : 802.11ac
    Receive rate (Mbps)    : 263.3
    Transmit rate (Mbps)   : 260
    Signal                 : 60%
    Rssi                   : -73
"""

SAMPLE_PERCENT_ONLY = """
There is 1 interface on the system:

    Name                   : Wi-Fi
    Description            : Intel(R) Wi-Fi 6 AX201
    State                  : connected
    SSID                   : CampusNet
    AP BSSID               : 11:22:33:44:55:66
    Band                   : 2.4 GHz
    Channel                : 6
    Receive rate (Mbps)    : 144.4
    Transmit rate (Mbps)   : 144.4
    Signal                 : 72%
"""

SAMPLE_NETWORKS_LOCATION_RESTRICTED = """
Interface name : Wi-Fi
There are 1 networks currently visible.

SSID 1 : TestHomeNet
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
"""

SAMPLE_NETWORKS_WITH_BSSID = """
Interface name : Wi-Fi
There are 1 networks currently visible.

SSID 1 : TestHomeNet
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 82%
         Radio type         : 802.11ax
         Band               : 5 GHz
         Channel            : 36
"""


class TestNetshParser(unittest.TestCase):
    def test_parses_both_signal_percent_and_rssi(self) -> None:
        ifaces = parse_netsh_interfaces(SAMPLE_WITH_RSSI)
        self.assertEqual(len(ifaces), 1)
        iface = ifaces[0]
        self.assertEqual(iface.state, "connected")
        self.assertEqual(iface.quality_percent, 60)
        self.assertEqual(iface.rssi_dbm, -73)
        self.assertEqual(iface.channel, 161)
        self.assertEqual(iface.rx_mbps, 263.3)

        obs = interface_to_observation(iface, sanitize=True)
        self.assertEqual(obs["technology"], "wifi_5ghz")
        self.assertEqual(obs["metrics"]["quality_percent"], 60)
        self.assertEqual(obs["metrics"]["rssi_dbm"], -73)
        self.assertEqual(obs["network"]["ssid"], "<REDACTED>")
        self.assertNotIn("rssi_unavailable", obs["flags"])
        self.assertEqual(validate_observation_structural(obs), [])

    def test_never_fabricates_dbm_from_percent_only(self) -> None:
        ifaces = parse_netsh_interfaces(SAMPLE_PERCENT_ONLY)
        self.assertEqual(len(ifaces), 1)
        obs = interface_to_observation(ifaces[0], sanitize=False)
        self.assertEqual(obs["technology"], "wifi_2_4ghz")
        self.assertEqual(obs["metrics"]["quality_percent"], 72)
        self.assertIsNone(obs["metrics"]["rssi_dbm"])
        self.assertIn("rssi_unavailable", obs["flags"])
        self.assertEqual(validate_observation_structural(obs), [])

    def test_parses_location_restricted_and_bssid_networks(self) -> None:
        restricted = parse_netsh_networks(SAMPLE_NETWORKS_LOCATION_RESTRICTED)
        self.assertEqual(len(restricted), 1)
        self.assertIsNone(restricted[0].bssid)

        full = parse_netsh_networks(SAMPLE_NETWORKS_WITH_BSSID)
        self.assertEqual(len(full), 1)
        self.assertEqual(full[0].bssid, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(full[0].quality_percent, 82)
        self.assertEqual(full[0].channel, 36)

    def test_band_mapping(self) -> None:
        self.assertEqual(map_band_to_technology("5 GHz"), "wifi_5ghz")
        self.assertEqual(map_band_to_technology("2.4 GHz"), "wifi_2_4ghz")
        self.assertEqual(map_band_to_technology("6 GHz"), "wifi_6ghz")
        self.assertEqual(map_band_to_technology(None, 6), "wifi_2_4ghz")


if __name__ == "__main__":
    unittest.main()
