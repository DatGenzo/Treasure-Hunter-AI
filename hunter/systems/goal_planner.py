"""
goal_planner.py — Plan next sub-goals for AI based on mission state and game state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from maps.tilemap import TileMap
from core.event_bus import EventBus, Events
from systems.mission_system import MissionSystem

logger = logging.getLogger(__name__)


class GoalPlanner:
    """Calculates the next grid target (col, row) for the AI based on mission progress."""

    def __init__(self, mission_system: MissionSystem, tilemap: TileMap, bus: EventBus) -> None:
        self._mission = mission_system
        self._tilemap = tilemap
        self._bus = bus
        self._current_subgoal: Optional[Tuple[int, int]] = None

    def plan_next_goal(self, game_state: Dict[str, Any]) -> Tuple[int, int]:
        """Determine (col, row) of the next sub-goal for pathfinding."""
        step = self._mission.get_current_step()
        if step is None:
            exit_pos = game_state.get("exit_pos", (0, 0))
            self._current_subgoal = exit_pos
            return exit_pos

        target = None
        player_pos = game_state.get("player_pos", (0, 0))
        if step.id == "collect_key":
            closest_dist = 999999
            for item in game_state.get("active_items", []):
                if item[2] == "KEY":
                    dist = abs(player_pos[0] - item[0]) + abs(player_pos[1] - item[1])
                    if dist < closest_dist:
                        closest_dist = dist
                        target = (item[0], item[1])
        elif step.id == "unlock_door":
            closest_dist = 999999
            chosen_door = None
            door_puzzles = game_state.get("door_puzzles", {})
            for door_info in game_state.get("doors", []):
                col, row = door_info[0], door_info[1]
                locked = door_info[2]
                puzzle_id = door_puzzles.get((col, row))
                if locked:
                    dist = abs(player_pos[0] - col) + abs(player_pos[1] - row)
                    if dist < closest_dist:
                        closest_dist = dist
                        chosen_door = (col, row, puzzle_id)
            if chosen_door:
                col, row, puzzle_id = chosen_door
                if puzzle_id:
                    triggers = game_state.get("puzzle_triggers", [])
                    trigger_target = None
                    for t in triggers:
                        if t.get("puzzle_id") == puzzle_id and not t.get("solved", False):
                            trigger_target = (t.get("col"), t.get("row"))
                            break
                    if trigger_target:
                        target = trigger_target
                    else:
                        target = (col, row)
                else:
                    if not game_state.get("player_has_key", False):
                        items = game_state.get("active_items", [])
                        key_target = None
                        for item in items:
                            if len(item) >= 3 and item[2] == "KEY":
                                key_target = (item[0], item[1])
                                break
                        if key_target:
                            target = key_target
                        else:
                            target = (col, row)
                    else:
                        target = (col, row)
        elif step.id == "solve_puzzle":
            closest_dist = 999999
            triggers = game_state.get("puzzle_triggers", [])
            for trigger in triggers:
                col, row = trigger.get("col"), trigger.get("row")
                solved = trigger.get("solved", False)
                if not solved:
                    dist = abs(player_pos[0] - col) + abs(player_pos[1] - row)
                    if dist < closest_dist:
                        closest_dist = dist
                        target = (col, row)
        elif step.id == "collect_treasure":
            closest_dist = 999999
            # Check regular treasure items
            for item in game_state.get("active_items", []):
                if item[2] == "TREASURE":
                    dist = abs(player_pos[0] - item[0]) + abs(player_pos[1] - item[1])
                    if dist < closest_dist:
                        closest_dist = dist
                        target = (item[0], item[1])
            # Also target closed chests (they hold higher-value treasure)
            for chest_pos in game_state.get("closed_chests", []):
                dist = abs(player_pos[0] - chest_pos[0]) + abs(player_pos[1] - chest_pos[1])
                if dist < closest_dist:
                    closest_dist = dist
                    target = (chest_pos[0], chest_pos[1])
        elif step.id == "reach_exit":
            target = game_state.get("exit_pos", (0, 0))

        if target is None:
            target = game_state.get("exit_pos", (0, 0))

        self._current_subgoal = target
        return target

    def on_subgoal_reached(self, game_state: Dict[str, Any]) -> bool:
        """Evaluate if the current subgoal is reached and progress the mission.

        Returns True if all required missions are completed.
        """
        player_pos = game_state.get("player_pos", (0, 0))
        
        step = self._mission.get_current_step()
        if step is None:
            return True

        subgoal_reached = False
        if self._current_subgoal and player_pos == self._current_subgoal:
            subgoal_reached = True

        newly_completed = self._mission.update(game_state)
        
        # For puzzle steps, position match alone is insufficient — puzzle must actually be solved
        if step.id in ["solve_puzzle", "unlock_door", "collect_treasure", "defeat_monster"]:
            subgoal_reached = False

        if step.id in newly_completed or subgoal_reached:
            if not step.completed:
                self._mission.mark_completed(step.id)
            self._bus.publish("mission_updated", step_id=step.id)
            self._bus.publish("ai_subgoal_reached", step_id=step.id)
            logger.info("AI Subgoal reached: %s at %s", step.id, player_pos)
            return self._mission.all_required_completed()
            
        return self._mission.all_required_completed()

    def get_goal_description(self) -> str:
        """Get a text description of the current objective."""
        step = self._mission.get_current_step()
        if step:
            return f"{step.icon} {step.description}"
        return "🚪 Reach the Exit Portal"
