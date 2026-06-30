"""
loader.py — Map serialization/deserialization helper to load JSON files.
"""

from __future__ import annotations

import json
import os
import logging
from typing import List, Tuple

from config.settings import LEVELS_DIR
from maps.tile import Tile, TileType
from maps.tilemap import TileMap
from utils.vec2 import Vec2

logger = logging.getLogger(__name__)

# Map integer code from JSON file to TileType
INT_TO_TILE_TYPE = {
    0: TileType.FLOOR,
    1: TileType.WALL,
    2: TileType.MUD,
    3: TileType.WATER,
    4: TileType.TRAP,
    5: TileType.LAVA,
    9: TileType.EXIT,
}


def load_level(level_id: int) -> TileMap:
    """Load and parse level JSON file for the given level_id.

    Args:
        level_id: The ID of the level to load (e.g. 1).

    Returns:
        A loaded TileMap instance.

    Raises:
        FileNotFoundError: If the level file does not exist.
        ValueError: If JSON data is invalid.
    """
    file_name = f"level_{level_id:02d}.json"
    file_path = os.path.join(LEVELS_DIR, file_name)

    logger.info("Loading level data from %s", file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Level file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Parse Grid
    grid_data: List[List[int]] = data["grid"]
    grid: List[List[Tile]] = []
    for row_data in grid_data:
        row_tiles: List[Tile] = []
        for cell_val in row_data:
            tile_type = INT_TO_TILE_TYPE.get(cell_val, TileType.WALL)
            row_tiles.append(Tile(tile_type))
        grid.append(row_tiles)

    # 2. Parse Spawns
    spawn_arr = data.get("spawn", [1, 1])
    exit_arr = data.get("exit", [28, 20])
    spawn_pos = Vec2(spawn_arr[0], spawn_arr[1])
    exit_pos = Vec2(exit_arr[0], exit_arr[1])

    # 3. Parse Items & Monsters
    raw_items = data.get("items", [])
    item_spawns: List[Tuple[int, int, str]] = []
    for item in raw_items:
        # Expected format: [col, row, type]
        item_spawns.append((item[0], item[1], item[2]))

    raw_monsters = data.get("monsters", [])
    monster_spawns: List[Tuple[int, int, str]] = []
    for monster in raw_monsters:
        # Expected format: [col, row, type]
        monster_spawns.append((monster[0], monster[1], monster[2]))

    # 4. Parse Doors and Puzzle Triggers
    raw_doors = data.get("doors", [])
    doors_data = []
    for d in raw_doors:
        if isinstance(d, dict):
            doors_data.append({
                "col": d.get("col"),
                "row": d.get("row"),
                "id": d.get("id"),
                "key_required": d.get("key_required"),
                "puzzle_id": d.get("puzzle_id"),
                "color": d.get("color")
            })
        elif isinstance(d, list) and len(d) >= 5:
            doors_data.append({
                "col": d[0],
                "row": d[1],
                "id": d[2],
                "key_required": d[3],
                "puzzle_id": d[4],
                "color": d[5] if len(d) >= 6 else None
            })

    raw_puzzles = data.get("puzzle_triggers", [])
    puzzle_triggers_data = []
    for p in raw_puzzles:
        if isinstance(p, dict):
            puzzle_triggers_data.append({
                "col": p.get("col"),
                "row": p.get("row"),
                "puzzle_id": p.get("puzzle_id"),
                "color": p.get("color")
            })
        elif isinstance(p, list) and len(p) >= 3:
            puzzle_triggers_data.append({
                "col": p[0],
                "row": p[1],
                "puzzle_id": p[2],
                "color": p[3] if len(p) >= 4 else None
            })

    raw_traps = data.get("traps", [])
    traps_data = []
    for t in raw_traps:
        if isinstance(t, dict):
            traps_data.append({
                "col": t.get("col"),
                "row": t.get("row"),
                "type": t.get("type", "spike"),
                "damage": t.get("damage", 10),
                "visible": t.get("visible", True)
            })
        elif isinstance(t, list) and len(t) >= 3:
            traps_data.append({
                "col": t[0],
                "row": t[1],
                "type": t[2],
                "damage": t[3] if len(t) >= 4 else 10,
                "visible": t[4] if len(t) >= 5 else True
            })

    raw_missions = data.get("missions", [])
    missions_data = []
    for m in raw_missions:
        if isinstance(m, dict):
            missions_data.append({
                "id": m.get("id"),
                "description": m.get("description"),
                "icon": m.get("icon", "❓"),
                "completed": m.get("completed", False),
                "is_optional": m.get("is_optional", False)
            })

    raw_chests = data.get("chests", [])
    chest_data = []
    for c in raw_chests:
        if isinstance(c, dict):
            chest_data.append({
                "col": c.get("col"),
                "row": c.get("row"),
                "value": c.get("value", 50)
            })
        elif isinstance(c, list) and len(c) >= 2:
            chest_data.append({
                "col": c[0],
                "row": c[1],
                "value": c[2] if len(c) >= 3 else 50
            })

    # Set the exit tile type in the grid explicitly to TileType.EXIT just in case
    # the grid array doesn't specify it, or override it to match the exit_pos.
    if 0 <= exit_pos.y < len(grid) and 0 <= exit_pos.x < len(grid[0]):
        grid[exit_pos.y][exit_pos.x] = Tile(TileType.EXIT)

    return TileMap(
        grid=grid,
        spawn_pos=spawn_pos,
        exit_pos=exit_pos,
        item_spawns=item_spawns,
        monster_spawns=monster_spawns,
        doors_data=doors_data,
        puzzle_triggers_data=puzzle_triggers_data,
        traps_data=traps_data,
        missions_data=missions_data,
        chest_data=chest_data,
    )
