"""
vec2.py — Immutable 2-D integer vector for grid coordinates.

All grid positions throughout the game use ``Vec2`` so that coordinate
arithmetic is readable and type-safe.

Example::

    pos = Vec2(3, 5)
    neighbour = pos + Vec2(1, 0)   # Vec2(4, 5)
    distance = pos.manhattan(neighbour)   # 1
"""

from __future__ import annotations

import math
from typing import Iterator, Tuple


class Vec2:
    """Immutable 2-D integer vector (column x, row y)."""

    __slots__ = ("_x", "_y")

    def __init__(self, x: int, y: int) -> None:
        object.__setattr__(self, "_x", int(x))
        object.__setattr__(self, "_y", int(y))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def x(self) -> int:
        """Column index (horizontal)."""
        return self._x  # type: ignore[return-value]

    @property
    def y(self) -> int:
        """Row index (vertical)."""
        return self._y  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Vec2 is immutable.")

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self._x + other._x, self._y + other._y)  # type: ignore[operator]

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self._x - other._x, self._y - other._y)  # type: ignore[operator]

    def __mul__(self, scalar: int) -> "Vec2":
        return Vec2(self._x * scalar, self._y * scalar)  # type: ignore[operator]

    def __neg__(self) -> "Vec2":
        return Vec2(-self._x, -self._y)  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Comparison & hashing
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vec2):
            return NotImplemented
        return self._x == other._x and self._y == other._y  # type: ignore[operator]

    def __hash__(self) -> int:
        return hash((self._x, self._y))

    def __lt__(self, other: "Vec2") -> bool:
        """Lexicographic comparison — enables use in ``heapq``."""
        return (self._x, self._y) < (other._x, other._y)  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Representations
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Vec2({self._x}, {self._y})"

    def __iter__(self) -> Iterator[int]:
        """Unpack as ``x, y = vec``."""
        yield self._x  # type: ignore[misc]
        yield self._y  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Distance metrics
    # ------------------------------------------------------------------

    def manhattan(self, other: "Vec2") -> int:
        """Return the Manhattan distance to *other*."""
        return abs(self._x - other._x) + abs(self._y - other._y)  # type: ignore[operator]

    def euclidean(self, other: "Vec2") -> float:
        """Return the Euclidean distance to *other*."""
        dx = self._x - other._x  # type: ignore[operator]
        dy = self._y - other._y  # type: ignore[operator]
        return math.sqrt(dx * dx + dy * dy)

    def chebyshev(self, other: "Vec2") -> int:
        """Return the Chebyshev (8-directional) distance to *other*."""
        return max(abs(self._x - other._x), abs(self._y - other._y))  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def to_tuple(self) -> Tuple[int, int]:
        """Return ``(x, y)`` tuple."""
        return (self._x, self._y)  # type: ignore[return-value]

    def to_pixel(self, tile_size: int) -> Tuple[int, int]:
        """Convert grid coordinates to top-left pixel position."""
        return (self._x * tile_size, self._y * tile_size)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Direction constants (class-level, lazily defined below)
    # ------------------------------------------------------------------

    @classmethod
    def up(cls) -> "Vec2":
        """One step up (y decreases)."""
        return cls(0, -1)

    @classmethod
    def down(cls) -> "Vec2":
        """One step down (y increases)."""
        return cls(0, 1)

    @classmethod
    def left(cls) -> "Vec2":
        """One step left."""
        return cls(-1, 0)

    @classmethod
    def right(cls) -> "Vec2":
        """One step right."""
        return cls(1, 0)

    @classmethod
    def zero(cls) -> "Vec2":
        """Origin vector (0, 0)."""
        return cls(0, 0)

    @classmethod
    def cardinal_directions(cls) -> Tuple["Vec2", "Vec2", "Vec2", "Vec2"]:
        """Return (up, right, down, left) as a 4-tuple."""
        return cls.up(), cls.right(), cls.down(), cls.left()
