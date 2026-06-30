"""
stats_scene.py — Level statistics comparison scene with charts, algorithm comparison table,
star rating bars, and Markdown export.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pygame

from config.settings import (
    DARK_BG,
    PANEL_BG,
    PANEL_BORDER,
    TEXT_PRIMARY,
    TEXT_MUTED,
    SUCCESS,
    ACCENT,
    ACCENT_HOVER,
    WARNING,
    SAVES_DIR,
)
from core.event_bus import EventBus
from core.state_machine import GameState, StateMachine
from scene.base_scene import BaseScene
from ui.widgets import Button
from audio import play_music

logger = logging.getLogger(__name__)

# Columns shown in the algorithm comparison table
_TABLE_COLS = ["Algorithm", "Nodes", "Cost", "Time", "Steps", "⭐"]
_COL_WIDTHS  = [160, 80, 80, 80, 80, 60]   # px, must sum ≈ 540
_TABLE_ROW_H = 24
_MAX_ROWS     = 8

# Star mini-bar palette
_BAR_COLORS = {
    "treasure": (255, 200, 40),
    "hp":       (80, 200, 120),
    "speed":    (90, 160, 255),
}


class StatsScene(BaseScene):
    """Shows comparative charts (Human vs AI) for time, path length, and nodes expanded,
    plus an algorithm comparison table and Markdown export.
    """

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        game_surface: pygame.Surface,
        panel_surface: pygame.Surface,
        level_id: int,
        run_stats: Dict[str, Any],   # current run stats
        history_stats: Dict[str, Any],  # historical comparisons
    ) -> None:
        super().__init__(bus, state_machine, game_surface)
        self._panel_surface = panel_surface
        self._level_id = level_id
        self._run_stats = run_stats
        self._history = history_stats

        # Fonts
        self._title_font = pygame.font.SysFont("consolas", 24, bold=True)
        self._bold_font  = pygame.font.SysFont("consolas", 16, bold=True)
        self._font       = pygame.font.SysFont("consolas", 15)
        self._small_font = pygame.font.SysFont("consolas", 12)

        # Buttons (panel-relative coordinates)
        btn_w, btn_h = 280, 42
        self._next_btn = Button(
            20, 100, btn_w, btn_h, "NEXT LEVEL", self._bold_font, (30, 120, 60), SUCCESS, PANEL_BORDER
        )
        self._retry_btn = Button(
            20, 160, btn_w, btn_h, "PLAY AGAIN", self._bold_font, (30, 60, 120), ACCENT_HOVER, PANEL_BORDER
        )
        self._menu_btn = Button(
            20, 220, btn_w, btn_h, "LEVEL SELECT", self._bold_font, (40, 45, 60), (60, 65, 80), PANEL_BORDER
        )
        self._export_btn = Button(
            20, 290, btn_w, btn_h, "📄 EXPORT REPORT", self._bold_font, (35, 35, 55), (70, 60, 100), PANEL_BORDER
        )

        # Export confirmation message state
        self._export_msg: str = ""
        self._export_msg_timer: float = 0.0

        # Cached algorithm results (loaded lazily from StatsTracker on first render)
        self._algo_results: Optional[Dict[str, Any]] = None

        logger.info("StatsScene loaded for Level %d.", level_id)

    # ------------------------------------------------------------------
    # Algorithm data helpers
    # ------------------------------------------------------------------

    def _get_algo_results(self) -> Dict[str, Any]:
        """Return best-run dict per algo key for the current level."""
        if self._algo_results is not None:
            return self._algo_results

        try:
            from systems.stats_tracker import StatsTracker
            tracker = StatsTracker()
            raw = tracker.get_all_algorithm_results(self._level_id)
            # Convert RunStats dataclasses to plain dicts for easy rendering
            self._algo_results = {
                k: {
                    "algorithm_key": v.algorithm_key,
                    "is_ai": v.is_ai,
                    "nodes_expanded": v.nodes_expanded,
                    "path_cost": v.path_cost,
                    "time_elapsed": v.time_elapsed,
                    "steps_taken": v.steps_taken,
                    "star_rating": v.star_rating,
                    "hp_remaining": v.hp_remaining,
                    "treasures_collected": v.treasures_collected,
                    "treasures_total": v.treasures_total,
                    "completion_pct": v.completion_pct,
                }
                for k, v in raw.items()
            }
        except Exception:
            logger.exception("Failed to load algorithm results for StatsScene")
            self._algo_results = {}

        return self._algo_results

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        play_music("tunic_menu.mp3")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route mouse clicks to buttons."""
        self._next_btn.handle_event(event, offset_x=960)
        self._retry_btn.handle_event(event, offset_x=960)
        self._menu_btn.handle_event(event, offset_x=960)
        self._export_btn.handle_event(event, offset_x=960)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            mx -= 960

            if self._next_btn.rect.collidepoint(mx, my):
                from config.level_config import LEVEL_MAP
                next_level_id = self._level_id + 1
                if next_level_id in LEVEL_MAP:
                    self._bus.publish("load_level", level_id=next_level_id)
                else:
                    self._sm.transition(GameState.LEVEL_SELECT)
            elif self._retry_btn.rect.collidepoint(mx, my):
                self._bus.publish("load_level", level_id=self._level_id)
            elif self._menu_btn.rect.collidepoint(mx, my):
                self._sm.transition(GameState.LEVEL_SELECT)
            elif self._export_btn.rect.collidepoint(mx, my):
                self._export_report()

    def update(self, dt: float) -> None:
        if self._export_msg_timer > 0:
            self._export_msg_timer -= dt

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_star(
        self,
        surface: pygame.Surface,
        color: Tuple[int, int, int],
        center: Tuple[float, float],
        size: float,
    ) -> None:
        """Draw a 5-pointed star polygon."""
        points = []
        for i in range(10):
            r = size if i % 2 == 0 else size / 2.0
            angle = i * math.pi / 5.0 - math.pi / 2.0
            points.append((center[0] + r * math.cos(angle), center[1] + r * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)

    def _draw_bar(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        val_human: float,
        val_ai: float,
        unit: str,
    ) -> None:
        """Draw comparative human vs AI horizontal bar charts."""
        pygame.draw.rect(surface, (20, 22, 35), (x, y, w, h), border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, (x, y, w, h), 1, border_radius=6)

        lbl_surf = self._bold_font.render(label, True, TEXT_PRIMARY)
        surface.blit(lbl_surf, (x + 12, y + 8))

        max_val = max(val_human, val_ai, 1.0)
        bar_max_w = w - 160

        # Human bar (Blue)
        hy = y + 32
        val_h_w = int(bar_max_w * (val_human / max_val)) if max_val > 0 else 0
        pygame.draw.rect(surface, (40, 100, 200), (x + 12, hy, val_h_w, 14), border_radius=3)
        h_lbl = self._font.render(f"Human: {val_human:.1f}{unit}", True, TEXT_MUTED)
        surface.blit(h_lbl, (x + 12 + bar_max_w + 8, hy - 2))

        # AI bar (Orange)
        ay = y + 52
        val_ai_w = int(bar_max_w * (val_ai / max_val)) if max_val > 0 else 0
        pygame.draw.rect(surface, (240, 120, 30), (x + 12, ay, val_ai_w, 14), border_radius=3)
        ai_lbl = self._font.render(f"AI:    {val_ai:.1f}{unit}", True, TEXT_MUTED)
        surface.blit(ai_lbl, (x + 12 + bar_max_w + 8, ay - 2))

    def _draw_mini_star_bars(self, surface: pygame.Surface, x: int, y: int) -> None:
        """Draw 3 mini star-rating progress bars: Treasure / HP / Speed."""
        treasures_pct = self._run_stats.get("treasures_pct", 0.0)
        hp_pct        = self._run_stats.get("hp_pct", 0.0)
        time_taken    = self._run_stats.get("time", 0.0)
        # Speed: invert time (0–120 s range; 120+ → 0%)
        speed_pct = max(0.0, min(100.0, (1.0 - time_taken / 120.0) * 100.0)) if time_taken > 0 else 100.0

        bars = [
            ("Treasure", treasures_pct, _BAR_COLORS["treasure"]),
            ("HP",       hp_pct,        _BAR_COLORS["hp"]),
            ("Speed",    speed_pct,     _BAR_COLORS["speed"]),
        ]

        bar_w   = 200
        bar_h   = 14
        spacing = 50
        label_w = 70

        title = self._bold_font.render("⭐ STAR BREAKDOWN", True, WARNING)
        surface.blit(title, (x, y))

        for i, (lbl, pct, color) in enumerate(bars):
            bx = x
            by = y + 28 + i * spacing

            # Label
            lbl_s = self._font.render(lbl, True, TEXT_MUTED)
            surface.blit(lbl_s, (bx, by + 1))

            # Background track
            pygame.draw.rect(surface, (30, 32, 48), (bx + label_w, by, bar_w, bar_h), border_radius=4)
            # Fill
            fill_w = int(bar_w * max(0.0, min(1.0, pct / 100.0)))
            if fill_w > 0:
                pygame.draw.rect(surface, color, (bx + label_w, by, fill_w, bar_h), border_radius=4)
            # Border
            pygame.draw.rect(surface, PANEL_BORDER, (bx + label_w, by, bar_w, bar_h), 1, border_radius=4)
            # Pct label
            pct_s = self._small_font.render(f"{pct:.0f}%", True, TEXT_PRIMARY)
            surface.blit(pct_s, (bx + label_w + bar_w + 6, by + 1))

    def _draw_algorithm_table(self, surface: pygame.Surface, x: int, y: int, table_w: int) -> None:
        """Draw the algorithm comparison table (best run per algorithm)."""
        algo_results = self._get_algo_results()
        if not algo_results:
            no_data = self._font.render("No algorithm runs recorded for this level yet.", True, TEXT_MUTED)
            surface.blit(no_data, (x + 10, y + 10))
            return

        # Sort by path_cost ascending; take up to _MAX_ROWS
        rows: List[Dict[str, Any]] = sorted(
            algo_results.values(), key=lambda d: d.get("path_cost", 999999.0)
        )[:_MAX_ROWS]

        best_cost = rows[0].get("path_cost", 0.0) if rows else 0.0

        row_h  = _TABLE_ROW_H
        col_ws = _COL_WIDTHS
        total_col_w = sum(col_ws)
        # Scale column widths proportionally to fit table_w
        scale = table_w / max(total_col_w, 1)
        col_ws = [max(40, int(cw * scale)) for cw in col_ws]

        # Header
        hdr_y = y
        pygame.draw.rect(surface, (25, 28, 45), (x, hdr_y, table_w, row_h), border_radius=4)
        cx = x + 4
        for col_lbl, cw in zip(_TABLE_COLS, col_ws):
            hdr_surf = self._small_font.render(col_lbl, True, WARNING)
            surface.blit(hdr_surf, (cx, hdr_y + 5))
            cx += cw
        pygame.draw.line(surface, PANEL_BORDER, (x, hdr_y + row_h), (x + table_w, hdr_y + row_h), 1)

        # Data rows
        for r_idx, row in enumerate(rows):
            ry = hdr_y + row_h * (r_idx + 1)
            is_best = abs(row.get("path_cost", 999999.0) - best_cost) < 0.001

            # Row background — gold tint for best, alternating dark for rest
            if is_best:
                bg_col = (40, 35, 10)
            elif r_idx % 2 == 0:
                bg_col = (18, 20, 30)
            else:
                bg_col = (22, 25, 38)
            pygame.draw.rect(surface, bg_col, (x, ry, table_w, row_h))

            # Cell values
            algo_display = row.get("algorithm_key", "?") or ("AI" if row.get("is_ai") else "Human")
            # Truncate to fit column
            algo_display = algo_display[:18]
            cells = [
                algo_display,
                str(row.get("nodes_expanded", 0)),
                f"{row.get('path_cost', 0.0):.1f}",
                f"{row.get('time_elapsed', 0.0):.1f}s",
                str(row.get("steps_taken", 0)),
                "★" * row.get("star_rating", 1),
            ]

            text_col = (255, 215, 0) if is_best else TEXT_PRIMARY
            cx = x + 4
            for cell, cw in zip(cells, col_ws):
                cell_surf = self._small_font.render(cell, True, text_col)
                surface.blit(cell_surf, (cx, ry + 6))
                cx += cw

            # Separator line
            pygame.draw.line(surface, (30, 33, 50), (x, ry + row_h - 1), (x + table_w, ry + row_h - 1), 1)

        # Table border
        total_h = row_h * (len(rows) + 1)
        pygame.draw.rect(surface, PANEL_BORDER, (x, y, table_w, total_h), 1, border_radius=4)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_report(self) -> None:
        """Generate a Markdown report file in saves/reports/."""
        try:
            reports_dir = os.path.join(SAVES_DIR, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            filename = f"level_{self._level_id}_report.md"
            file_path = os.path.join(reports_dir, filename)

            algo_results = self._get_algo_results()
            rows: List[Dict[str, Any]] = sorted(
                algo_results.values(), key=lambda d: d.get("path_cost", 999999.0)
            )

            lines = [
                f"# Level {self._level_id} Statistics Report\n",
                "_Generated by Treasure Hunter AI_\n",
                "",
                "## Algorithm Comparison\n",
                "| Algorithm | Nodes | Cost | Time (s) | Steps | Stars |",
                "|-----------|-------|------|----------|-------|-------|",
            ]
            for row in rows:
                algo = row.get("algorithm_key", "?") or ("AI" if row.get("is_ai") else "Human")
                lines.append(
                    f"| {algo} | {row.get('nodes_expanded', 0)} | "
                    f"{row.get('path_cost', 0.0):.1f} | "
                    f"{row.get('time_elapsed', 0.0):.1f} | "
                    f"{row.get('steps_taken', 0)} | "
                    f"{'★' * row.get('star_rating', 1)} |"
                )

            hist = self._history.get(self._level_id, {})
            human = hist.get("human", {})
            ai    = hist.get("ai", {})

            lines += [
                "",
                "## Human vs AI Summary\n",
                f"| Metric | Human | AI |",
                f"|--------|-------|----|",
                f"| Path Cost   | {human.get('cost', 0.0):.1f} | {ai.get('cost', 0.0):.1f} |",
                f"| Time (s)    | {human.get('time', 0.0):.1f} | {ai.get('time', 0.0):.1f} |",
                f"| Steps       | {human.get('steps_taken', 0)} | {ai.get('steps_taken', 0)} |",
                f"| Treasure %  | {human.get('treasures_pct', 0.0):.1f}% | {ai.get('treasures_pct', 0.0):.1f}% |",
                f"| HP %        | {human.get('hp_pct', 100.0):.1f}% | {ai.get('hp_pct', 100.0):.1f}% |",
                "",
                "---",
                f"_Exported from Treasure Hunter AI — Level {self._level_id}_",
            ]

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            self._export_msg = f"Saved to reports/{filename}"
            self._export_msg_timer = 4.0
            logger.info("Report exported to %s", file_path)

        except Exception:
            logger.exception("Failed to export stats report")
            self._export_msg = "Export failed — check logs"
            self._export_msg_timer = 3.0

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        """Render charts, star rating bars, and algorithm comparison table."""
        surface.fill(DARK_BG)

        # Header Title
        title_surf = self._title_font.render(
            f"LEVEL {self._level_id} COMPLETE — COMPARATIVE STATISTICS", True, WARNING
        )
        surface.blit(title_surf, title_surf.get_rect(center=(960 // 2, 30)))

        # Load historical metrics for current level
        hist = self._history.get(self._level_id, {})
        human_data = hist.get("human", {"time": 0.0, "cost": 0.0, "nodes": 0, "steps_taken": 0, "treasures_pct": 0.0, "hp_pct": 100.0})
        ai_data    = hist.get("ai",    {"time": 0.0, "cost": 0.0, "nodes": 0, "steps_taken": 0, "treasures_pct": 0.0, "hp_pct": 100.0})

        # --- Bar Charts (2-column layout) ---
        cx1, cx2 = 30, 495
        cy       = 60
        chart_w  = 430
        chart_h  = 80
        spacing  = 90

        self._draw_bar(surface, cx1, cy, chart_w, chart_h, "Path Move Cost (lower is better)",   human_data.get("cost", 0.0),             ai_data.get("cost", 0.0),             "pts")
        self._draw_bar(surface, cx2, cy, chart_w, chart_h, "Steps Taken (lower is better)",      float(human_data.get("steps_taken", 0)), float(ai_data.get("steps_taken", 0)), "steps")

        self._draw_bar(surface, cx1, cy + spacing, chart_w, chart_h, "Execution Time (lower is better)",     human_data.get("time", 0.0),          ai_data.get("time", 0.0),          "s")
        self._draw_bar(surface, cx2, cy + spacing, chart_w, chart_h, "Treasures Collected (higher is better)", human_data.get("treasures_pct", 0.0), ai_data.get("treasures_pct", 0.0), "%")

        self._draw_bar(surface, cx1, cy + 2 * spacing, chart_w, chart_h, "Search Nodes Expanded (lower is better)", float(human_data.get("nodes", 0)), float(ai_data.get("nodes", 0)), "nodes")
        self._draw_bar(surface, cx2, cy + 2 * spacing, chart_w, chart_h, "HP Remaining % (higher is better)",       human_data.get("hp_pct", 100.0),   ai_data.get("hp_pct", 100.0),   "%")

        # --- Star Mini-Bars (below charts) ---
        star_bar_y = cy + 3 * spacing + 5
        self._draw_mini_star_bars(surface, 30, star_bar_y)

        # --- Classic 3-star rating (current run) ---
        current_mode  = "AI" if self._run_stats.get("is_ai") else "Human"
        treasures_pct = self._run_stats.get("treasures_pct", 100.0)
        hp_pct        = self._run_stats.get("hp_pct", 100.0)

        if treasures_pct >= 99.0 and hp_pct >= 50.0:
            stars = 3
        elif treasures_pct >= 50.0 or hp_pct >= 30.0:
            stars = 2
        else:
            stars = 1

        rating_lbl = self._bold_font.render(f"Current {current_mode} Run:", True, TEXT_PRIMARY)
        surface.blit(rating_lbl, (530, star_bar_y + 2))
        star_size    = 14.0
        star_spacing = 38
        start_x      = 530 + rating_lbl.get_width() + 16
        for i in range(3):
            color = (255, 215, 0) if i < stars else (50, 50, 60)
            self._draw_star(surface, color, (start_x + i * star_spacing, star_bar_y + 14), star_size)

        # --- Algorithm Comparison Table ---
        table_section_y = star_bar_y + 185
        section_title = self._bold_font.render("📊 ALGORITHM COMPARISON", True, (130, 180, 255))
        surface.blit(section_title, (30, table_section_y))
        self._draw_algorithm_table(surface, 30, table_section_y + 24, 900)

        # --- Performance Insight box (below table) ---
        table_rows = min(_MAX_ROWS, len(self._get_algo_results()))
        table_total_h = _TABLE_ROW_H * (table_rows + 1) + 24
        insight_y   = table_section_y + table_total_h + 12
        insight_box_w = 900
        insight_box_h = 80

        # Only draw if there is room
        if insight_y + insight_box_h < surface.get_height() - 20:
            pygame.draw.rect(surface, (15, 17, 28), (30, insight_y, insight_box_w, insight_box_h), border_radius=8)
            pygame.draw.rect(surface, PANEL_BORDER, (30, insight_y, insight_box_w, insight_box_h), 1, border_radius=8)

            ins_title = self._bold_font.render("💡 PERFORMANCE INSIGHT", True, WARNING)
            surface.blit(ins_title, (50, insight_y + 10))

            human_cost = human_data.get("cost", 0.0)
            ai_cost    = ai_data.get("cost", 0.0)
            human_time = human_data.get("time", 0.0)
            ai_time    = ai_data.get("time", 0.0)

            insights = []
            if human_cost == 0 or ai_cost == 0:
                insights.append("• Play the level in both Human and AI modes to generate full comparative reports.")
            else:
                if ai_cost < human_cost:
                    insights.append(f"• AI achieved a lower path cost ({ai_cost:.1f} vs {human_cost:.1f}), demonstrating search optimality.")
                elif human_cost < ai_cost:
                    insights.append(f"• Human navigated with lower cost ({human_cost:.1f} vs {ai_cost:.1f}) via adaptive exploration.")
                else:
                    insights.append("• AI and Human achieved identical path cost efficiency.")

                if ai_time < human_time and ai_time > 0:
                    speedup = human_time / ai_time
                    insights.append(f"• AI executed the path {speedup:.1f}x faster than human response times.")

            if not insights:
                insights.append("• No run history yet. Complete the level in both Human and AI modes!")

            y_text = insight_y + 32
            for ins in insights[:2]:
                ins_surf = self._font.render(ins, True, TEXT_PRIMARY)
                surface.blit(ins_surf, (50, y_text))
                y_text += 22

        # Bottom tip
        tip_surf = self._font.render(
            "Run the level again in both Human and AI modes to update comparison charts!", True, WARNING
        )
        surface.blit(tip_surf, tip_surf.get_rect(center=(960 // 2, surface.get_height() - 12)))

    def render_panel(self, panel: pygame.Surface) -> None:
        """Render panel buttons and export controls."""
        panel.fill(PANEL_BG)

        # Header
        title_surf = self._title_font.render("VICTORY!", True, SUCCESS)
        panel.blit(title_surf, (20, 20))
        pygame.draw.line(panel, PANEL_BORDER, (10, 60), (310, 60), 2)

        # Navigation buttons
        self._next_btn.render(panel)
        self._retry_btn.render(panel)
        self._menu_btn.render(panel)

        # Export button
        self._export_btn.render(panel)

        # Export confirmation message
        if self._export_msg and self._export_msg_timer > 0:
            alpha = min(1.0, self._export_msg_timer) * 255
            msg_surf = self._small_font.render(self._export_msg, True, (120, 220, 120))
            msg_surf.set_alpha(int(alpha))
            panel.blit(msg_surf, (20, 342))

        # --- Panel: Algorithm summary list ---
        section_y = 380
        sep_lbl = self._bold_font.render("RECENT ALGORITHM RUNS", True, (100, 140, 200))
        panel.blit(sep_lbl, (20, section_y))
        pygame.draw.line(panel, PANEL_BORDER, (10, section_y + 22), (310, section_y + 22), 1)

        algo_results = self._get_algo_results()
        if not algo_results:
            no_data = self._small_font.render("No runs recorded yet.", True, TEXT_MUTED)
            panel.blit(no_data, (20, section_y + 30))
        else:
            sorted_rows = sorted(algo_results.values(), key=lambda d: d.get("path_cost", 999999.0))
            best_cost = sorted_rows[0].get("path_cost", 0.0) if sorted_rows else 0.0
            y_off = section_y + 28
            for row in sorted_rows[:6]:
                is_best = abs(row.get("path_cost", 999999.0) - best_cost) < 0.001
                col = (255, 215, 0) if is_best else TEXT_MUTED
                algo = row.get("algorithm_key", "?") or ("AI" if row.get("is_ai") else "Human")
                line = f"{'★ ' if is_best else '  '}{algo[:16]:16s}  {row.get('path_cost', 0.0):.0f}pt"
                lbl = self._small_font.render(line, True, col)
                panel.blit(lbl, (20, y_off))
                y_off += 18
