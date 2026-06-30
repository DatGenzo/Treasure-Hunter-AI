"""
inventory_system.py — Manages the player's inventory, keys, treasures, and potions.
"""

from __future__ import annotations

from typing import Dict, Union, Optional
from entities.item import ItemType


class Inventory:
    """Manages player inventory, including keys, treasures, and potions."""

    def __init__(self) -> None:
        self.keys: Dict[str, int] = {}
        self.treasures: int = 0
        self.potions: int = 0
        self.gold: int = 0

    def add_gold(self, amount: int) -> None:
        """Add gold to the inventory."""
        self.gold += max(0, amount)

    def add_item(self, item_type: Union[ItemType, str]) -> bool:
        """Add an item to the inventory. Returns True if successfully added."""
        from entities.item import VALUE_MAP
        if item_type == ItemType.KEY:
            self.add_key("default")
            return True
        elif isinstance(item_type, str) and "key" in item_type.lower():
            self.add_key(item_type)
            return True
        elif item_type in (ItemType.TREASURE, ItemType.TREASURE_SMALL, ItemType.TREASURE_MEDIUM, ItemType.TREASURE_LARGE):
            self.treasures += 1
            self.add_gold(VALUE_MAP.get(item_type, 0))
            return True
        elif item_type == ItemType.HEALTH_POTION:
            self.potions += 1
            return True
        return False

    def add_key(self, key_id: str = "default") -> None:
        """Add a named key to the inventory."""
        self.keys[key_id] = self.keys.get(key_id, 0) + 1

    def use_key(self, key_id: str = "default") -> bool:
        """Consume a key from inventory. Returns True if successfully consumed."""
        if self.keys.get(key_id, 0) > 0:
            self.keys[key_id] -= 1
            if self.keys[key_id] == 0:
                del self.keys[key_id]
            return True
        if len(self.keys) > 0:
            first_key = list(self.keys.keys())[0]
            self.keys[first_key] -= 1
            if self.keys[first_key] == 0:
                del self.keys[first_key]
            return True
        return False

    def use_potion(self) -> bool:
        """Consume a potion from inventory. Returns True if successfully consumed."""
        if self.potions > 0:
            self.potions -= 1
            return True
        return False

    def has_key(self, key_id: Optional[str] = None) -> bool:
        """Check if inventory contains a key.

        If key_id is specified, checks for that specific key.
        Otherwise, checks if there is any key.
        """
        if key_id is not None:
            if key_id in self.keys and self.keys[key_id] > 0:
                return True
            if key_id == "default" or key_id == "key":
                return sum(self.keys.values()) > 0
            return False
        return sum(self.keys.values()) > 0

    def clear(self) -> None:
        """Reset the inventory contents."""
        self.keys.clear()
        self.treasures = 0
        self.potions = 0
        self.gold = 0
