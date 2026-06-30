"""
combat_rules.py — Defines the turn-based 1D combat model and state transitions for adversarial search.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


class CombatState:
    """Represents the complete state of a combat match."""

    def __init__(
        self,
        player_hp: int = 100,
        player_pos: int = 1,
        monster_hp: int = 50,
        monster_pos: int = 5,
        is_player_turn: bool = True,
        player_dodging: bool = False,
        monster_dodging: bool = False,
    ) -> None:
        self.player_hp = player_hp
        self.player_pos = player_pos
        self.monster_hp = monster_hp
        self.monster_pos = monster_pos
        self.is_player_turn = is_player_turn
        self.player_dodging = player_dodging
        self.monster_dodging = monster_dodging

    def to_tuple(self) -> Tuple[int, int, int, int, bool, bool, bool]:
        """Convert state properties to hashable tuple representation."""
        return (
            self.player_hp,
            self.player_pos,
            self.monster_hp,
            self.monster_pos,
            self.is_player_turn,
            self.player_dodging,
            self.monster_dodging,
        )

    def copy(self) -> CombatState:
        """Create a clone of the combat state."""
        return CombatState(*self.to_tuple())


def get_actions() -> List[str]:
    """Return available actions in combat."""
    return ["ATTACK", "DODGE", "MOVE_L", "MOVE_R"]


def evaluate_state(state: CombatState) -> float:
    """Utility heuristic: player health advantage with bonuses/penalties for wins/losses."""
    if state.monster_hp <= 0:
        return 1000.0 + state.player_hp
    if state.player_hp <= 0:
        return -1000.0 - state.monster_hp
    return float(state.player_hp - state.monster_hp)


def get_successor(state: CombatState, action: str) -> CombatState:
    """Compute the resulting state after executing an action."""
    next_s = state.copy()
    
    # 1. Determine active entity
    is_player = state.is_player_turn

    # 2. Reset active entity's dodge status at start of turn
    if is_player:
        next_s.player_dodging = False
    else:
        next_s.monster_dodging = False

    # 3. Apply action mechanics
    if action == "ATTACK":
        dist = abs(next_s.player_pos - next_s.monster_pos)
        if dist == 1:
            damage = 15
            if is_player:
                if next_s.monster_dodging:
                    damage = 3  # Block 80%
                next_s.monster_hp = max(0, next_s.monster_hp - damage)
            else:
                if next_s.player_dodging:
                    damage = 3  # Block 80%
                next_s.player_hp = max(0, next_s.player_hp - damage)
        else:
            # Miss if out of range
            pass

    elif action == "DODGE":
        if is_player:
            next_s.player_dodging = True
        else:
            next_s.monster_dodging = True

    elif action == "MOVE_L":
        if is_player:
            new_pos = max(1, next_s.player_pos - 1)
            if new_pos != next_s.monster_pos:
                next_s.player_pos = new_pos
        else:
            new_pos = max(1, next_s.monster_pos - 1)
            if new_pos != next_s.player_pos:
                next_s.monster_pos = new_pos

    elif action == "MOVE_R":
        if is_player:
            new_pos = min(5, next_s.player_pos + 1)
            if new_pos != next_s.monster_pos:
                next_s.player_pos = new_pos
        else:
            new_pos = min(5, next_s.monster_pos + 1)
            if new_pos != next_s.player_pos:
                next_s.monster_pos = new_pos

    # 4. Flip turn
    next_s.is_player_turn = not is_player
    return next_s
