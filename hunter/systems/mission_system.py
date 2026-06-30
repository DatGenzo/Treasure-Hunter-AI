"""
mission_system.py — Mission and objective tracking system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MissionStep:
    """Represents a single objective within a level."""

    id: str                  # Unique identifier, e.g. "collect_key"
    description: str         # Text shown to player, e.g. "Collect the Golden Key"
    icon: str                # Graphical icon character, e.g. "🔑"
    completed: bool = False
    is_optional: bool = False


class MissionSystem:
    """Manages level goals, evaluates completion, and updates HUD states."""

    def __init__(self, steps: Optional[List[MissionStep]] = None) -> None:
        self.steps: List[MissionStep] = steps if steps is not None else []
        self.current_step_idx: int = 0

    def add_step(self, step: MissionStep) -> None:
        """Add an objective to the mission list."""
        self.steps.append(step)

    def load_from_json_data(self, data: List[Dict[str, Any]]) -> None:
        """Load mission steps from level configuration list."""
        self.steps = []
        for step_data in data:
            self.steps.append(MissionStep(
                id=step_data.get("id"),
                description=step_data.get("description"),
                icon=step_data.get("icon", "❓"),
                completed=step_data.get("completed", False),
                is_optional=step_data.get("is_optional", False)
            ))
        self.current_step_idx = 0

    def get_current_step(self) -> Optional[MissionStep]:
        """Return the current active objective."""
        # Find first uncompleted non-optional step
        for step in self.steps:
            if not step.completed and not step.is_optional:
                return step
        return None

    def get_active_goal(self) -> Optional[str]:
        """Return the ID of the current active goal."""
        step = self.get_current_step()
        return step.id if step else None

    def mark_completed(self, step_id: str) -> bool:
        """Manually mark a step as completed by its ID."""
        for step in self.steps:
            if step.id == step_id:
                if not step.completed:
                    step.completed = True
                    return True
        return False

    def update(self, game_state: Any) -> List[str]:
        """Automatically evaluate objectives based on current game state.

        Returns a list of step IDs that were completed in this update frame.
        """
        newly_completed = []

        # We support game_state as a dataclass or dictionary
        player_has_key = getattr(game_state, "player_has_key", False)
        if isinstance(game_state, dict):
            player_has_key = game_state.get("player_has_key", False)

        doors = getattr(game_state, "doors", [])
        if isinstance(game_state, dict):
            doors = game_state.get("doors", [])

        puzzle_states = getattr(game_state, "puzzle_states", {})
        if isinstance(game_state, dict):
            puzzle_states = game_state.get("puzzle_states", {})

        player_pos = getattr(game_state, "player_pos", (0, 0))
        if isinstance(game_state, dict):
            player_pos = game_state.get("player_pos", (0, 0))

        exit_pos = getattr(game_state, "exit_pos", (0, 0))
        if isinstance(game_state, dict):
            exit_pos = game_state.get("exit_pos", (0, 0))

        active_items = getattr(game_state, "active_items", [])
        if isinstance(game_state, dict):
            active_items = game_state.get("active_items", [])

        monsters = getattr(game_state, "monsters", [])
        if isinstance(game_state, dict):
            monsters = game_state.get("monsters", [])

        # Check objectives
        for step in self.steps:
            if step.completed:
                continue

            if step.id == "collect_key" and player_has_key:
                step.completed = True
                newly_completed.append(step.id)

            elif step.id == "unlock_door":
                # If all doors are unlocked
                all_unlocked = True
                for door in doors:
                    if hasattr(door, "locked"):
                        if door.locked:
                            all_unlocked = False
                            break
                    elif isinstance(door, tuple) and len(door) >= 3:
                        if door[2]:  # is_locked
                            all_unlocked = False
                            break
                if all_unlocked and len(doors) > 0:
                    step.completed = True
                    newly_completed.append(step.id)

            elif step.id == "solve_puzzle":
                if puzzle_states:
                    all_solved = all(puzzle_states.values())
                    if all_solved:
                        step.completed = True
                        newly_completed.append(step.id)
                else:
                    # Fallback check triggers solved
                    puzzle_triggers = getattr(game_state, "puzzle_triggers", [])
                    if isinstance(game_state, dict):
                        puzzle_triggers = game_state.get("puzzle_triggers", [])
                    
                    if puzzle_triggers and all(t.get("solved", False) for t in puzzle_triggers):
                        step.completed = True
                        newly_completed.append(step.id)

            elif step.id == "collect_treasure":
                has_treasure_left = False
                for item in active_items:
                    if isinstance(item, tuple) and len(item) >= 3:
                        if item[2] == "TREASURE":
                            has_treasure_left = True
                            break
                if not has_treasure_left:
                    step.completed = True
                    newly_completed.append(step.id)

            elif step.id == "defeat_monster":
                has_monsters_left = False
                for monster in monsters:
                    if isinstance(monster, tuple) and len(monster) >= 3:
                        if monster[2] != "DEAD" and monster[2] != "INACTIVE":
                            has_monsters_left = True
                            break
                    elif hasattr(monster, "active"):
                        if monster.active:
                            has_monsters_left = True
                            break
                if not has_monsters_left:
                    step.completed = True
                    newly_completed.append(step.id)

            elif step.id == "reach_exit" and player_pos == exit_pos:
                step.completed = True
                newly_completed.append(step.id)

        return newly_completed

    def all_required_completed(self) -> bool:
        """Return True if all non-optional objectives are complete."""
        return all(step.completed for step in self.steps if not step.is_optional)

    def get_ai_target(self, game_state: dict, goal_planner: Optional[Any] = None) -> Tuple[int, int]:
        """Determine next AI target by delegating to GoalPlanner.

        Args:
            game_state: A dictionary representation of current game state.
            goal_planner: An optional GoalPlanner instance.
        """
        if goal_planner is not None:
            return goal_planner.plan_next_goal(game_state)
        return game_state.get("exit_pos", (0, 0))

