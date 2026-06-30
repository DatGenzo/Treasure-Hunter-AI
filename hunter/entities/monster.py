"""
monster.py — Monster entity representing patrols and chasing behaviors on the map.
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

import pygame

from config.settings import HP_RED, HP_GREEN, TILE_SIZE
from entities.base_entity import Entity
from maps.tilemap import TileMap
from utils.vec2 import Vec2

logger = logging.getLogger(__name__)


class Monster(Entity):
    """A hostile patrol/chase monster that can initiate combat.

    Args:
        col:         Starting grid column.
        row:         Starting grid row.
        tilemap:     The active TileMap.
        patrol_path: List of grid coordinates (col, row) to patrol.
    """

    def __init__(
        self,
        col: int,
        row: int,
        tilemap: TileMap,
        patrol_path: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        super().__init__(col, row, tilemap)
        self.hp = 50
        self.max_hp = 50
        self.detection_radius = 5  # grid cells

        # Patrol variables
        self.patrol_path = patrol_path or [(col, row)]
        self._patrol_idx = 0

        # State machine
        # States: "PATROL", "CHASE", "ATTACK"
        self.state = "PATROL"

        # Movement interpolation
        self._is_moving = False
        self._target_col = col
        self._target_row = row
        self.move_accumulator = 0.0
        self.speed = 2.0  # slightly slower than player

        # Eye angle for animation
        self._pulse = 0.0

    @property
    def grid_pos(self) -> Tuple[int, int]:
        return self._col, self._row

    def detect_player(self, player_pos: Tuple[int, int]) -> bool:
        """Check if player is within detection radius (Manhattan distance)."""
        dist = abs(self._col - player_pos[0]) + abs(self._row - player_pos[1])
        return dist <= self.detection_radius

    def _move_towards(self, target_col: int, target_row: int, dt: float) -> None:
        """Move one grid cell closer to the target cell."""
        if self._is_moving:
            return

        dx, dy = 0, 0
        if target_col > self._col:
            dx = 1
        elif target_col < self._col:
            dx = -1
        elif target_row > self._row:
            dy = 1
        elif target_row < self._row:
            dy = -1

        if dx != 0 or dy != 0:
            tc = self._col + dx
            tr = self._row + dy
            if self._tilemap.is_walkable(tc, tr):
                self._target_col = tc
                self._target_row = tr
                self._is_moving = True
                self.move_accumulator = 0.0

    def update_ai(self, dt: float, player_pos: Tuple[int, int], tilemap: TileMap) -> None:
        """Process Monster AI states: PATROL, CHASE, ATTACK."""
        self._pulse += dt * 5.0
        
        # 1. Update movement interpolation
        if self._is_moving:
            cost = self._tilemap.move_cost(self._target_col, self._target_row)
            effective_speed = self.speed / cost
            self.move_accumulator += effective_speed * dt

            if self.move_accumulator >= 1.0:
                self._col = self._target_col
                self._row = self._target_row
                self._is_moving = False
            else:
                return  # Continue sliding

        # 2. State checks
        dist_to_player = abs(self._col - player_pos[0]) + abs(self._row - player_pos[1])
        
        if dist_to_player <= 1:
            self.state = "ATTACK"
        elif self.detect_player(player_pos):
            self.state = "CHASE"
        else:
            self.state = "PATROL"

        # 3. State action execution
        if self.state == "CHASE":
            self._move_towards(player_pos[0], player_pos[1], dt)
        elif self.state == "PATROL":
            if self.patrol_path:
                target = self.patrol_path[self._patrol_idx]
                if self._col == target[0] and self._row == target[1]:
                    # Advance target index
                    self._patrol_idx = (self._patrol_idx + 1) % len(self.patrol_path)
                    target = self.patrol_path[self._patrol_idx]
                self._move_towards(target[0], target[1], dt)

    def update(self, dt: float) -> None:
        """Abstract update hook: handles slide ticks."""
        # Note: GameScene calls update_ai with player position instead of raw update
        pass

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Render a scary red monster with glowing eyes and an HP bar."""
        if not self.active:
            return

        # Calculate current world pixel position
        col_f = self._col
        row_f = self._row
        if self._is_moving:
            col_f = self._col + (self._target_col - self._col) * self.move_accumulator
            row_f = self._row + (self._target_row - self._row) * self.move_accumulator

        px = col_f * TILE_SIZE + TILE_SIZE // 2 - camera_offset.x
        py = row_f * TILE_SIZE + TILE_SIZE // 2 - camera_offset.y

        # Draw main scary body
        r = TILE_SIZE // 2 - 2
        pygame.draw.circle(surface, (180, 20, 20), (int(px), int(py)), r)

        # Pulsing glowing eyes
        eye_pulse = 2 + int(2 * abs(math.sin(self._pulse)))
        pygame.draw.circle(surface, (255, 230, 0), (int(px - 6), int(py - 4)), eye_pulse)
        pygame.draw.circle(surface, (255, 230, 0), (int(px + 6), int(py - 4)), eye_pulse)

        # Draw simple scary mouth
        pygame.draw.line(surface, (10, 10, 10), (int(px - 8), int(py + 6)), (int(px + 8), int(py + 6)), 2)

        # Render HP bar above monster
        hp_y = py - r - 8
        bar_w = TILE_SIZE
        bar_h = 4
        pygame.draw.rect(surface, HP_RED, (px - bar_w // 2, hp_y, bar_w, bar_h))
        
        ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, HP_GREEN, (px - bar_w // 2, hp_y, int(bar_w * ratio), bar_h))
