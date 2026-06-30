"""
csp_overlay.py — CSP Constraint Graph visualization overlay rendering nodes and edges on the Puzzle Panel.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pygame

from config.settings import PANEL_BORDER, SUCCESS, DANGER, TEXT_PRIMARY, TEXT_MUTED


class CSPOverlay:
    """Helper to render a Latin Square CSP constraint graph network."""

    @staticmethod
    def render_constraint_graph(
        surface: pygame.Surface,
        vis_data: Dict[str, Any],
        puzzle_rect: pygame.Rect,
    ) -> None:
        """Draw constraint graph as a network of nodes + edges.
        
        Node = puzzle cell (3x3 = 9 nodes)
        Edge = constraint relationship (same row or same column)
        """
        # 1. Gather variables from vis_data
        assigned = vis_data.get("assigned", {})
        violations = vis_data.get("violations", set())
        current_var = vis_data.get("current_var", None)
        domain_sizes = vis_data.get("domain_sizes", {})
        constraint_violations = vis_data.get("constraint_violations", [])

        # Positions mapping: 3x3 layout centered inside the puzzle_rect
        margin_x = puzzle_rect.width // 4
        margin_y = puzzle_rect.height // 4
        
        node_pos: Dict[Tuple[int, int], Tuple[int, int]] = {}
        for r in range(3):
            for c in range(3):
                px = puzzle_rect.x + (c + 1) * margin_x
                py = puzzle_rect.y + (r + 1) * margin_y
                node_pos[(r, c)] = (px, py)

        # 2. Draw constraint lines (edges) between nodes in same row or column
        for r1 in range(3):
            for c1 in range(3):
                for r2 in range(3):
                    for c2 in range(3):
                        # Avoid duplicates and self edges
                        if (r1, c1) >= (r2, c2):
                            continue
                        # Sharing row or column represents a constraint edge
                        if r1 == r2 or c1 == c2:
                            p1 = node_pos[(r1, c1)]
                            p2 = node_pos[(r2, c2)]
                            
                            # Check if this edge constraint is violated
                            is_violated = False
                            for v1, v2 in constraint_violations:
                                if ((v1 == (r1, c1) and v2 == (r2, c2)) or 
                                    (v2 == (r1, c1) and v1 == (r2, c2))):
                                    is_violated = True
                                    break
                            
                            edge_color = DANGER if is_violated else (60, 65, 80)
                            thickness = 2 if is_violated else 1
                            pygame.draw.line(surface, edge_color, p1, p2, thickness)

        # 3. Draw nodes (circles)
        for r in range(3):
            for c in range(3):
                px, py = node_pos[(r, c)]
                val = assigned.get((r, c), 0)
                is_violation = (r, c) in violations
                is_current = (r, c) == current_var
                
                # Determine node color
                if is_current:
                    node_color = (255, 230, 0)  # Current under review
                elif is_violation:
                    node_color = DANGER
                elif val != 0:
                    node_color = SUCCESS
                else:
                    node_color = (60, 65, 80)

                # Draw base circle
                pygame.draw.circle(surface, node_color, (px, py), 15)
                
                # Highlight if active/current
                if is_current:
                    pygame.draw.circle(surface, (255, 255, 255), (px, py), 17, 2)
                else:
                    pygame.draw.circle(surface, PANEL_BORDER, (px, py), 15, 1)

                # Draw Label (current assigned value or '-' if empty)
                font = pygame.font.SysFont("consolas", 12, bold=True)
                lbl_text = str(val) if val != 0 else "-"
                lbl_color = (10, 10, 15) if (is_current or val != 0) else TEXT_PRIMARY
                lbl_surf = font.render(lbl_text, True, lbl_color)
                surface.blit(lbl_surf, lbl_surf.get_rect(center=(px, py)))

                # Draw Domain size indicator "dom:N" below node
                dom_size = domain_sizes.get((r, c), 3)
                small_font = pygame.font.SysFont("consolas", 8)
                dom_surf = small_font.render(f"d:{dom_size}", True, TEXT_MUTED)
                surface.blit(dom_surf, dom_surf.get_rect(center=(px, py + 22)))
