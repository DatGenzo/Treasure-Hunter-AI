"""
puzzle_scene.py — The Latin Square gem arrangement minigame scene.
"""

from __future__ import annotations

import logging
import math
from typing import Any, List, Tuple

import pygame

from algorithms.csp.backtracking import BacktrackingCSPSolver
from config.settings import (
    DARK_BG,
    ACCENT,
    ACCENT_HOVER,
    PANEL_BG,
    PANEL_BORDER,
    TEXT_PRIMARY,
    TEXT_MUTED,
    SUCCESS,
    WARNING,
    DANGER,
)
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine
from maps.puzzle import GemPuzzle
from scene.base_scene import BaseScene
from ui.widgets import Button, StatRow, InGameMenu

logger = logging.getLogger(__name__)


class PuzzleScene(BaseScene):
    """Minigame scene where the user or AI solves a 3x3 Latin Square gem arrangement puzzle."""

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        game_surface: pygame.Surface,
        panel_surface: pygame.Surface,
        puzzle_id: str = "puzzle",
        auto_solve: bool = False,
    ) -> None:
        super().__init__(bus, state_machine, game_surface)
        self._panel_surface = panel_surface
        self._puzzle_id = puzzle_id
        self._auto_solve = auto_solve
        self._auto_close_timer = 0.0

        # Model and solver
        self._puzzle = GemPuzzle()
        self._solver = BacktrackingCSPSolver()

        # Fonts
        self._title_font = pygame.font.SysFont("consolas", 24, bold=True)
        self._font = pygame.font.SysFont("consolas", 16)
        self._bold_font = pygame.font.SysFont("consolas", 16, bold=True)
        self._gem_font = pygame.font.SysFont("consolas", 36, bold=True)

        # UI components (Relative to panel surface coordinates)
        self._solve_btn = Button(
            20, 100, 280, 42, "AI SOLVE", self._bold_font, (30, 60, 120), ACCENT_HOVER, PANEL_BORDER
        )
        self._reset_btn = Button(
            20, 160, 280, 42, "RESET", self._bold_font, (40, 45, 60), (60, 65, 80), PANEL_BORDER
        )
        self._exit_btn = Button(
            20, 220, 280, 42, "EXIT PUZZLE", self._bold_font, (120, 30, 30), DANGER, PANEL_BORDER
        )

        # AI execution control
        self._ai_active = False
        self._step_timer = 0.0
        self._step_delay = 0.2  # Time in seconds between CSP steps

        # Grid geometry (Centered in 960 × 720 game surface)
        self._cell_size = 90
        self._cell_spacing = 15
        grid_dim = 3 * self._cell_size + 2 * self._cell_spacing
        self._grid_start_x = (960 - grid_dim) // 2
        self._grid_start_y = (720 - grid_dim) // 2

        # Glowing outline animation
        self._glow_timer = 0.0

        self._ingame_menu = InGameMenu(self._bus, self._sm)
        logger.info("PuzzleScene initialized successfully.")

    def on_enter(self) -> None:
        """Invoked when scene is pushed."""
        logger.info("Entering PuzzleScene minigame.")
        self._bus.publish(Events.PUZZLE_STARTED)
        if self._auto_solve and not self._puzzle.is_solved():
            logger.info("Auto-solving puzzle (AI mode).")
            self._ai_active = True
            self._solver.initialise(self._puzzle)

    def on_exit(self) -> None:
        """Invoked when scene is popped."""
        logger.info("Exiting PuzzleScene minigame.")
        if self._puzzle.is_solved():
            self._bus.publish("ai_resume")

    def _get_cell_rect(self, row: int, col: int) -> pygame.Rect:
        """Return the Screen Rect for the grid cell at (row, col)."""
        x = self._grid_start_x + col * (self._cell_size + self._cell_spacing)
        y = self._grid_start_y + row * (self._cell_size + self._cell_spacing)
        return pygame.Rect(x, y, self._cell_size, self._cell_size)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward mouse events to panel buttons or solve manual grid clicks."""
        # 0. Forward to in-game menu first
        if self._ingame_menu.handle_event(event):
            return
        # 1. Forward to panel buttons (offset by 960 pixels)
        self._solve_btn.handle_event(event, offset_x=960)
        self._reset_btn.handle_event(event, offset_x=960)
        self._exit_btn.handle_event(event, offset_x=960)

        # 2. Check panel button clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            # Reset
            if self._reset_btn.rect.collidepoint(mx - 960, my):
                logger.info("Resetting puzzle.")
                self._ai_active = False
                self._puzzle.reset()
                return

            # AI Solve
            if self._solve_btn.rect.collidepoint(mx - 960, my):
                if not self._ai_active and not self._puzzle.is_solved():
                    logger.info("Starting backtracking CSP solver.")
                    self._ai_active = True
                    self._solver.initialise(self._puzzle)
                return

            # Exit minigame
            if self._exit_btn.rect.collidepoint(mx - 960, my):
                logger.info("Exiting Gem Puzzle.")
                # We simply return to play scene
                self._bus.publish("pop_scene")
                return

            # Check manual grid cells clicks (Only if AI is not running and not yet solved)
            if not self._ai_active and not self._puzzle.is_solved():
                for r in range(3):
                    for c in range(3):
                        rect = self._get_cell_rect(r, c)
                        if rect.collidepoint(mx, my):
                            # Cycle colors: 0 (Empty) -> 1 (Red) -> 2 (Green) -> 3 (Blue) -> 0
                            curr = self._puzzle.get_val(r, c)
                            nxt = (curr + 1) % 4
                            
                            # Skip fixed cells
                            if self._puzzle.set_val(r, c, nxt):
                                logger.debug("Manual cell (%d, %d) set to %d", r, c, nxt)
                                if self._puzzle.is_solved():
                                    logger.info("Puzzle Solved manually!")
                                    self._bus.publish(Events.PUZZLE_SOLVED, puzzle_id=self._puzzle_id)
                                return

    def update(self, dt: float) -> None:
        """Step the CSP solver and advance glow animations."""
        if self._ingame_menu.active:
            return
        self._glow_timer += dt

        if self._ai_active:
            self._step_timer += dt
            if self._step_timer >= self._step_delay:
                self._step_timer = 0.0
                
                # Step the solver
                self._solver.step()

                if self._solver.is_done():
                    self._ai_active = False
                    if self._solver.is_success():
                        logger.info("CSP solver succeeded in solving the puzzle!")
                        self._bus.publish(Events.PUZZLE_SOLVED, puzzle_id=self._puzzle_id)
                        if self._auto_solve:
                            self._auto_close_timer = 1.5
                    else:
                        logger.warning("CSP solver failed to find a valid solution!")

        if self._auto_close_timer > 0:
            self._auto_close_timer -= dt
            if self._auto_close_timer <= 0:
                self._bus.publish("pop_scene")

    def render(self, surface: pygame.Surface) -> None:
        """Render the minigame grid, gems, and title."""
        surface.fill(DARK_BG)

        # Draw pulsing outer title
        pulse = int(180 + 75 * abs(math.sin(self._glow_timer * 4.0)))
        title_surf = self._title_font.render("ANCIENT GEM ARRANGEMENT PUZZLE", True, (pulse, pulse, 255))
        surface.blit(title_surf, title_surf.get_rect(center=(960 // 2, 50)))

        desc_surf = self._font.render("Latin Square Rule: No duplicate gem colors in any row or column.", True, TEXT_MUTED)
        surface.blit(desc_surf, desc_surf.get_rect(center=(960 // 2, 85)))

        # Draw grid board
        board_rect = pygame.Rect(self._grid_start_x - 10, self._grid_start_y - 10, 330 + 20, 330 + 20)
        pygame.draw.rect(surface, (25, 25, 40), board_rect, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, board_rect, 2, border_radius=10)

        # Color table for gems
        gem_colors = {
            0: (40, 45, 60),      # Empty (Gray)
            1: (230, 50, 50),     # Red
            2: (50, 200, 80),     # Green
            3: (50, 100, 230),    # Blue
        }
        gem_labels = {
            0: "",
            1: "R",
            2: "G",
            3: "B",
        }

        # Draw cells
        for r in range(3):
            for c in range(3):
                rect = self._get_cell_rect(r, c)
                val = self._puzzle.get_val(r, c)
                color = gem_colors.get(val, (40, 45, 60))

                # Background cell
                pygame.draw.rect(surface, color, rect, border_radius=8)

                # Draw outline
                if self._puzzle.fixed[r][c]:
                    # Fixed cells have white locks
                    pygame.draw.rect(surface, (255, 255, 255), rect, 3, border_radius=8)
                else:
                    # Mutable cells
                    is_violation = (r, c) in self._solver.violations
                    is_current = (r, c) == self._solver.current_var

                    if is_violation:
                        pygame.draw.rect(surface, DANGER, rect, 3, border_radius=8)
                    elif is_current:
                        pulse_val = int(120 + 135 * abs(math.sin(self._glow_timer * 6.0)))
                        pygame.draw.rect(surface, (pulse_val, pulse_val, 50), rect, 3, border_radius=8)
                    elif val != 0 and not self._puzzle.is_valid(r, c, val):
                        pygame.draw.rect(surface, DANGER, rect, 3, border_radius=8)
                    else:
                        pygame.draw.rect(surface, (80, 85, 105), rect, 1, border_radius=8)

                # Render gem character text
                if val != 0:
                    text_color = (255, 255, 255)
                    char_surf = self._gem_font.render(gem_labels[val], True, text_color)
                    surface.blit(char_surf, char_surf.get_rect(center=rect.center))

        # Status text below board
        if self._puzzle.is_solved():
            status_text = "SOLVED! Ancient door unlocks..."
            status_color = SUCCESS
        elif self._ai_active:
            status_text = "AI backtracking... analyzing constraint graphs"
            status_color = WARNING
        else:
            status_text = "Select cells to cycle colors: Red -> Green -> Blue -> Empty"
            status_color = TEXT_PRIMARY

        stat_surf = self._font.render(status_text, True, status_color)
        surface.blit(stat_surf, stat_surf.get_rect(center=(960 // 2, 720 - 100)))

        # Draw in-game menu overlay
        self._ingame_menu.render(surface)

    def render_panel(self, panel: pygame.Surface) -> None:
        """Render the minigame instructions and controls on the side panel."""
        panel.fill(PANEL_BG)

        # Title
        title_surf = self._title_font.render("🧩 GEM PUZZLE", True, TEXT_PRIMARY)
        panel.blit(title_surf, (20, 20))
        pygame.draw.line(panel, PANEL_BORDER, (10, 60), (310, 60), 2)

        # Render buttons
        self._solve_btn.render(panel)
        self._reset_btn.render(panel)
        self._exit_btn.render(panel)

        # Divider
        pygame.draw.line(panel, PANEL_BORDER, (10, 290), (310, 290), 1)

        # Stats Header
        stats_hdr = self._bold_font.render("CSP STATISTICS", True, TEXT_PRIMARY)
        panel.blit(stats_hdr, (20, 310))

        y = 345
        assignments_str = f"{self._solver.assignments}" if self._ai_active or self._solver.is_done() else "0"
        backtracks_str = f"{self._solver.backtracks}" if self._ai_active or self._solver.is_done() else "0"
        
        y = StatRow("Variable Assigns:", assignments_str, self._font).render(panel, 20, y)
        y = StatRow("Constraint Checks:", f"{max(0, self._solver.assignments + self._solver.backtracks)}", self._font).render(panel, 20, y)
        y = StatRow("Backtracks:", backtracks_str, self._font).render(panel, 20, y)

        # Solver status
        status_val = "Solving..." if self._ai_active else ("Solved" if self._puzzle.is_solved() else "Idle")
        y = StatRow("Solver Status:", status_val, self._font).render(panel, 20, y)

        # -------------------------------------------------------------
        # CONSTRAINT GRAPH SECTION
        # -------------------------------------------------------------
        pygame.draw.line(panel, PANEL_BORDER, (10, y + 10), (310, y + 10), 1)
        graph_hdr = self._bold_font.render("CONSTRAINT GRAPH", True, TEXT_PRIMARY)
        panel.blit(graph_hdr, (20, y + 20))

        # Import and render CSP Overlay constraint graph
        from visualisation.csp_overlay import CSPOverlay
        graph_rect = pygame.Rect(20, y + 40, 280, 200)
        
        # Build live vis data from solver
        vis_data = self._solver.get_vis_data()
        CSPOverlay.render_constraint_graph(panel, vis_data, graph_rect)
