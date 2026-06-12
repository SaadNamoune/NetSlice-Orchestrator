"""Unit tests for slice logic — no Mininet/Ryu required."""
from __future__ import annotations
import pytest


SLICE_MAP = {
    ("00:00:00:00:00:01", "00:00:00:00:00:03"): "A",
    ("00:00:00:00:00:03", "00:00:00:00:00:01"): "A",
    ("00:00:00:00:00:02", "00:00:00:00:00:04"): "B",
    ("00:00:00:00:00:04", "00:00:00:00:00:02"): "B",
}


def get_slice(src_mac: str, dst_mac: str) -> str | None:
    return SLICE_MAP.get((src_mac, dst_mac))


class TestSliceAssignment:
    def test_h1_h3_in_slice_a(self):
        assert get_slice("00:00:00:00:00:01", "00:00:00:00:00:03") == "A"

    def test_h3_h1_in_slice_a(self):
        assert get_slice("00:00:00:00:00:03", "00:00:00:00:00:01") == "A"

    def test_h2_h4_in_slice_b(self):
        assert get_slice("00:00:00:00:00:02", "00:00:00:00:00:04") == "B"

    def test_cross_slice_not_allowed(self):
        assert get_slice("00:00:00:00:00:01", "00:00:00:00:00:04") is None

    def test_cross_slice_reverse_not_allowed(self):
        assert get_slice("00:00:00:00:00:03", "00:00:00:00:00:02") is None

    def test_unknown_mac_not_allowed(self):
        assert get_slice("aa:bb:cc:dd:ee:ff", "00:00:00:00:00:01") is None
