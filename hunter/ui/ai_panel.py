"""
ai_panel.py — Right-hand side AI configuration, statistics, and legend panel.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from systems.mission_system import MissionSystem

import pygame

from config.algorithm_config import ALGORITHMS
from config.settings import (
    ACCENT,
    ACCENT_HOVER,
    PANEL_BG,
    PANEL_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    SUCCESS,
    WARNING,
    DANGER,
)
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine
from ui.widgets import Button, Dropdown, Slider, StatRow, wrap_text

logger = logging.getLogger(__name__)


class AIPanel:
    """Combines algorithm selection dropdown, speed slider, action buttons, stats rows, and map legends.

    Renders onto the right-side 320 × 720 panel surface.

    Args:
        bus:                Shared EventBus.
        state_machine:      Shared StateMachine.
        allowed_algorithms: Allowed algorithm keys for the active level.
    """

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        allowed_algorithms: Set[str],
        mission_system: Optional["MissionSystem"] = None,
    ) -> None:
        self._bus = bus
        self._sm = state_machine
        self._mission_system = mission_system

        self._font = pygame.font.SysFont("consolas", 15)
        self._bold_font = pygame.font.SysFont("consolas", 16, bold=True)
        self._title_font = pygame.font.SysFont("consolas", 24, bold=True)

        # 1. Filter and build dropdown options
        options = [
            (a.key, a.display_name) for a in ALGORITHMS if a.key in allowed_algorithms
        ]
        if not options:
            options = [("bfs", "Breadth-First Search")]  # Fallback
        self._dropdown = Dropdown(20, 80, 280, 36, options, self._font)

        # 2. Build playback speed slider
        self._slider = Slider(
            x=20,
            y=135,
            w=280,
            min_val=1.0,
            max_val=20.0,
            initial_val=10.0,
            font=self._font,
            label="AI Search Speed",
        )

        # 3. Control Buttons
        btn_w, btn_h = 280, 42
        self._solve_btn = Button(
            20, 200, btn_w, btn_h, "AI SOLVE", self._bold_font, (30, 60, 120), ACCENT_HOVER, PANEL_BORDER
        )
        self._pause_btn = Button(
            20, 200, 130, btn_h, "PAUSE", self._bold_font, (180, 120, 30), WARNING, PANEL_BORDER
        )
        self._resume_btn = Button(
            20, 200, 130, btn_h, "RESUME", self._bold_font, (30, 120, 60), SUCCESS, PANEL_BORDER
        )
        self._stop_btn = Button(
            170, 200, 130, btn_h, "STOP", self._bold_font, (120, 30, 30), DANGER, PANEL_BORDER
        )

        # 4. Search Statistics state
        self._nodes_expanded = 0
        self._nodes_visited = 0
        self._path_length = 0
        self._path_cost = 0.0
        self._elapsed_ms = 0.0
        self._memory_peak = 0
        
        self._open_list_size = 0
        self._closed_list_size = 0
        self._current_depth = 0
        self._current_iteration = 0
        self._belief_state_size = 0
        self._assignments_count = 0
        self._backtracks_count = 0
        self._pruned_count = 0
        self._g_cost = 0.0
        self._h_cost = 0.0
        self._temperature = 0.0

        # Subgoal details
        self._current_subgoal: Optional[Tuple[int, int]] = None
        self._current_subgoal_desc: str = ""
        self._is_stuck = False

        # Subscribe to updates
        self._bus.subscribe(Events.STATS_UPDATED, self._on_stats_updated)
        self._bus.subscribe(Events.AI_STARTED, self._on_ai_started)
        self._bus.subscribe("ai_subgoal_changed", self._on_ai_subgoal_changed)
        self._bus.subscribe("ai_algo_stuck", self._on_ai_stuck)

    def cleanup(self) -> None:
        """Unsubscribe from event channels."""
        self._bus.unsubscribe(Events.STATS_UPDATED, self._on_stats_updated)
        self._bus.unsubscribe(Events.AI_STARTED, self._on_ai_started)
        self._bus.unsubscribe("ai_subgoal_changed", self._on_ai_subgoal_changed)
        self._bus.unsubscribe("ai_algo_stuck", self._on_ai_stuck)

    def _on_ai_stuck(self, algo: Any) -> None:
        self._is_stuck = True


    def _on_stats_updated(self, stats: Any) -> None:
        """Receive live statistics from the running algorithm."""
        self._nodes_expanded = stats.nodes_expanded
        self._nodes_visited = stats.nodes_visited
        self._path_length = stats.path_length
        self._path_cost = stats.path_cost
        self._elapsed_ms = stats.elapsed_ms
        self._memory_peak = getattr(stats, "memory_peak", 0)
        self._open_list_size = getattr(stats, "open_list_size", 0)
        self._closed_list_size = getattr(stats, "closed_list_size", 0)
        self._current_depth = getattr(stats, "current_depth", 0)
        self._current_iteration = getattr(stats, "current_iteration", 0)
        self._belief_state_size = getattr(stats, "belief_state_size", 0)
        self._assignments_count = getattr(stats, "assignments_count", 0)
        self._backtracks_count = getattr(stats, "backtracks_count", 0)
        self._pruned_count = getattr(stats, "pruned_count", 0)
        self._g_cost = getattr(stats, "g_cost", 0.0)
        self._h_cost = getattr(stats, "h_cost", 0.0)
        self._temperature = getattr(stats, "temperature", 0.0)

    def _on_ai_started(self, algorithm_key: str = "", **kwargs: Any) -> None:
        """Reset stats counters when a new AI algorithm begins."""
        self._nodes_expanded = 0
        self._nodes_visited = 0
        self._path_length = 0
        self._path_cost = 0.0
        self._elapsed_ms = 0.0
        self._memory_peak = 0
        self._open_list_size = 0
        self._closed_list_size = 0
        self._current_depth = 0
        self._current_iteration = 0
        self._belief_state_size = 0
        self._assignments_count = 0
        self._backtracks_count = 0
        self._pruned_count = 0
        self._g_cost = 0.0
        self._h_cost = 0.0
        self._temperature = 0.0
        self._current_subgoal = None
        self._current_subgoal_desc = ""
        self._is_stuck = False


    def _on_ai_subgoal_changed(self, target: Tuple[int, int], description: str) -> None:
        """Update current subgoal details."""
        self._current_subgoal = target
        self._current_subgoal_desc = description

    def handle_event(self, event: pygame.event.Event, offset_x: int = 0, offset_y: int = 0) -> None:
        """Forward mouse interaction events to sub-controls."""
        # 1. Forward to dropdown first (it overlays others, so it blocks clicks if expanded)
        dropdown_clicked = self._dropdown.handle_event(event, offset_x, offset_y)
        if self._dropdown.expanded:
            return

        # 2. Forward to slider (only if AI is not active, or let slider change speed dynamically)
        self._slider.handle_event(event, offset_x, offset_y)
        if event.type in {pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP}:
            # Update AI runner speed in real-time
            if self._sm.is_ai_active():
                self._bus.publish("set_ai_speed", speed=self._slider.value)

        # 3. Handle button clicks based on high-level game state
        if self._sm.state == GameState.PLAYING:
            if self._solve_btn.handle_event(event, offset_x, offset_y):
                # Trigger solver startup
                logger.info("AI Solve button clicked.")
                self._bus.publish(
                    Events.AI_START,
                    algorithm_key=self._dropdown.selected_key,
                    speed=self._slider.value,
                )
        elif self._sm.state == GameState.AI_RUNNING:
            if self._pause_btn.handle_event(event, offset_x, offset_y):
                self._bus.publish("ai_pause")
            elif self._stop_btn.handle_event(event, offset_x, offset_y):
                self._bus.publish("ai_stop")
        elif self._sm.state == GameState.AI_PAUSED:
            if self._resume_btn.handle_event(event, offset_x, offset_y):
                self._bus.publish("ai_resume")
            elif self._stop_btn.handle_event(event, offset_x, offset_y):
                self._bus.publish("ai_stop")

    def render(self, surface: pygame.Surface) -> None:
        """Render panel background, header, controls, statistics, and visualization legends."""
        # Background fill
        surface.fill(PANEL_BG)

        # Header Title
        title_surf = self._title_font.render("🤖 AI SOLVER", True, TEXT_PRIMARY)
        surface.blit(title_surf, (20, 20))
        
        # Divider line
        pygame.draw.line(surface, PANEL_BORDER, (10, 60), (310, 60), 2)

        # Draw widgets
        self._slider.render(surface)

        # Render active buttons
        if self._sm.state == GameState.PLAYING:
            self._solve_btn.render(surface)
        elif self._sm.state == GameState.AI_RUNNING:
            self._pause_btn.render(surface)
            self._stop_btn.render(surface)
        elif self._sm.state == GameState.AI_PAUSED:
            self._resume_btn.render(surface)
            self._stop_btn.render(surface)

        # Stats section
        stats_y = 255
        pygame.draw.line(surface, PANEL_BORDER, (10, stats_y - 10), (310, stats_y - 10), 1)

        # Retrieve algorithm metadata
        selected_key = self._dropdown.selected_key
        from config.algorithm_config import ALGORITHM_MAP
        meta = ALGORITHM_MAP.get(selected_key)
        description = meta.description if meta else ""
        category = meta.category if meta else ""

        # ALGORITHM INFO section
        info_hdr = self._bold_font.render("ALGORITHM INFO", True, TEXT_PRIMARY)
        surface.blit(info_hdr, (20, stats_y))
        
        # Draw category badge
        category_surf = self._bold_font.render(category.upper(), True, ACCENT)
        surface.blit(category_surf, (20, stats_y + 20))
        
        # Word wrap description dynamically to fit 280px content area
        desc_lines = wrap_text(description, self._font, 280)
        
        desc_y = stats_y + 40
        for line in desc_lines:
            line_surf = self._font.render(line, True, TEXT_MUTED)
            surface.blit(line_surf, (20, desc_y))
            desc_y += line_surf.get_height() + 4
        
        # Divider between Info and Stats
        stats_y_start = desc_y + 5
        pygame.draw.line(surface, PANEL_BORDER, (10, stats_y_start - 5), (310, stats_y_start - 5), 1)

        stats_hdr = self._bold_font.render("SEARCH STATISTICS", True, TEXT_PRIMARY)
        surface.blit(stats_hdr, (20, stats_y_start))
        
        y = stats_y_start + 25
        y = StatRow("Algorithm:", self._dropdown.selected_name, self._font).render(surface, 20, y)
        y = StatRow("Nodes Expanded:", f"{self._nodes_expanded}", self._font).render(surface, 20, y)
        y = StatRow("Nodes Visited:", f"{self._nodes_visited}", self._font).render(surface, 20, y)
        y = StatRow("Path Length:", f"{self._path_length} steps" if self._path_length > 0 else "—", self._font).render(surface, 20, y)
        y = StatRow("Path Cost:", f"{self._path_cost:.1f}" if self._path_cost > 0 else "—", self._font).render(surface, 20, y)
        y = StatRow("Peak Memory:", f"{self._memory_peak} nodes" if self._memory_peak > 0 else "—", self._font).render(surface, 20, y)
        y = StatRow("Elapsed Time:", f"{self._elapsed_ms:.1f} ms" if self._elapsed_ms > 0 else "—", self._font).render(surface, 20, y)

        # Context-sensitive rows
        cat_lower = category.lower()
        key_lower = selected_key.lower()

        def fmt_val(v: Any, suffix: str = "") -> str:
            if not v or v == 0 or v == 0.0:
                return "—"
            return f"{v}{suffix}"

        if "uninformed" in cat_lower or "informed" in cat_lower:
            y = StatRow("Open / Closed:", f"{fmt_val(self._open_list_size)} / {fmt_val(self._closed_list_size)}", self._font).render(surface, 20, y)
        
        if "astar" in key_lower or "greedy" in key_lower:
            g_str = f"{self._g_cost:.1f}" if self._g_cost > 0 else "—"
            h_str = f"{self._h_cost:.1f}" if self._h_cost > 0 else "—"
            y = StatRow("g(n) / h(n):", f"{g_str} / {h_str}", self._font).render(surface, 20, y)
        elif "dfs" in key_lower or "iddfs" in key_lower:
            y = StatRow("Depth / Iter:", f"{fmt_val(self._current_depth)} / {fmt_val(self._current_iteration)}", self._font).render(surface, 20, y)
        elif "local" in cat_lower:
            if "annealing" in key_lower:
                y = StatRow("Temperature:", f"{self._temperature:.2f}°" if self._temperature > 0 else "—", self._font).render(surface, 20, y)
            elif "beam" in key_lower:
                from config.algorithm_config import ALGORITHM_MAP
                beam_w = ALGORITHM_MAP.get("local_beam").params.get("beam_width", 4)
                y = StatRow("Beam Width:", f"{beam_w}", self._font).render(surface, 20, y)
        elif "no_observation" in key_lower:
            y = StatRow("Belief States:", f"{fmt_val(self._belief_state_size)}", self._font).render(surface, 20, y)
        elif "constraint" in cat_lower or "backtracking" in key_lower or "min_conflicts" in key_lower:
            y = StatRow("Assign / Back:", f"{fmt_val(self._assignments_count)} / {fmt_val(self._backtracks_count)}", self._font).render(surface, 20, y)
        elif "alpha_beta" in key_lower:
            y = StatRow("Pruned Nodes:", f"{fmt_val(self._pruned_count)}", self._font).render(surface, 20, y)

        # CURRENT GOAL section
        goal_y = y + 5
        pygame.draw.line(surface, PANEL_BORDER, (10, goal_y - 10), (310, goal_y - 10), 1)
        goal_hdr = self._bold_font.render("CURRENT GOAL", True, TEXT_PRIMARY)
        surface.blit(goal_hdr, (20, goal_y))
        
        goal_desc = self._current_subgoal_desc if self._current_subgoal_desc else "No active AI goal"
        # If no active subgoal desc, but we have mission system, get the first uncompleted mission step
        if not self._current_subgoal_desc and self._mission_system:
            step = self._mission_system.get_current_step()
            if step:
                goal_desc = f"{step.icon} {step.description}"
        goal_pos_str = f"({self._current_subgoal[0]}, {self._current_subgoal[1]})" if self._current_subgoal else "N/A"
        
        y = goal_y + 25
        y = StatRow("Goal:", goal_desc, self._font).render(surface, 20, y)
        y = StatRow("Target Pos:", goal_pos_str, self._font).render(surface, 20, y)

        # WARNING box: Hill Climbing stuck at local optimum
        if self._is_stuck:
            warn_box_y = y + 4
            warn_h = 44
            warn_rect = pygame.Rect(10, warn_box_y, 300, warn_h)
            pygame.draw.rect(surface, (90, 45, 5), warn_rect, border_radius=6)
            pygame.draw.rect(surface, (180, 100, 20), warn_rect, 2, border_radius=6)
            # Title line
            title_surf = self._font.render("⚠ Mắc kẹt điểm cực trị cục bộ!", True, (255, 185, 50))
            surface.blit(title_surf, (18, warn_box_y + 4))
            # Hint line
            hint_surf = self._font.render("  Hãy thử Simulated Annealing.", True, (220, 160, 60))
            surface.blit(hint_surf, (18, warn_box_y + 22))
            y = warn_box_y + warn_h + 4


        mission_y = y + 5
        pygame.draw.line(surface, PANEL_BORDER, (10, mission_y - 10), (310, mission_y - 10), 1)
        mission_hdr = self._bold_font.render("MISSION PROGRESS", True, TEXT_PRIMARY)
        surface.blit(mission_hdr, (20, mission_y))
        
        y = mission_y + 25
        if self._mission_system and self._mission_system.steps:
            for step in self._mission_system.steps:
                status_char = "✓" if step.completed else "○"
                status_color = SUCCESS if step.completed else TEXT_MUTED
                
                # Render step checkmark and description
                chk_surf = self._bold_font.render(status_char, True, status_color)
                surface.blit(chk_surf, (20, y))
                
                # Wrap description to fit the available space (260px)
                desc_lines = wrap_text(step.description, self._font, 260)
                for i, line in enumerate(desc_lines):
                    desc_surf = self._font.render(line, True, TEXT_PRIMARY if not step.completed else TEXT_MUTED)
                    surface.blit(desc_surf, (40, y))
                    y += desc_surf.get_height() + 4
        else:
            no_mission_surf = self._font.render("No active missions", True, TEXT_MUTED)
            surface.blit(no_mission_surf, (20, y))
            y += 20

        # Legend Section
        legend_y = y + 5
        pygame.draw.line(surface, PANEL_BORDER, (10, legend_y - 10), (310, legend_y - 10), 1)

        legend_hdr = self._bold_font.render("VISUALIZATION LEGEND", True, TEXT_PRIMARY)
        surface.blit(legend_hdr, (20, legend_y))

        # Helper to draw legend rows
        def draw_legend_row(color: Tuple[int, int, int], text: str, row_y: int) -> int:
            pygame.draw.rect(surface, color, (20, row_y, 16, 16), border_radius=3)
            pygame.draw.rect(surface, PANEL_BORDER, (20, row_y, 16, 16), 1, border_radius=3)
            row_text = self._font.render(text, True, TEXT_MUTED)
            surface.blit(row_text, (48, row_y - 1))
            return row_y + 20

        ly = legend_y + 25
        ly = draw_legend_row((50, 100, 200), "Đã duyệt (Visited)", ly)
        ly = draw_legend_row((255, 165, 0), "Tập biên (Frontier)", ly)
        ly = draw_legend_row((80, 200, 120), "Đường đi (Path)", ly)


        # Render dropdown last so its expanded options list overlays everything else
        self._dropdown.render(surface)
