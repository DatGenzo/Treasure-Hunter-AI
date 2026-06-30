"""
combat_scene.py — Turn-based combat arena using adversarial search algorithms.
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any, List, Optional, Tuple

import pygame

from algorithms.adversarial.combat_rules import (
    CombatState,
    evaluate_state,
    get_actions,
    get_successor,
)
from algorithms import create_algorithm
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
    HP_RED,
    HP_GREEN,
)
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine
from entities.monster import Monster
from entities.player import Player
from scene.base_scene import BaseScene
from ui.widgets import Button, Dropdown, StatRow, wrap_text, InGameMenu

logger = logging.getLogger(__name__)


class CombatScene(BaseScene):
    """Combat arena where Player fights a Monster. Supports manual actions or Adversarial AI solves."""

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        game_surface: pygame.Surface,
        panel_surface: pygame.Surface,
        player: Player,
        monster: Monster,
        auto_resume_ai: bool = False,
    ) -> None:
        super().__init__(bus, state_machine, game_surface)
        self._panel_surface = panel_surface
        self._player_entity = player
        self._monster_entity = monster
        self._auto_resume_ai = auto_resume_ai

        # Initialize combat state
        self._state = CombatState(
            player_hp=self._player_entity.hp,
            player_pos=1,
            monster_hp=self._monster_entity.hp,
            monster_pos=5,
            is_player_turn=True,
            player_dodging=False,
            monster_dodging=False,
        )

        # Fonts
        self._title_font = pygame.font.SysFont("consolas", 24, bold=True)
        self._font = pygame.font.SysFont("consolas", 16)
        self._bold_font = pygame.font.SysFont("consolas", 16, bold=True)
        self._large_font = pygame.font.SysFont("consolas", 20, bold=True)

        # AI solvers dropdown
        ai_options = [
            ("minimax", "Minimax Search"),
            ("alpha_beta", "Alpha-Beta Pruning"),
            ("expectimax", "Expectimax Search"),
        ]
        self._ai_dropdown = Dropdown(20, 100, 280, 36, ai_options, self._font)

        # UI Control buttons (drawn on panel side)
        btn_w, btn_h = 130, 40
        self._attack_btn = Button(20, 150, btn_w, btn_h, "ATTACK", self._bold_font, (120, 30, 30), DANGER, PANEL_BORDER)
        self._dodge_btn = Button(170, 150, btn_w, btn_h, "DODGE", self._bold_font, (30, 120, 60), SUCCESS, PANEL_BORDER)
        self._move_l_btn = Button(20, 200, btn_w, btn_h, "MOVE LEFT", self._bold_font, (40, 45, 60), ACCENT_HOVER, PANEL_BORDER)
        self._move_r_btn = Button(170, 200, btn_w, btn_h, "MOVE RIGHT", self._bold_font, (40, 45, 60), ACCENT_HOVER, PANEL_BORDER)

        self._ai_solve_btn = Button(20, 260, 280, 42, "AI SOLVE TURN", self._bold_font, (30, 60, 120), ACCENT_HOVER, PANEL_BORDER)

        # Turn log feedback
        self._combat_log: List[str] = ["Combat started! Player turn."]

        # Timer for monster turns
        self._monster_turn_timer = 0.0
        self._monster_turn_delay = 1.0  # seconds

        # Visual overlays stats
        self._tree_depth = 2
        self._nodes_evaluated = 0
        self._best_action = ""
        self._pruned_count = 0
        self._tree_nodes = []
        self._pruned_nodes = []
        self._expected_values = {}

        self._ingame_menu = InGameMenu(self._bus, self._sm)
        logger.info("CombatScene successfully loaded.")

    def on_enter(self) -> None:
        logger.info("Entering CombatScene.")
        self._bus.publish(Events.COMBAT_STARTED)

    def on_exit(self) -> None:
        logger.info("Exiting CombatScene.")
        self._bus.publish(Events.COMBAT_ENDED)
        if self._sm.state == GameState.COMBAT:
            if getattr(self, '_auto_resume_ai', False) and self._state.player_hp > 0:
                self._sm.transition(GameState.AI_PAUSED)
                self._bus.publish("ai_resume")
            elif self._state.player_hp > 0:
                self._sm.transition(GameState.PLAYING)

    def _add_log(self, text: str) -> None:
        self._combat_log.append(text)
        if len(self._combat_log) > 6:
            self._combat_log.pop(0)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route clicks to AI dropdown, combat buttons, or AI solve commands."""
        # 0. Forward to in-game menu first
        if self._ingame_menu.handle_event(event):
            return
        # 1. Forward events to dropdown first
        if self._ai_dropdown.handle_event(event, offset_x=960):
            return
        if self._ai_dropdown.expanded:
            return

        # 2. Forward to other buttons
        self._attack_btn.handle_event(event, offset_x=960)
        self._dodge_btn.handle_event(event, offset_x=960)
        self._move_l_btn.handle_event(event, offset_x=960)
        self._move_r_btn.handle_event(event, offset_x=960)
        self._ai_solve_btn.handle_event(event, offset_x=960)

        # Only process input if it's Player's turn
        if self._state.is_player_turn and self._state.player_hp > 0 and self._state.monster_hp > 0:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                mx -= 960

                action = None
                if self._attack_btn.rect.collidepoint(mx, my):
                    action = "ATTACK"
                elif self._dodge_btn.rect.collidepoint(mx, my):
                    action = "DODGE"
                elif self._move_l_btn.rect.collidepoint(mx, my):
                    action = "MOVE_L"
                elif self._move_r_btn.rect.collidepoint(mx, my):
                    action = "MOVE_R"
                
                if action:
                    self._execute_player_action(action)
                    return

                if self._ai_solve_btn.rect.collidepoint(mx, my):
                    self._execute_ai_turn()
                    return

    def _execute_player_action(self, action: str) -> None:
        """Apply player move, log feedback, and check victory conditions."""
        old_m_hp = self._state.monster_hp
        old_p_pos = self._state.player_pos
        
        self._state = get_successor(self._state, action)
        
        # Log action
        if action == "ATTACK":
            dmg = old_m_hp - self._state.monster_hp
            if dmg > 0:
                self._add_log(f"Player dealt {dmg} damage to Monster!")
            else:
                self._add_log("Player attacked but missed (out of range)!")
        elif action == "DODGE":
            self._add_log("Player prepares to dodge!")
        elif action == "MOVE_L":
            if self._state.player_pos != old_p_pos:
                self._add_log("Player moves left.")
            else:
                self._add_log("Player tries to move left but is blocked!")
        elif action == "MOVE_R":
            if self._state.player_pos != old_p_pos:
                self._add_log("Player moves right.")
            else:
                self._add_log("Player tries to move right but is blocked!")

        self._check_combat_status()

    def _execute_ai_turn(self) -> None:
        """Run selected adversarial search algorithm to decide player action."""
        logger.info("Executing Adversarial Search AI for Player's turn.")
        algo_key = self._ai_dropdown.selected_key
        
        # Create solver instance
        algo = create_algorithm(algo_key)
        # Type safety: set combat state
        if hasattr(algo, "set_combat_state"):
            algo.set_combat_state(self._state)
            
            # Step the solver
            res = algo.step()
            action = res.action

            # Update stats for visualization
            if res.vis_data:
                self._tree_depth = res.vis_data.get("tree_depth", 2)
                self._nodes_evaluated = res.vis_data.get("nodes_evaluated", 0)
                self._best_action = res.vis_data.get("best_action", "")
                self._pruned_count = res.vis_data.get("pruned_count", 0)
                self._tree_nodes = res.vis_data.get("tree_nodes", [])
                self._pruned_nodes = res.vis_data.get("pruned_nodes", [])
                self._expected_values = res.vis_data.get("expected_values", {})

            self._add_log(f"🤖 AI solver '{algo_key.upper()}' chose: {action}")
            self._execute_player_action(action)

    def _execute_monster_turn(self) -> None:
        """Decide monster action: 70% optimal, 30% random."""
        if self._state.player_hp <= 0 or self._state.monster_hp <= 0:
            return

        actions = get_actions()
        
        # Evaluate all monster actions (Monster wants to minimize player utility)
        evaluated = []
        for act in actions:
            succ = get_successor(self._state, act)
            val = evaluate_state(succ)
            evaluated.append((act, val))
            
        # Sort ascending (lowest player utility is optimal for monster)
        evaluated.sort(key=lambda item: item[1])
        optimal_action = evaluated[0][0]

        # 70% optimal, 30% random choice
        if random.random() < 0.7:
            chosen = optimal_action
        else:
            chosen = random.choice(actions)

        # Apply action
        old_p_hp = self._state.player_hp
        old_m_pos = self._state.monster_pos
        self._state = get_successor(self._state, chosen)

        # Log action
        if chosen == "ATTACK":
            dmg = old_p_hp - self._state.player_hp
            if dmg > 0:
                self._add_log(f"Monster dealt {dmg} damage to Player!")
            else:
                self._add_log("Monster attacked but missed!")
        elif chosen == "DODGE":
            self._add_log("Monster prepares to dodge!")
        elif chosen == "MOVE_L":
            if self._state.monster_pos != old_m_pos:
                self._add_log("Monster moves left.")
            else:
                self._add_log("Monster tries to move left but is blocked!")
        elif chosen == "MOVE_R":
            if self._state.monster_pos != old_m_pos:
                self._add_log("Monster moves right.")
            else:
                self._add_log("Monster tries to move right but is blocked!")

        self._check_combat_status()

    def _check_combat_status(self) -> None:
        """Verify win/loss states and apply syncs to world entities."""
        # Sync HPs back to entities
        self._player_entity.hp = self._state.player_hp
        self._monster_entity.hp = self._state.monster_hp

        if self._state.monster_hp <= 0:
            self._add_log("VICTORY! Monster was defeated.")
            self._monster_entity.active = False
            self._monster_entity.hp = 0
            
            # Auto pop back to game scene in 1.5 seconds
            self._monster_turn_timer = -1.5  # Negative timer triggers return
        elif self._state.player_hp <= 0:
            self._add_log("DEFEAT! Player died.")
            self._monster_turn_timer = -999.0  # Triggers game over
            self._sm.transition(GameState.GAME_OVER)

    def update(self, dt: float) -> None:
        """Handle delay pacing for monster turn execution."""
        if self._ingame_menu.active:
            return
        # Victory return delay handler
        if self._monster_turn_timer < 0.0:
            self._monster_turn_timer += dt
            if self._monster_turn_timer >= 0.0:
                self._bus.publish("pop_scene")
            return

        # Game over freeze
        if self._state.player_hp <= 0:
            return

        # Handle monster turn delay
        if not self._state.is_player_turn and self._state.monster_hp > 0:
            self._monster_turn_timer += dt
            if self._monster_turn_timer >= self._monster_turn_delay:
                self._monster_turn_timer = 0.0
                self._execute_monster_turn()

    def render(self, surface: pygame.Surface) -> None:
        """Draw the 1D combat arena, HP bars, turn indicator, and combat logs."""
        surface.fill(DARK_BG)

        # Title
        title_surf = self._title_font.render("⚔️ COMBAT ARENA ⚔️", True, WARNING)
        surface.blit(title_surf, title_surf.get_rect(center=(960 // 2, 60)))

        # Draw 1D Grid positions [1, 2, 3, 4, 5]
        grid_y = 300
        start_x = 230
        spacing = 120
        cell_size = 70

        for i in range(1, 6):
            cell_x = start_x + (i - 1) * spacing
            rect = pygame.Rect(cell_x - cell_size // 2, grid_y - cell_size // 2, cell_size, cell_size)
            
            # Check cell highlight
            border_color = PANEL_BORDER
            bg_color = (25, 28, 45)
            if i == self._state.player_pos:
                border_color = ACCENT
                bg_color = (15, 35, 65)
            elif i == self._state.monster_pos:
                border_color = DANGER
                bg_color = (65, 15, 25)

            pygame.draw.rect(surface, bg_color, rect, border_radius=10)
            pygame.draw.rect(surface, border_color, rect, 2, border_radius=10)

            # Draw position label
            lbl_surf = self._font.render(str(i), True, TEXT_MUTED)
            surface.blit(lbl_surf, lbl_surf.get_rect(center=(cell_x, grid_y + 55)))

        # Draw Player figure (on current position)
        p_x = start_x + (self._state.player_pos - 1) * spacing
        pygame.draw.circle(surface, (40, 120, 220), (p_x, grid_y), 24)
        pygame.draw.circle(surface, (255, 255, 255), (p_x - 6, grid_y - 4), 5)
        pygame.draw.circle(surface, (255, 255, 255), (p_x + 6, grid_y - 4), 5)
        pygame.draw.circle(surface, (0, 0, 0), (p_x - 5, grid_y - 4), 2)
        pygame.draw.circle(surface, (0, 0, 0), (p_x + 7, grid_y - 4), 2)
        if self._state.player_dodging:
            # Draw blue protective circle around player
            pygame.draw.circle(surface, ACCENT, (p_x, grid_y), 32, 2)

        # Draw Monster figure
        m_x = start_x + (self._state.monster_pos - 1) * spacing
        pygame.draw.circle(surface, (200, 30, 30), (m_x, grid_y), 24)
        pygame.draw.circle(surface, (255, 230, 0), (m_x - 6, grid_y - 4), 4)
        pygame.draw.circle(surface, (255, 230, 0), (m_x + 6, grid_y - 4), 4)
        pygame.draw.line(surface, (10, 10, 10), (m_x - 6, grid_y + 8), (m_x + 6, grid_y + 8), 2)
        if self._state.monster_dodging:
            # Draw red protective shield circle
            pygame.draw.circle(surface, DANGER, (m_x, grid_y), 32, 2)

        # Show status/turn indicator above grid
        if self._state.monster_hp <= 0:
            turn_str = "VICTORY! YOU DEFEATED THE MONSTER!"
            turn_color = SUCCESS
        elif self._state.player_hp <= 0:
            turn_str = "DEFEAT! YOU PERISHED IN COMBAT!"
            turn_color = DANGER
        elif self._state.is_player_turn:
            turn_str = "YOUR TURN - CHOOSE ACTION"
            turn_color = ACCENT
        else:
            turn_str = "MONSTER TURN - THINKING..."
            turn_color = WARNING

        turn_surf = self._large_font.render(turn_str, True, turn_color)
        surface.blit(turn_surf, turn_surf.get_rect(center=(960 // 2, 180)))

        # Render Combat Logs at the bottom of game canvas
        log_start_y = 450
        pygame.draw.rect(surface, (15, 15, 25), (60, log_start_y, 840, 160), border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, (60, log_start_y, 840, 160), 1, border_radius=8)

        log_hdr = self._bold_font.render("COMBAT FEEDBACK LOGS", True, TEXT_MUTED)
        surface.blit(log_hdr, (80, log_start_y + 10))

        ly = log_start_y + 35
        wrapped_logs = []
        for log in self._combat_log:
            clr = SUCCESS if "VICTORY" in log or "dealt" in log else (DANGER if "Monster dealt" in log or "DEFEAT" in log else (WARNING if "🤖" in log else TEXT_PRIMARY))
            lines = wrap_text(log, self._font, 800)
            for line in lines:
                wrapped_logs.append((line, clr))
        
        for line, clr in wrapped_logs[-6:]:
            log_surf = self._font.render(line, True, clr)
            surface.blit(log_surf, (80, ly))
            ly += 20

        # Draw in-game menu overlay
        self._ingame_menu.render(surface)

    def render_panel(self, panel: pygame.Surface) -> None:
        """Render combat statistics, adversarial search metrics, and AI dropdown panel."""
        panel.fill(PANEL_BG)

        # Header Title
        title_surf = self._title_font.render("⚔️ ARENA CONTROLS", True, TEXT_PRIMARY)
        panel.blit(title_surf, (20, 20))
        pygame.draw.line(panel, PANEL_BORDER, (10, 60), (310, 60), 2)



        # Action Buttons (only show if it is Player's turn and combat not finished)
        if self._state.is_player_turn and self._state.player_hp > 0 and self._state.monster_hp > 0:
            self._attack_btn.render(panel)
            self._dodge_btn.render(panel)
            self._move_l_btn.render(panel)
            self._move_r_btn.render(panel)
            self._ai_solve_btn.render(panel)
        else:
            # Draw disabled buttons indicator or simple message
            msg = "Thinking..." if not self._state.is_player_turn else "Combat Finished"
            msg_surf = self._bold_font.render(msg, True, TEXT_MUTED)
            panel.blit(msg_surf, msg_surf.get_rect(center=(320 // 2, 200)))

        # Combat Stats Section
        stats_y = 325
        pygame.draw.line(panel, PANEL_BORDER, (10, stats_y - 10), (310, stats_y - 10), 1)

        stats_hdr = self._bold_font.render("COMBAT STATUS", True, TEXT_PRIMARY)
        panel.blit(stats_hdr, (20, stats_y))

        sy = stats_y + 25
        # Custom HP rows
        sy = StatRow("Player HP:", f"{self._state.player_hp} / 100", self._font).render(panel, 20, sy)
        sy = StatRow("Monster HP:", f"{self._state.monster_hp} / 50", self._font).render(panel, 20, sy)
        sy = StatRow("D. Between:", f"{abs(self._state.player_pos - self._state.monster_pos)} cells", self._font).render(panel, 20, sy)

        # AI adversarial search metrics
        pygame.draw.line(panel, PANEL_BORDER, (10, sy + 5), (310, sy + 5), 1)
        ai_hdr = self._bold_font.render("ADVERSARIAL SEARCH STATS", True, TEXT_PRIMARY)
        panel.blit(ai_hdr, (20, sy + 15))

        ai_y = sy + 40
        ai_y = StatRow("Search Depth:", f"{self._tree_depth}", self._font).render(panel, 20, ai_y)
        ai_y = StatRow("Nodes Examined:", f"{self._nodes_evaluated}", self._font).render(panel, 20, ai_y)
        ai_y = StatRow("Cutoffs / Prunes:", f"{self._pruned_count}", self._font).render(panel, 20, ai_y)
        ai_y = StatRow("Best Choice:", f"{self._best_action}", self._font).render(panel, 20, ai_y)

        # -------------------------------------------------------------
        # GAME TREE SECTION
        # -------------------------------------------------------------
        tree_y = ai_y + 15
        pygame.draw.line(panel, PANEL_BORDER, (10, tree_y - 10), (310, tree_y - 10), 1)
        tree_hdr = self._bold_font.render("GAME TREE (depth=2)", True, TEXT_PRIMARY)
        panel.blit(tree_hdr, (20, tree_y))

        # Root Node Coordinates
        root_cx, root_cy = 160, tree_y + 35

        # Player Turn Actions at Depth 1
        actions = ["ATTACK", "DODGE", "MOVE_L", "MOVE_R"]
        depth1_nodes = []
        spacing_x = 72
        d1_y = root_cy + 45

        # Calculate child positions
        for idx, act in enumerate(actions):
            cx = root_cx + (idx - 1.5) * spacing_x
            depth1_nodes.append((act, cx, d1_y))

        # Draw Lines Root -> Depth 1
        for act, cx, cy in depth1_nodes:
            # Check if this branch is pruned or expectimax chance node
            is_pruned = False
            for p in self._pruned_nodes:
                if p.get("depth") == 1 and p.get("action") == act:
                    is_pruned = True
                    break
            
            line_color = (120, 30, 30) if is_pruned else (60, 65, 80)
            if act == self._best_action:
                line_color = SUCCESS
            pygame.draw.line(panel, line_color, (root_cx, root_cy), (cx, cy), 2)

        # Draw Root Node
        pygame.draw.circle(panel, (140, 140, 160), (root_cx, root_cy), 8)
        pygame.draw.circle(panel, PANEL_BORDER, (root_cx, root_cy), 8, 1)

        # Draw Depth 1 Nodes and Labels
        for act, cx, cy in depth1_nodes:
            is_pruned = False
            for p in self._pruned_nodes:
                if p.get("depth") == 1 and p.get("action") == act:
                    is_pruned = True
                    break

            # Find matching node value
            val = None
            for n in self._tree_nodes:
                if n.get("depth") == 1 and n.get("action") == act:
                    val = n.get("value")
                    break

            node_color = (60, 65, 80)
            if is_pruned:
                node_color = DANGER
            elif act == self._best_action:
                node_color = SUCCESS

            pygame.draw.circle(panel, node_color, (cx, cy), 8)
            
            # Highlight border if best action
            if act == self._best_action:
                pygame.draw.circle(panel, WARNING, (cx, cy), 11, 2)
            else:
                pygame.draw.circle(panel, PANEL_BORDER, (cx, cy), 8, 1)

            # Draw action label and heuristic value below node to keep line area clean
            font_size = 9
            small_font = pygame.font.SysFont("consolas", font_size)
            
            # Full Action name
            lbl = small_font.render(act, True, TEXT_MUTED)
            panel.blit(lbl, lbl.get_rect(center=(cx, cy + 14)))

            # Expectimax or heuristic value
            val_text = ""
            if val is not None:
                val_text = f"{val:.1f}"
            elif self._expected_values and act in self._expected_values:
                val_text = f"{self._expected_values[act]:.1f}"
            
            if val_text:
                val_surf = small_font.render(val_text, True, WARNING)
                panel.blit(val_surf, val_surf.get_rect(center=(cx, cy + 25)))

            # If Alpha-Beta pruned, draw a small red X on it
            if is_pruned:
                pygame.draw.line(panel, DANGER, (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
                pygame.draw.line(panel, DANGER, (cx + 4, cy - 4), (cx - 4, cy + 4), 2)

        # Draw the dropdown last so it renders on top of other controls
        algo_lbl = self._bold_font.render("COMBAT AI SOLVER", True, TEXT_MUTED)
        panel.blit(algo_lbl, (20, 75))
        self._ai_dropdown.render(panel)

