"""
tilemap.py — Grid map container holding tile grid and spawn data.
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any

import pygame

from config.settings import TILE_SIZE
from maps.tile import Tile, TileType
from utils.vec2 import Vec2


class TileMap:
    """Represents the 2D grid level layout and handles coordinates/queries.

    Args:
        grid:           2D grid list of Tile objects [row][col].
        spawn_pos:      Starting grid position of the player.
        exit_pos:       Target grid position to complete the level.
        item_spawns:    List of (col, row, item_type_str) for items.
        monster_spawns: List of (col, row, monster_type_str) for monsters.
    """

    def __init__(
        self,
        grid: List[List[Tile]],
        spawn_pos: Vec2,
        exit_pos: Vec2,
        item_spawns: List[Tuple[int, int, str]],
        monster_spawns: List[Tuple[int, int, str]],
        doors_data: List[Dict[str, Any]] = None,
        puzzle_triggers_data: List[Dict[str, Any]] = None,
        traps_data: List[Dict[str, Any]] = None,
        missions_data: List[Dict[str, Any]] = None,
        chest_data: List[Dict[str, Any]] = None,
    ) -> None:
        self._grid = grid
        self._spawn_pos = spawn_pos
        self._exit_pos = exit_pos
        self._item_spawns = item_spawns
        self._monster_spawns = monster_spawns
        self.doors_data = doors_data if doors_data is not None else []
        self.puzzle_triggers_data = puzzle_triggers_data if puzzle_triggers_data is not None else []
        self.traps_data = traps_data if traps_data is not None else []
        self.missions_data = missions_data if missions_data is not None else []
        self.chest_data = chest_data if chest_data is not None else []

        # Grid dimensions
        self._rows = len(grid)
        self._cols = len(grid[0]) if self._rows > 0 else 0

    @property
    def width(self) -> int:
        """Width of the map in columns."""
        return self._cols

    @property
    def height(self) -> int:
        """Height of the map in rows."""
        return self._rows

    @property
    def spawn_pos(self) -> Vec2:
        """Starting grid position for the player."""
        return self._spawn_pos

    @property
    def exit_pos(self) -> Vec2:
        """Target grid position to escape the temple."""
        return self._exit_pos

    @property
    def item_spawns(self) -> List[Tuple[int, int, str]]:
        """List of coordinates and types for item spawns."""
        return self._item_spawns

    @property
    def monster_spawns(self) -> List[Tuple[int, int, str]]:
        """List of coordinates and types for monster spawns."""
        return self._monster_spawns

    def get_tile(self, col: int, row: int) -> Tile:
        """Return the Tile at (col, row). Invalid coords return WALL."""
        if 0 <= col < self._cols and 0 <= row < self._rows:
            return self._grid[row][col]
        return Tile(TileType.WALL)

    def is_walkable(self, col: int, row: int, treat_goal_as_walkable: Optional[Tuple[int, int]] = None) -> bool:
        """Return True if the grid coordinate is within bounds and walkable."""
        if treat_goal_as_walkable and (col, row) == treat_goal_as_walkable:
            return True
        return self.get_tile(col, row).walkable

    def move_cost(self, col: int, row: int) -> float:
        """Return the terrain movement cost at (col, row)."""
        return self.get_tile(col, row).move_cost

    def grid_to_world(self, col: int, row: int) -> Vec2:
        """Convert a grid coordinate to the center pixel world position."""
        x = col * TILE_SIZE + TILE_SIZE // 2
        y = row * TILE_SIZE + TILE_SIZE // 2
        return Vec2(x, y)

    def world_to_grid(self, px: int, py: int) -> Tuple[int, int]:
        """Convert pixel world coordinates to (col, row) grid coordinates."""
        col = int(px // TILE_SIZE)
        row = int(py // TILE_SIZE)
        return col, row

    def neighbors(self, col: int, row: int, treat_goal_as_walkable: Optional[Tuple[int, int]] = None) -> List[Vec2]:
        """Return the walkable 4-directional neighbor grid positions."""
        neighbors_list: List[Vec2] = []
        current = Vec2(col, row)
        for direction in Vec2.cardinal_directions():
            neighbor = current + direction
            if self.is_walkable(neighbor.x, neighbor.y, treat_goal_as_walkable):
                neighbors_list.append(neighbor)
        return neighbors_list

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw the tile map onto the surface using prototype colors."""
        import math
        from maps.tile import TileType
        for r in range(self._rows):
            for c in range(self._cols):
                tile = self.get_tile(c, r)
                # Compute screen position
                rect = pygame.Rect(
                    c * TILE_SIZE - camera_offset.x,
                    r * TILE_SIZE - camera_offset.y,
                    TILE_SIZE,
                    TILE_SIZE,
                )
                if tile.tile_type == TileType.TRAP:
                    # Spikes
                    pygame.draw.rect(surface, (60, 50, 40), rect)
                    # Spikes (dark red) - Draw 2 triangles
                    p1 = (rect.x + 4, rect.y + rect.height - 4)
                    p2 = (rect.x + rect.width // 4 + 2, rect.y + 4)
                    p3 = (rect.x + rect.width // 2, rect.y + rect.height - 4)
                    pygame.draw.polygon(surface, (140, 20, 20), [p1, p2, p3])
                    
                    p1_2 = (rect.x + rect.width // 2, rect.y + rect.height - 4)
                    p2_2 = (rect.x + 3 * rect.width // 4 - 2, rect.y + 4)
                    p3_2 = (rect.x + rect.width - 4, rect.y + rect.height - 4)
                    pygame.draw.polygon(surface, (140, 20, 20), [p1_2, p2_2, p3_2])
                elif tile.tile_type == TileType.LAVA:
                    # Animated lava color
                    ticks = pygame.time.get_ticks()
                    wave = (math.sin(ticks * 0.005 + (c + r) * 0.5) + 1.0) / 2.0
                    red = int(210 + 45 * wave)
                    green = int(40 + 70 * wave)
                    blue = int(10)
                    pygame.draw.rect(surface, (red, green, blue), rect)
                    
                    # Bubbles
                    bubble_radius = int(2 + 3 * wave)
                    bx = rect.x + int(rect.width * ((c * 7 + r * 13) % 10) / 10)
                    by = rect.y + int(rect.height * ((c * 17 + r * 3) % 10) / 10)
                    pygame.draw.circle(surface, (255, 160, 50), (bx, by), bubble_radius)
                else:
                    pygame.draw.rect(surface, tile.color, rect)

                # Draw subtle borders for better grid visibility
                pygame.draw.rect(surface, (20, 20, 30), rect, 1)
