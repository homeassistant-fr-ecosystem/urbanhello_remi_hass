"""Tests for const.py helpers (device info, MAC normalization)."""

from __future__ import annotations

import pytest

from custom_components.urbanhello_remi.const import _normalize_mac, get_device_info


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"),
        ("aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF"),
        ("AA-BB-CC-DD-EE-FF", "AA:BB:CC:DD:EE:FF"),
        ("aabbccddeeff", "AA:BB:CC:DD:EE:FF"),
        ("AABBCCDDEEFF", "AA:BB:CC:DD:EE:FF"),
        ("AA:BB:CC", None),  # too short
        ("AA:BB:CC:DD:EE:FF:00", None),  # too long
        ("GG:HH:II:JJ:KK:LL", None),  # non-hex
        ("not-a-mac", None),
    ],
)
def test_normalize_mac(value, expected):
    """MAC addresses are normalized to canonical form or rejected."""
    assert _normalize_mac(value) == expected


def test_get_device_info_without_mac():
    """No MAC connection is added when macAddress is absent."""
    info = get_device_info(
        "urbanhello_remi",
        "dev1",
        "Rémi",
        {"raw": {"ipv4Address": "1.2.3.4"}},
    )
    connections = dict(info).get("connections", set())
    assert ("ip", "1.2.3.4") in connections
    assert not any(kind == "mac" for kind, _ in connections)


def test_get_device_info_with_mac():
    """A valid MAC address is added as a mac connection."""
    info = get_device_info(
        "urbanhello_remi",
        "dev1",
        "Rémi",
        {
            "raw": {
                "ipv4Address": "1.2.3.4",
                "macAddress": "aa:bb:cc:dd:ee:ff",
            }
        },
    )
    connections = dict(info).get("connections", set())
    assert ("ip", "1.2.3.4") in connections
    assert ("mac", "AA:BB:CC:DD:EE:FF") in connections


def test_get_device_info_invalid_mac_ignored():
    """An invalid MAC address is not added as a connection."""
    info = get_device_info(
        "urbanhello_remi",
        "dev1",
        "Rémi",
        {"raw": {"macAddress": "not-a-mac"}},
    )
    connections = dict(info).get("connections", set())
    assert not any(kind == "mac" for kind, _ in connections)
