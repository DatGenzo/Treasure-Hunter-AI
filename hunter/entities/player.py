"""
player.py — Player entity managing input, grid movement, health, inventory, and stats.
"""

from __future__ import annotations

from typing import Any, List, Optional

import pygame

from config.settings import ACCENT_HOVER, PLAYER_MAX_HP, PLAYER_SPEED, TILE_SIZE
from core.event_bus import EventBus, Events
from entities.base_entity import Entity
from entities.item import Item, ItemType
from maps.tilemap import TileMap
from utils.vec2 import Vec2
from systems.inventory_system import Inventory


class Player(Entity):
    """The archaeology adventurer character controlled by the user or AI.

    Args:
        col:     Starting grid column.
        row:     Starting grid row.
        tilemap: The active TileMap.
        bus:     Shared EventBus for publishing collection/movement events.
    """

    def __init__(self, col: int, row: int, tilemap: TileMap, bus: EventBus) -> None:
        super().__init__(col, row, tilemap)
        self._bus = bus

        # Player stats
        self.hp: int = PLAYER_MAX_HP
        self.max_hp: int = PLAYER_MAX_HP
        self.score: int = 0
        self.has_key: bool = False
        self.inventory: Inventory = Inventory()

        # Movement state
        self.speed: float = float(PLAYER_SPEED)
        self.move_accumulator: float = 0.0
        self.facing: str = "S"  # Default facing south

        self._is_moving: bool = False
        self._target_col: int = col
        self._target_row: int = row

    @property
    def is_moving(self) -> bool:
        """Return True if the player is currently sliding between grid cells."""
        return self._is_moving

    @property
    def world_pos(self) -> Vec2:
        """Override world_pos to interpolate smoothly while moving between tiles."""
        if self._is_moving:
            start = self._tilemap.grid_to_world(self._col, self._row)
            target = self._tilemap.grid_to_world(self._target_col, self._target_row)
            t = min(1.0, max(0.0, self.move_accumulator))
            x = int(start.x + (target.x - start.x) * t)
            y = int(start.y + (target.y - start.y) * t)
            return Vec2(x, y)
        return super().world_pos

    def handle_input(self, keys: pygame.key.ScancodeWrapper, tilemap: TileMap, dt: float) -> None:
        """Process manual keyboard controls (WASD) and trigger smooth grid movement.

        Args:
            keys:    The pygame key states array.
            tilemap: The active TileMap.
            dt:      Delta-time in seconds.
        """
        # If currently moving, we advance progress, we don't start a new move yet
        if self._is_moving:
            return

        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -1
            self.facing = "N"
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = 1
            self.facing = "S"
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -1
            self.facing = "W"
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = 1
            self.facing = "E"

        if dx != 0 or dy != 0:
            target_col = self._col + dx
            target_row = self._row + dy

            # Check collision with wall
            if tilemap.is_walkable(target_col, target_row):
                self._target_col = target_col
                self._target_row = target_row
                self._is_moving = True
                self.move_accumulator = 0.0

    def move_in_direction(self, action: str, tilemap: TileMap) -> None:
        """Trigger smooth grid movement in the specified direction action."""
        if self._is_moving:
            return

        dx, dy = 0, 0
        if action == "move_n":
            dy = -1
            self.facing = "N"
        elif action == "move_s":
            dy = 1
            self.facing = "S"
        elif action == "move_w":
            dx = -1
            self.facing = "W"
        elif action == "move_e":
            dx = 1
            self.facing = "E"

        if dx != 0 or dy != 0:
            target_col = self._col + dx
            target_row = self._row + dy

            # Check collision with wall
            if tilemap.is_walkable(target_col, target_row):
                self._target_col = target_col
                self._target_row = target_row
                self._is_moving = True
                self.move_accumulator = 0.0

    def update(self, dt: float) -> None:
        """Advance smooth movement and update animations."""
        if not self.active:
            return

        if self._is_moving:
            # Accumulate progress based on speed and travel cost
            cost = self._tilemap.move_cost(self._target_col, self._target_row)
            # Adjust speed by cost (higher cost = slower movement)
            effective_speed = self.speed / cost
            self.move_accumulator += effective_speed * dt

            if self.move_accumulator >= 1.0:
                # Finalize move
                self._col = self._target_col
                self._row = self._target_row
                self._is_moving = False
                self.move_accumulator = 0.0
                # Publish event
                self._bus.publish(Events.PLAYER_MOVED, pos=Vec2(self._col, self._row))

    def collect_item(self, item: Item) -> None:
        """Process item pick-up: add to inventory, heal or add score, and publish events."""
        if item.collected:
            return

        item.collected = True
        item.active = False
        self.inventory.add_item(item.item_type)
        self.has_key = self.inventory.has_key()

        if item.item_type == ItemType.TREASURE:
            self.score += item.value
            self._bus.publish(Events.TREASURE_COLLECTED, score=self.score)
        elif item.item_type == ItemType.KEY:
            self.score += item.value
            self._bus.publish(Events.KEY_COLLECTED)
        elif item.item_type == ItemType.HEALTH_POTION:
            self.hp = min(self.max_hp, self.hp + item.value)
            self._bus.publish(Events.POTION_USED, hp=self.hp)
            self._bus.publish(Events.PLAYER_HP_CHANGED, hp=self.hp)

        self._bus.publish(Events.ITEM_COLLECTED, item_type=item.item_type, score=self.score)

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Render player body, facing eyes, and HP bar."""
        if not self.active:
            return

        # Body rect
        r = self.rect
        r.x -= camera_offset.x
        r.y -= camera_offset.y

        # Draw body
        pygame.draw.rect(surface, ACCENT_HOVER, r, border_radius=6)
        pygame.draw.rect(surface, (50, 80, 120), r, 2, border_radius=6)

        # Draw eyes based on direction
        eye_color = (30, 30, 45)
        eye_radius = 3
        cx, cy = r.centerx, r.centery

        if self.facing == "N":
            pygame.draw.circle(surface, eye_color, (cx - 6, cy - 8), eye_radius)
            pygame.draw.circle(surface, eye_color, (cx + 6, cy - 8), eye_radius)
        elif self.facing == "S":
            pygame.draw.circle(surface, eye_color, (cx - 6, cy + 6), eye_radius)
            pygame.draw.circle(surface, eye_color, (cx + 6, cy + 6), eye_radius)
        elif self.facing == "W":
            pygame.draw.circle(surface, eye_color, (cx - 8, cy - 4), eye_radius)
            pygame.draw.circle(surface, eye_color, (cx - 8, cy + 4), eye_radius)
        elif self.facing == "E":
            pygame.draw.circle(surface, eye_color, (cx + 8, cy - 4), eye_radius)
            pygame.draw.circle(surface, eye_color, (cx + 8, cy + 4), eye_radius)

        # Draw HP bar above
        hp_bar_width = TILE_SIZE
        hp_bar_height = 4
        hp_x = r.x
        hp_y = r.y - 8

        # Background (red)
        pygame.draw.rect(surface, (200, 50, 50), (hp_x, hp_y, hp_bar_width, hp_bar_height))
        # Foreground (green)
        hp_ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        pygame.draw.rect(surface, (50, 200, 80), (hp_x, hp_y, int(hp_bar_width * hp_ratio), hp_bar_height))

    def take_damage(self, amount: int) -> bool:
        """Decrease player HP by amount. Returns True if alive, False if dead."""
        self.hp = max(0, self.hp - amount)
        self._bus.publish(Events.PLAYER_HP_CHANGED, hp=self.hp)
        if self.hp <= 0:
            self.active = False
            self._bus.publish(Events.GAME_OVER)
            return False
        return True

    def get_game_state_snapshot(self, scene: Optional[Any] = None) -> dict:
        """Return a dictionary snapshot of the current game state."""
        items_state = []
        doors_state = []
        monsters_state = []
        closed_chests_state = []

        fog_grid = None
        puzzle_triggers_state = []
        door_puzzles = {}
        if scene is not None:
            # Real-time state from scene
            for item in getattr(scene, "_items", []):
                if item.active and not item.collected:
                    items_state.append((item.grid_pos[0], item.grid_pos[1], item.item_type.name))
            for door in getattr(scene, "_doors", []):
                doors_state.append((door.grid_pos[0], door.grid_pos[1], door.locked))
                if getattr(door, "puzzle_id", None):
                    door_puzzles[(door.grid_pos[0], door.grid_pos[1])] = door.puzzle_id
            for monster in getattr(scene, "_monsters", []):
                if monster.active:
                    monsters_state.append((monster.grid_pos[0], monster.grid_pos[1], monster.state))
            for trigger in getattr(scene, "_puzzle_triggers", []):
                puzzle_triggers_state.append({
                    "col": trigger.grid_pos[0],
                    "row": trigger.grid_pos[1],
                    "puzzle_id": trigger.puzzle_id,
                    "solved": trigger.solved
                })
            for chest in getattr(scene, "_chests", []):
                if chest.active and chest.state == "CLOSED":
                    closed_chests_state.append((chest.grid_pos[0], chest.grid_pos[1]))
            if getattr(scene, "_fog", None) is not None:
                fog_grid = scene._fog._fog_grid
        else:
            # Fallback to defaults from tilemap
            if self._tilemap:
                for col, row, type_str in self._tilemap.item_spawns:
                    items_state.append((col, row, type_str.upper()))
                for col, row, type_str in self._tilemap.monster_spawns:
                    monsters_state.append((col, row, "PATROL"))

        return {
            "player_pos": self.grid_pos,
            "player_hp": self.hp,
            "player_has_key": self.has_key,
            "player_inventory": {
                "keys": [k.name if hasattr(k, "name") else str(k) for k in self.inventory.keys],
                "treasures": self.inventory.treasures,
                "potions": self.inventory.potions
            },
            "active_items": items_state,
            "doors": doors_state,
            "door_puzzles": door_puzzles,
            "monsters": monsters_state,
            "exit_pos": (self._tilemap.exit_pos.x, self._tilemap.exit_pos.y) if self._tilemap else (0, 0),
            "fog_grid": fog_grid,
            "puzzle_triggers": puzzle_triggers_state,
            "closed_chests": closed_chests_state,
        }
