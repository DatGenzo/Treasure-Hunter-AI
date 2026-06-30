"""
settings.py — Global constants and configuration for Treasure Hunter AI.

All magic numbers live here. No other module should hard-code values that
appear in this file.
"""

from __future__ import annotations

import os
from typing import Final, Tuple

# ---------------------------------------------------------------------------
# Window & display
# ---------------------------------------------------------------------------

WINDOW_TITLE: Final[str] = "Treasure Hunter AI"
WINDOW_WIDTH: Final[int] = 1280
WINDOW_HEIGHT: Final[int] = 720
FPS: Final[int] = 60

# Right-side AI panel width (pixels).  Game canvas = WINDOW_WIDTH - PANEL_WIDTH.
PANEL_WIDTH: Final[int] = 320
GAME_WIDTH: Final[int] = WINDOW_WIDTH - PANEL_WIDTH   # 960
GAME_HEIGHT: Final[int] = WINDOW_HEIGHT               # 720

# ---------------------------------------------------------------------------
# Tile grid
# ---------------------------------------------------------------------------

TILE_SIZE: Final[int] = 32          # pixels per tile
GRID_COLS: Final[int] = GAME_WIDTH  // TILE_SIZE   # 30
GRID_ROWS: Final[int] = GAME_HEIGHT // TILE_SIZE   # 22

# ---------------------------------------------------------------------------
# Colour palette  (R, G, B)
# ---------------------------------------------------------------------------

# UI chrome
BLACK:         Final[Tuple[int, int, int]] = (0,   0,   0)
WHITE:         Final[Tuple[int, int, int]] = (255, 255, 255)
DARK_BG:       Final[Tuple[int, int, int]] = (18,  18,  30)
PANEL_BG:      Final[Tuple[int, int, int]] = (22,  22,  38)
PANEL_BORDER:  Final[Tuple[int, int, int]] = (70,  70, 110)
ACCENT:        Final[Tuple[int, int, int]] = (90, 160, 255)
ACCENT_HOVER:  Final[Tuple[int, int, int]] = (120, 190, 255)
TEXT_PRIMARY:  Final[Tuple[int, int, int]] = (220, 220, 235)
TEXT_MUTED:    Final[Tuple[int, int, int]] = (130, 130, 160)
SUCCESS:       Final[Tuple[int, int, int]] = (80,  200, 120)
WARNING:       Final[Tuple[int, int, int]] = (255, 190,  50)
DANGER:        Final[Tuple[int, int, int]] = (220,  60,  60)

# HUD
HP_RED:        Final[Tuple[int, int, int]] = (200,  50,  50)
HP_GREEN:      Final[Tuple[int, int, int]] = (50,  200,  80)
SCORE_GOLD:    Final[Tuple[int, int, int]] = (255, 200,  40)

# Algorithm visualisation — pathfinding
VIS_VISITED:   Final[Tuple[int, int, int]] = (50,  100, 200)   # blue
VIS_FRONTIER:  Final[Tuple[int, int, int]] = (255, 165,   0)   # orange
VIS_SOLUTION:  Final[Tuple[int, int, int]] = (50,  200,  80)   # green
VIS_CURRENT:   Final[Tuple[int, int, int]] = (255, 230,   0)   # yellow
VIS_OPEN:      Final[Tuple[int, int, int]] = (0,   220, 220)   # cyan  (A*)
VIS_CLOSED:    Final[Tuple[int, int, int]] = (140,  60, 200)   # purple (A*)

# Algorithm visualisation — local search
VIS_CANDIDATE: Final[Tuple[int, int, int]] = (255, 140,  0)    # orange gradient
VIS_BEST:      Final[Tuple[int, int, int]] = (50,  200, 80)    # green
VIS_REJECTED:  Final[Tuple[int, int, int]] = (200,  50, 50)    # red fade

# Algorithm visualisation — CSP
VIS_ASSIGNED:  Final[Tuple[int, int, int]] = (50,  200,  80)
VIS_VIOLATION: Final[Tuple[int, int, int]] = (220,  50,  50)

# Algorithm visualisation — belief states
VIS_BELIEF:    Final[Tuple[int, int, int, int]] = (50, 120, 255, 80)  # RGBA

# Fog of war
FOG_COLOUR:    Final[Tuple[int, int, int]] = (10,  10,  20)
FOG_ALPHA:     Final[int] = 200

# ---------------------------------------------------------------------------
# Entity defaults
# ---------------------------------------------------------------------------

PLAYER_MAX_HP:        Final[int]   = 100
PLAYER_SPEED:         Final[int]   = 4     # tiles per second (manual mode)
MONSTER_PATROL_SPEED: Final[int]   = 2
TREASURE_SCORE:       Final[int]   = 50
KEY_SCORE:            Final[int]   = 10
HEALTH_POTION_HEAL:   Final[int]   = 30

# ---------------------------------------------------------------------------
# AI runner defaults
# ---------------------------------------------------------------------------

AI_STEPS_PER_SECOND_DEFAULT: Final[int] = 10
AI_STEPS_PER_SECOND_MIN:     Final[int] = 1
AI_STEPS_PER_SECOND_MAX:     Final[int] = 20

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE: Final[str] = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR:    Final[str] = os.path.dirname(_HERE)
ASSETS_DIR:  Final[str] = os.path.join(ROOT_DIR, "assets")
SPRITES_DIR: Final[str] = os.path.join(ASSETS_DIR, "sprites")
FONTS_DIR:   Final[str] = os.path.join(ASSETS_DIR, "fonts")
LEVELS_DIR:  Final[str] = os.path.join(ROOT_DIR, "maps", "levels")
SAVES_DIR:   Final[str] = os.path.join(ROOT_DIR, "config")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL: Final[str] = "DEBUG"
LOG_FILE:  Final[str] = os.path.join(ROOT_DIR, "treasure_hunter.log")
