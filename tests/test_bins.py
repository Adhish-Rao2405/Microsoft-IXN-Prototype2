"""Tests for src/simulation/bins.py – Task 1.3."""

from __future__ import annotations

import pytest

from src.simulation.bins import Bin, BinRegistry


# ---------------------------------------------------------------------------
# Bin data object
# ---------------------------------------------------------------------------


class TestBin:
    def test_initial_count_is_zero(self) -> None:
        b = Bin(bin_id="bin_a", position=[0.6, 0.4, 0.0])
        assert b.count == 0

    def test_increment_adds_one(self) -> None:
        b = Bin(bin_id="bin_a", position=[0.6, 0.4, 0.0])
        b.increment()
        assert b.count == 1

    def test_increment_is_cumulative(self) -> None:
        b = Bin(bin_id="bin_a", position=[0.6, 0.4, 0.0])
        for _ in range(5):
            b.increment()
        assert b.count == 5

    def test_reset_sets_count_to_zero(self) -> None:
        b = Bin(bin_id="bin_a", position=[0.6, 0.4, 0.0])
        b.increment()
        b.increment()
        b.reset()
        assert b.count == 0

    def test_to_dict_shape(self) -> None:
        b = Bin(bin_id="bin_a", position=[0.6, 0.4, 0.0])
        b.increment()
        d = b.to_dict()
        assert d == {"bin_id": "bin_a", "position": [0.6, 0.4, 0.0], "count": 1}

    def test_to_dict_position_is_a_list(self) -> None:
        b = Bin(bin_id="bin_b", position=[0.6, -0.4, 0.0])
        d = b.to_dict()
        assert isinstance(d["position"], list)


# ---------------------------------------------------------------------------
# Default registry initialisation
# ---------------------------------------------------------------------------


class TestBinRegistryDefaults:
    def test_default_registry_has_bin_a_and_bin_b(self) -> None:
        r = BinRegistry()
        assert set(r.bin_ids()) == {"bin_a", "bin_b"}

    def test_bin_a_position(self) -> None:
        r = BinRegistry()
        assert r.get("bin_a").position == pytest.approx([0.6, 0.4, 0.0])

    def test_bin_b_position(self) -> None:
        r = BinRegistry()
        assert r.get("bin_b").position == pytest.approx([0.6, -0.4, 0.0])

    def test_initial_counts_are_zero(self) -> None:
        r = BinRegistry()
        for bid in r.bin_ids():
            assert r.get(bid).count == 0


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


class TestLookup:
    def test_get_known_bin_returns_bin_object(self) -> None:
        r = BinRegistry()
        b = r.get("bin_a")
        assert isinstance(b, Bin)
        assert b.bin_id == "bin_a"

    def test_get_unknown_bin_raises_key_error(self) -> None:
        r = BinRegistry()
        with pytest.raises(KeyError):
            r.get("bin_c")

    def test_get_empty_string_raises_key_error(self) -> None:
        r = BinRegistry()
        with pytest.raises(KeyError):
            r.get("")

    def test_is_valid_true_for_known_bin(self) -> None:
        r = BinRegistry()
        assert r.is_valid("bin_a") is True
        assert r.is_valid("bin_b") is True

    def test_is_valid_false_for_unknown_bin(self) -> None:
        r = BinRegistry()
        assert r.is_valid("bin_c") is False
        assert r.is_valid("") is False

    def test_bin_ids_returns_sorted_list(self) -> None:
        r = BinRegistry()
        assert r.bin_ids() == sorted(r.bin_ids())


# ---------------------------------------------------------------------------
# Count management
# ---------------------------------------------------------------------------


class TestCounts:
    def test_increment_increases_count(self) -> None:
        r = BinRegistry()
        r.increment("bin_a")
        assert r.get("bin_a").count == 1

    def test_increment_unknown_bin_raises_key_error(self) -> None:
        r = BinRegistry()
        with pytest.raises(KeyError):
            r.increment("bin_c")

    def test_counts_snapshot(self) -> None:
        r = BinRegistry()
        r.increment("bin_a")
        r.increment("bin_a")
        r.increment("bin_b")
        snapshot = r.counts()
        assert snapshot["bin_a"] == 2
        assert snapshot["bin_b"] == 1

    def test_counts_does_not_mutate_registry(self) -> None:
        r = BinRegistry()
        snapshot = r.counts()
        snapshot["bin_a"] = 999
        assert r.get("bin_a").count == 0

    def test_reset_all_clears_every_bin(self) -> None:
        r = BinRegistry()
        r.increment("bin_a")
        r.increment("bin_b")
        r.reset_all()
        for bid in r.bin_ids():
            assert r.get(bid).count == 0


# ---------------------------------------------------------------------------
# Custom registry
# ---------------------------------------------------------------------------


class TestCustomRegistry:
    def test_custom_bins_are_registered(self) -> None:
        r = BinRegistry(bins=[
            {"bin_id": "left",  "position": [1.0, 0.5, 0.0]},
            {"bin_id": "right", "position": [1.0, -0.5, 0.0]},
        ])
        assert set(r.bin_ids()) == {"left", "right"}

    def test_custom_bin_position(self) -> None:
        r = BinRegistry(bins=[{"bin_id": "x", "position": [9.0, 8.0, 7.0]}])
        assert r.get("x").position == pytest.approx([9.0, 8.0, 7.0])

    def test_default_bins_absent_in_custom_registry(self) -> None:
        r = BinRegistry(bins=[{"bin_id": "only", "position": [0.0, 0.0, 0.0]}])
        assert not r.is_valid("bin_a")
        assert not r.is_valid("bin_b")


# ---------------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_list_returns_all_bins(self) -> None:
        r = BinRegistry()
        listing = r.to_list()
        ids = [entry["bin_id"] for entry in listing]
        assert set(ids) == {"bin_a", "bin_b"}

    def test_to_list_is_sorted_by_bin_id(self) -> None:
        r = BinRegistry()
        listing = r.to_list()
        ids = [entry["bin_id"] for entry in listing]
        assert ids == sorted(ids)

    def test_to_list_reflects_current_counts(self) -> None:
        r = BinRegistry()
        r.increment("bin_a")
        r.increment("bin_a")
        listing = {entry["bin_id"]: entry for entry in r.to_list()}
        assert listing["bin_a"]["count"] == 2
        assert listing["bin_b"]["count"] == 0

    def test_to_list_entries_have_required_keys(self) -> None:
        r = BinRegistry()
        for entry in r.to_list():
            assert "bin_id" in entry
            assert "position" in entry
            assert "count" in entry
