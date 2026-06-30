import math
import pygame

from entities.item import Item, ItemType
from maps.tilemap import TileMap
from utils.sprite_utils import get_key_surface
from utils.vec2 import Vec2


class KeyItem(Item):
    """A collectible key required to open doors."""

    def __init__(self, col: int, row: int, tilemap: TileMap) -> None:
        super().__init__(col, row, ItemType.KEY, tilemap)

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw the item with a pixel art key and glowing rings."""
        if not self.active or self.collected:
            return

        wpos = self.world_pos
        screen_x = wpos.x - camera_offset.x
        screen_y = wpos.y - camera_offset.y

        # Dynamic pulsing scale
        base_radius = int(8 * self._pulse_scale)
        color = (253, 203, 0)  # Golden yellow matching the key sprite

        # 1. Draw outer glow (alpha ring 1)
        outer_radius = int(base_radius * 2.2)
        glow_surf1 = pygame.Surface((outer_radius * 2, outer_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf1, (*color, 40), (outer_radius, outer_radius), outer_radius)
        surface.blit(glow_surf1, (screen_x - outer_radius, screen_y - outer_radius))

        # 2. Draw mid glow (alpha ring 2)
        mid_radius = int(base_radius * 1.6)
        glow_surf2 = pygame.Surface((mid_radius * 2, mid_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf2, (*color, 80), (mid_radius, mid_radius), mid_radius)
        surface.blit(glow_surf2, (screen_x - mid_radius, screen_y - mid_radius))

        # 3. Draw pixel-art key (centered and bobbing vertically)
        bob_y = int(3 * math.sin(self._time_elapsed * 5.0))
        key_surf = get_key_surface(scale=1)
        
        kx = int(screen_x - key_surf.get_width() / 2)
        ky = int(screen_y - key_surf.get_height() / 2 + bob_y)
        surface.blit(key_surf, (kx, ky))
