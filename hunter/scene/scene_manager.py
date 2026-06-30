"""
scene_manager.py — Owns and routes between all Scene instances.

SceneManager holds exactly one *active* scene at a time.  When the
StateMachine changes state, ``on_state_change()`` swaps in the correct
scene.  All pygame event, update, and render calls are forwarded to the
active scene.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from scene.base_scene import BaseScene

import pygame

from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine

logger = logging.getLogger(__name__)


class SceneManager:
    """Routes game loop calls to the currently active Scene.

    Args:
        bus:           Shared EventBus.
        state_machine: Shared StateMachine.
        game_surface:  Left surface (960 × 720) for map / entities.
        panel_surface: Right surface (320 × 720) for AI panel.
    """

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        game_surface: pygame.Surface,
        panel_surface: pygame.Surface,
        screen_surface: Optional[pygame.Surface] = None,
    ) -> None:
        self._bus = bus
        self._sm = state_machine
        self._game_surface = game_surface
        self._panel_surface = panel_surface
        self._screen_surface = screen_surface

        # Scenes are imported lazily on first use to avoid circular imports
        self._scenes: Dict[GameState, "BaseScene"] = {}  # noqa: F821
        self._active: Optional["BaseScene"] = None        # noqa: F821
        self._scene_stack: List["BaseScene"] = []

        # Comparative history metrics: level_id -> {"human": {...}, "ai": {...}}
        self._history: Dict[int, Dict[str, Any]] = {}
        self._last_completed_level_id: int = 1
        self._last_completed_run_stats: Dict[str, Any] = {}

        self._bus.subscribe("load_level", self.load_level)
        self._bus.subscribe("push_scene", self.push_scene)
        self._bus.subscribe("pop_scene", self.pop_scene)
        self._bus.subscribe("start_benchmark", self.load_benchmark)
        self._bus.subscribe(Events.LEVEL_COMPLETE, self.on_level_complete)

        self.load_progression()

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def load_menu(self) -> None:
        """Switch to the main-menu scene."""
        from scene.menu_scene import MenuScene  # noqa: PLC0415
        surface = self._screen_surface if self._screen_surface is not None else self._game_surface
        self._set_scene(GameState.MAIN_MENU, MenuScene(
            bus=self._bus,
            state_machine=self._sm,
            surface=surface,
        ))

    def load_level_select(self) -> None:
        """Switch to the level-select scene."""
        from scene.level_select_scene import LevelSelectScene  # noqa: PLC0415
        self._set_scene(GameState.LEVEL_SELECT, LevelSelectScene(
            bus=self._bus,
            state_machine=self._sm,
            surface=self._game_surface,
        ))

    def load_level(self, level_id: int) -> None:
        """Load and activate the gameplay scene for *level_id*."""
        if self._sm.state != GameState.PLAYING:
            if not self._sm.transition(GameState.PLAYING):
                self._sm.force_transition(GameState.PLAYING)
        from scene.game_scene import GameScene  # noqa: PLC0415
        scene = GameScene(
            bus=self._bus,
            state_machine=self._sm,
            game_surface=self._game_surface,
            panel_surface=self._panel_surface,
            level_id=level_id,
        )
        self._set_scene(GameState.PLAYING, scene)

    # ------------------------------------------------------------------
    # Game-loop forwarding
    def push_scene(self, scene: "BaseScene") -> None:
        """Suspend the current active scene and push a new scene onto the stack."""
        if self._active is not None:
            self._active.on_exit()
            self._scene_stack.append(self._active)
        self._active = scene
        self._active.on_enter()
        logger.info("SceneManager: Pushed scene %s", type(scene).__name__)

    def pop_scene(self) -> None:
        """Pop the top scene from the stack and resume the previous scene."""
        if self._scene_stack:
            if self._active is not None:
                self._active.on_exit()
            self._active = self._scene_stack.pop()
            self._active.on_enter()
            logger.info("SceneManager: Popped back to scene %s", type(self._active).__name__)
        else:
            logger.warning("SceneManager: Attempted to pop scene with empty stack.")

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward a pygame event to the active scene."""
        if self._active is not None:
            self._active.handle_event(event)

    def update(self, dt: float) -> None:
        """Forward update tick to the active scene."""
        if self._active is not None:
            self._active.update(dt)

    def render(self, surface: Optional[pygame.Surface] = None) -> None:
        """Ask the active scene to draw onto the given surface (defaults to self._game_surface)."""
        if self._active is not None:
            target_surf = surface if surface is not None else self._game_surface
            self._active.render(target_surf)

    def render_panel(self) -> None:
        """Ask the active scene to draw the AI panel onto ``panel_surface``."""
        if self._active is not None:
            self._active.render_panel(self._panel_surface)

    # ------------------------------------------------------------------
    # State-change callback (registered by Game)
    # ------------------------------------------------------------------

    def on_state_change(
        self,
        old_state: GameState,
        new_state: GameState,
    ) -> None:
        """React to a StateMachine transition."""
        logger.debug("SceneManager: %s -> %s", old_state.name, new_state.name)

        if new_state == GameState.MAIN_MENU:
            self.load_menu()
        elif new_state == GameState.LEVEL_SELECT:
            self.load_level_select()
        elif new_state == GameState.LEVEL_COMPLETE:
            self.load_stats()

    def load_stats(self) -> None:
        """Switch to comparative StatsScene."""
        from scene.stats_scene import StatsScene  # noqa: PLC0415
        scene = StatsScene(
            bus=self._bus,
            state_machine=self._sm,
            game_surface=self._game_surface,
            panel_surface=self._panel_surface,
            level_id=self._last_completed_level_id,
            run_stats=self._last_completed_run_stats,
            history_stats=self._history,
        )
        self._set_scene(GameState.LEVEL_COMPLETE, scene)

    def load_benchmark(self, level_id: int) -> None:
        """Switch to BenchmarkScene."""
        from scene.benchmark_scene import BenchmarkScene
        scene = BenchmarkScene(
            bus=self._bus,
            state_machine=self._sm,
            game_surface=self._game_surface,
            panel_surface=self._panel_surface,
            level_id=level_id,
        )
        self._set_scene(GameState.LEVEL_SELECT, scene)

    def on_level_complete(self, level_id: int, stats: Dict[str, Any]) -> None:
        """Process level complete metrics and unlock next level progression."""
        self._last_completed_level_id = level_id
        self._last_completed_run_stats = stats

        # Update comparative history metrics
        mode = "ai" if stats.get("is_ai", False) else "human"
        if level_id not in self._history:
            self._history[level_id] = {
                "human": {"time": 0.0, "cost": 0.0, "nodes": 0, "steps_taken": 0, "treasures_pct": 0.0, "hp_pct": 100.0},
                "ai": {"time": 0.0, "cost": 0.0, "nodes": 0, "steps_taken": 0, "treasures_pct": 0.0, "hp_pct": 100.0}
            }
        
        self._history[level_id][mode] = {
            "time": stats.get("time", 0.0),
            "cost": stats.get("cost", 0.0),
            "nodes": stats.get("nodes", 0),
            "steps_taken": stats.get("steps_taken", 0),
            "treasures_pct": stats.get("treasures_pct", 0.0),
            "hp_pct": stats.get("hp_pct", 100.0)
        }

        # Progression: unlock next level
        from scene.level_select_scene import LevelSelectScene  # noqa: PLC0415
        next_level = level_id + 1
        from config.level_config import LEVEL_MAP
        if next_level in LEVEL_MAP:
            LevelSelectScene.unlocked_levels.add(next_level)
            self.save_progression()

    def load_progression(self) -> None:
        """Load level unlock progression from unlocked_levels.json."""
        import json
        import os
        try:
            from scene.level_select_scene import LevelSelectScene  # noqa: PLC0415
            if os.path.exists("unlocked_levels.json"):
                with open("unlocked_levels.json", "r", encoding="utf-8") as f:
                    unlocked = json.load(f)
                    if isinstance(unlocked, list):
                        LevelSelectScene.unlocked_levels = set(unlocked)
        except Exception as e:
            logger.debug("Failed to load level progression: %s", e)

    def save_progression(self) -> None:
        """Save level unlock progression to unlocked_levels.json."""
        import json
        try:
            from scene.level_select_scene import LevelSelectScene  # noqa: PLC0415
            with open("unlocked_levels.json", "w", encoding="utf-8") as f:
                json.dump(list(LevelSelectScene.unlocked_levels), f)
        except Exception as e:
            logger.debug("Failed to save level progression: %s", e)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_scene(self, state: GameState, scene: "BaseScene") -> None:  # noqa: F821
        """Deactivate the current scene and activate *scene*."""
        if self._active is not None:
            self._active.on_exit()

        self._scene_stack.clear()

        self._scenes[state] = scene
        self._active = scene
        self._active.on_enter()
        logger.info("SceneManager: active scene -> %s", type(scene).__name__)
