"""
game.py — Master Game class: pygame initialisation, main loop, and
scene/AI-runner coordination (MVC Controller layer).

The ``Game`` object owns:
- The pygame display surface
- The shared ``EventBus``
- The ``StateMachine``
- The ``GameClock``
- The active ``Scene`` stack
- The ``AIRunner`` (controls the AI tick budget per frame)
"""

from __future__ import annotations

import logging
import sys
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from scene.scene_manager import SceneManager
    from core.ai_runner import AIRunner

import pygame

from config.settings import (
    FPS,
    GAME_HEIGHT,
    GAME_WIDTH,
    PANEL_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from core.clock import GameClock
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine

logger = logging.getLogger(__name__)


class Game:
    """Top-level controller that owns the pygame window and main loop.

    Responsibilities:
    - Initialise / quit pygame subsystems.
    - Run the fixed-rate game loop (process events → update → render).
    - Route scene transitions driven by the StateMachine.
    - Delegate per-frame AI stepping to the AIRunner.

    Args:
        start_level: Level ID to load immediately (default: None → show menu).
    """

    def __init__(self, start_level: Optional[int] = None) -> None:
        self._start_level = start_level
        self._running: bool = False

        # Shared infrastructure
        self._bus: EventBus = EventBus()
        self._state_machine: StateMachine = StateMachine(self._bus)
        self._clock: GameClock = GameClock(FPS)

        # pygame surfaces
        self._screen: pygame.Surface
        self._game_surface: pygame.Surface  # left 960 px – map + entities
        self._panel_surface: pygame.Surface  # right 320 px – AI panel

        # Scenes and AI runner are imported lazily to avoid circular imports
        # at module load time.  They are assigned in _initialise().
        self._scene_manager: "SceneManager"  # noqa: F821 (forward ref, imported below)
        self._ai_runner: "AIRunner"           # noqa: F821

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Initialise pygame and start the game loop.  Blocks until exit."""
        try:
            self._initialise()
            self._loop()
        except Exception:
            logger.exception("Unhandled exception in Game.run()")
            raise
        finally:
            self._shutdown()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialise(self) -> None:
        """Set up pygame, create surfaces, and load the first scene."""
        logger.info("Initialising pygame …")
        pygame.init()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        pygame.display.set_caption(WINDOW_TITLE)

        self._screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE,
        )
        self._virtual_screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        self._panel_surface = pygame.Surface((PANEL_WIDTH, WINDOW_HEIGHT))

        # Install scaled mouse position monkeypatch
        if not hasattr(pygame.mouse, "get_pos_original"):
            pygame.mouse.get_pos_original = pygame.mouse.get_pos
            
            def _get_scaled_mouse_pos() -> tuple[int, int]:
                mx, my = pygame.mouse.get_pos_original()
                surface = pygame.display.get_surface()
                if surface is None:
                    return mx, my
                actual_w, actual_h = surface.get_size()
                if actual_w == 0 or actual_h == 0:
                    return mx, my
                return int(mx * WINDOW_WIDTH / actual_w), int(my * WINDOW_HEIGHT / actual_h)
            
            pygame.mouse.get_pos = _get_scaled_mouse_pos

        # Import scene manager and AI runner here to prevent circular imports
        from scene.scene_manager import SceneManager  # noqa: PLC0415
        from core.ai_runner import AIRunner            # noqa: PLC0415

        self._scene_manager = SceneManager(
            bus=self._bus,
            state_machine=self._state_machine,
            game_surface=self._game_surface,
            panel_surface=self._panel_surface,
            screen_surface=self._screen,
        )
        self._ai_runner = AIRunner(bus=self._bus, state_machine=self._state_machine, scene_manager=self._scene_manager)

        # Subscribe to scene-change events so Game can relay them
        self._bus.subscribe(Events.SCENE_CHANGE, self._on_scene_change)
        self._bus.subscribe(Events.GAME_OVER, self._on_game_over)

        # Load initial scene
        if self._start_level is not None:
            self._scene_manager.load_level(self._start_level)
        else:
            self._scene_manager.load_menu()

        self._running = True
        logger.info("Initialisation complete.  Window: %dx%d @ %d FPS",
                    WINDOW_WIDTH, WINDOW_HEIGHT, FPS)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Process events → update → render, every frame."""
        while self._running:
            dt: float = self._clock.tick()

            # 1. Pump pygame events
            actual_w, actual_h = self._screen.get_size()
            scale_x = WINDOW_WIDTH / actual_w if actual_w > 0 else 1.0
            scale_y = WINDOW_HEIGHT / actual_h if actual_h > 0 else 1.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.type == pygame.VIDEORESIZE:
                    self._screen = pygame.display.set_mode(
                        event.size,
                        pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE
                    )
                    actual_w, actual_h = event.size
                    scale_x = WINDOW_WIDTH / actual_w if actual_w > 0 else 1.0
                    scale_y = WINDOW_HEIGHT / actual_h if actual_h > 0 else 1.0
                
                # Scale mouse event coordinates to virtual space
                if hasattr(event, "pos") and event.pos is not None:
                    event.pos = (int(event.pos[0] * scale_x), int(event.pos[1] * scale_y))
                if event.type == pygame.MOUSEMOTION and hasattr(event, "rel") and event.rel is not None:
                    event.rel = (int(event.rel[0] * scale_x), int(event.rel[1] * scale_y))

                self._scene_manager.handle_event(event)

            if not self._running:
                break

            # 2. Update active scene + AI runner
            self._scene_manager.update(dt)
            if self._state_machine.is_ai_active():
                self._ai_runner.update(dt)

            # 3. Render
            if self._state_machine.state == GameState.MAIN_MENU:
                self._scene_manager.render(self._virtual_screen)
            else:
                self._scene_manager.render(self._game_surface)
                self._panel_surface.fill((22, 22, 38))  # PANEL_BG
                self._scene_manager.render_panel()

                # 4. Blit sub-surfaces onto the virtual screen
                self._virtual_screen.blit(self._game_surface, (0, 0))
                self._virtual_screen.blit(self._panel_surface, (GAME_WIDTH, 0))

            # Scale virtual screen to the actual screen resolution
            if (actual_w, actual_h) == (WINDOW_WIDTH, WINDOW_HEIGHT):
                self._screen.blit(self._virtual_screen, (0, 0))
            else:
                pygame.transform.smoothscale(self._virtual_screen, (actual_w, actual_h), self._screen)

            # 5. FPS counter in title bar (debug)
            pygame.display.set_caption(
                f"{WINDOW_TITLE}  —  {self._clock.fps:.1f} FPS"
            )
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_scene_change(
        self,
        old_state: GameState,
        new_state: GameState,
    ) -> None:
        """Relay state changes to the scene manager."""
        logger.debug("Game received scene change: %s -> %s",
                     old_state.name, new_state.name)
        self._scene_manager.on_state_change(old_state, new_state)

    def _on_game_over(self) -> None:
        """Handle game-over signal."""
        logger.info("Game Over received.")
        self._state_machine.transition(GameState.GAME_OVER)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        """Cleanly quit pygame subsystems."""
        logger.info("Shutting down pygame …")
        pygame.mixer.quit()
        pygame.quit()
        logger.info("Shutdown complete.")
