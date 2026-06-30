"""
tile.py — Grid tile types and cell data representations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Tuple


class TileType(Enum):
    """Enumeration of all grid cell terrain and feature types."""

    FLOOR = auto()
    WALL = auto()
    MUD = auto()
    WATER = auto()
    EXIT = auto()
    TRAP = auto()
    LAVA = auto()


TILE_COST: Dict[TileType, int] = {
    TileType.FLOOR: 1,
    TileType.WALL: 999999,  # Unwalkable, but represented with a very high cost
    TileType.MUD: 3,
    TileType.WATER: 5,
    TileType.EXIT: 1,
    TileType.TRAP: 2,
    TileType.LAVA: 8,
}

TILE_COLOR: Dict[TileType, Tuple[int, int, int]] = {
    TileType.FLOOR: (60, 50, 40),
    TileType.WALL: (30, 30, 50),
    TileType.MUD: (100, 70, 30),
    TileType.WATER: (30, 60, 120),
    TileType.EXIT: (50, 200, 80),
    TileType.TRAP: (120, 20, 20),   # Dark Red
    TileType.LAVA: (220, 80, 20),   # Orange-Red
}


@dataclass(frozen=True)
class Tile:
    """Immutable data record representing a single grid tile."""

    tile_type: TileType

    @property
    def walkable(self) -> bool:
        """Return True if entities can walk onto this tile."""
        return self.tile_type != TileType.WALL

    @property
    def move_cost(self) -> float:
        """Return the travel cost penalty for this terrain."""
        return float(TILE_COST.get(self.tile_type, 1.0))

    @property
    def color(self) -> Tuple[int, int, int]:
        """Return the representative RGB color for this tile type."""
        return TILE_COLOR.get(self.tile_type, (0, 0, 0))
