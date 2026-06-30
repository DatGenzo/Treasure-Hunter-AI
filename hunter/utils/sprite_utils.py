"""
sprite_utils.py — Helper utilities for drawing pixel art sprites.
"""

from __future__ import annotations

from typing import Dict
import pygame

_key_surface_cache: Dict[int, pygame.Surface] = {}

def get_key_surface(scale: int = 1) -> pygame.Surface:
    """Pre-render and cache the pixel art key surface at a given scale."""
    if scale in _key_surface_cache:
        return _key_surface_cache[scale]
    
    grid = [
        "......BBBB................",
        "....BBHHHHBB..............",
        "...BHHGGGGGSB.............",
        "..BHHGG...GGSB............",
        ".BHHGG.....GGSBBBBBBBBBBBB",
        ".BHHG.......GGSSHHHHHHHHHB",
        ".BHHG.......GGSSGGGGGGGGGB",
        "..BGGGG...GGSSBBSSSSSSSSSB",
        "...BGGGGGGSSB..BSSB.BSSB..",
        "....BBGGGGSB....BB...BB...",
        "......BBBB................"
    ]
    
    width = len(grid[0])
    height = len(grid)
    
    surf = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
    
    colors = {
        'B': (101, 67, 33),     # Dark brown outline
        'H': (255, 235, 50),    # Light yellow highlight
        'G': (253, 203, 0),     # Main yellow/gold
        'S': (190, 130, 20),    # Shadow gold/orange
    }
    
    for r_idx, row in enumerate(grid):
        for c_idx, char in enumerate(row):
            if char in colors:
                color = colors[char]
                if scale == 1:
                    surf.set_at((c_idx, r_idx), color)
                else:
                    surf.fill(color, (c_idx * scale, r_idx * scale, scale, scale))
                    
    _key_surface_cache[scale] = surf
    return surf
