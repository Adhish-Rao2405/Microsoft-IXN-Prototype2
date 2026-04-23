"""Bin definitions – fixed positions, counts, and lookup for the workcell."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Bin:
    """A single bin: a fixed position and a running drop count."""

    bin_id: str
    position: List[float]  # [x, y, z] centre of the bin
    count: int = field(default=0, compare=False)

    def increment(self) -> None:
        """Record one additional object dropped into this bin."""
        self.count += 1

    def reset(self) -> None:
        """Reset the drop count to zero."""
        self.count = 0

    def to_dict(self) -> dict:
        """Return a JSON-compatible representation."""
        return {
            "bin_id": self.bin_id,
            "position": list(self.position),
            "count": self.count,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Default bin positions (metres, relative to robot base at origin).
_DEFAULT_BINS: List[Dict] = [
    {"bin_id": "bin_a", "position": [0.6,  0.4, 0.0]},
    {"bin_id": "bin_b", "position": [0.6, -0.4, 0.0]},
]


class BinRegistry:
    """
    Deterministic lookup table for workcell bins.

    The registry is initialised with a fixed set of bins (``bin_a`` and
    ``bin_b`` by default).  It tracks how many objects have been dropped into
    each bin and provides safe lookup that raises ``KeyError`` for unknown IDs.

    This class has no dependency on PyBullet, LLMs, or agents.  It is designed
    to be unit-testable in isolation and later read by the workcell state
    abstraction.
    """

    def __init__(
        self,
        bins: Optional[List[Dict]] = None,
    ) -> None:
        """
        Parameters
        ----------
        bins:
            List of ``{"bin_id": str, "position": [x, y, z]}`` dicts.
            Defaults to the two standard workcell bins (``bin_a``, ``bin_b``).
        """
        source = bins if bins is not None else _DEFAULT_BINS
        self._bins: Dict[str, Bin] = {
            entry["bin_id"]: Bin(
                bin_id=entry["bin_id"],
                position=list(entry["position"]),
            )
            for entry in source
        }

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, bin_id: str) -> Bin:
        """Return the ``Bin`` for *bin_id*, raising ``KeyError`` if unknown."""
        try:
            return self._bins[bin_id]
        except KeyError:
            raise KeyError(f"Unknown bin_id {bin_id!r}") from None

    def bin_ids(self) -> List[str]:
        """Return sorted list of all registered bin IDs."""
        return sorted(self._bins.keys())

    def is_valid(self, bin_id: str) -> bool:
        """Return ``True`` if *bin_id* is a known bin."""
        return bin_id in self._bins

    # ------------------------------------------------------------------
    # Count management
    # ------------------------------------------------------------------

    def increment(self, bin_id: str) -> None:
        """Increment the drop count for *bin_id*."""
        self.get(bin_id).increment()

    def counts(self) -> Dict[str, int]:
        """Return a ``{bin_id: count}`` snapshot of all bins."""
        return {bid: b.count for bid, b in self._bins.items()}

    def reset_all(self) -> None:
        """Reset every bin's count to zero."""
        for b in self._bins.values():
            b.reset()

    def to_list(self) -> List[dict]:
        """Return a JSON-compatible list of all bin records."""
        return [self._bins[bid].to_dict() for bid in sorted(self._bins)]
