"""
widgets.py — Custom pygame-drawn UI controls (Button, Dropdown, Slider, StatRow).
"""

from __future__ import annotations

from typing import List, Tuple, Optional

import math
import pygame

from config.settings import ACCENT, ACCENT_HOVER, PANEL_BORDER, TEXT_PRIMARY, TEXT_MUTED


class Button:
    """A clickable text button drawn with rounded corners."""

    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        text: str,
        font: pygame.font.Font,
        bg_color: Tuple[int, int, int],
        hover_color: Tuple[int, int, int],
        border_color: Optional[Tuple[int, int, int]] = None,
        border_radius: int = 6,
    ) -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.border_color = border_color
        self.border_radius = border_radius
        self.hovered = False

    def handle_event(self, event: pygame.event.Event, offset_x: int = 0, offset_y: int = 0) -> bool:
        """Update hover state and check for left-click."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered = self.rect.collidepoint(mx - offset_x, my - offset_y)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if self.rect.collidepoint(mx - offset_x, my - offset_y):
                    return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        """Render button shape and text."""
        bg = self.hover_color if self.hovered else self.bg_color
        pygame.draw.rect(surface, bg, self.rect, border_radius=self.border_radius)

        if self.border_color:
            pygame.draw.rect(surface, self.border_color, self.rect, 2, border_radius=self.border_radius)

        text_surf = self.font.render(self.text, True, TEXT_PRIMARY)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class Dropdown:
    """A dropdown menu control holding selectable options."""

    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        options: List[Tuple[str, str]],  # List of (key, display_name)
        font: pygame.font.Font,
    ) -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.options = options
        self.font = font
        self.selected_idx = 0
        self.expanded = False

        self._option_height = 36
        self._hover_idx = -1

    @property
    def selected_key(self) -> str:
        """Return key of currently selected option."""
        if 0 <= self.selected_idx < len(self.options):
            return self.options[self.selected_idx][0]
        return ""

    @property
    def selected_name(self) -> str:
        """Return display name of currently selected option."""
        if 0 <= self.selected_idx < len(self.options):
            return self.options[self.selected_idx][1]
        return "None"

    def handle_event(self, event: pygame.event.Event, offset_x: int = 0, offset_y: int = 0) -> bool:
        """Manage expansion toggles and item selection."""
        mx, my = pygame.mouse.get_pos()
        mx -= offset_x
        my -= offset_y

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Clicked header
                if self.rect.collidepoint(mx, my):
                    self.expanded = not self.expanded
                    return True
                
                # Clicked open options list
                if self.expanded:
                    for i in range(len(self.options)):
                        opt_rect = pygame.Rect(
                            self.rect.x,
                            self.rect.bottom + i * self._option_height,
                            self.rect.width,
                            self._option_height,
                        )
                        if opt_rect.collidepoint(mx, my):
                            self.selected_idx = i
                            self.expanded = False
                            return True
                    # Clicked outside
                    self.expanded = False

        elif event.type == pygame.MOUSEMOTION:
            if self.expanded:
                self._hover_idx = -1
                for i in range(len(self.options)):
                    opt_rect = pygame.Rect(
                        self.rect.x,
                        self.rect.bottom + i * self._option_height,
                        self.rect.width,
                        self._option_height,
                    )
                    if opt_rect.collidepoint(mx, my):
                        self._hover_idx = i
                        break
        return False

    def render(self, surface: pygame.Surface) -> None:
        """Render dropdown box, selected label, and options overlay list."""
        # Draw header
        pygame.draw.rect(surface, (22, 28, 48), self.rect, border_radius=6)
        pygame.draw.rect(surface, ACCENT if self.expanded else PANEL_BORDER, self.rect, 2, border_radius=6)

        # Header text
        name_surf = self.font.render(self.selected_name, True, TEXT_PRIMARY)
        surface.blit(name_surf, (self.rect.x + 12, self.rect.y + (self.rect.height - name_surf.get_height()) // 2))

        # Draw down arrow
        arrow_char = "▲" if self.expanded else "▼"
        arrow_surf = self.font.render(arrow_char, True, TEXT_MUTED)
        surface.blit(arrow_surf, (self.rect.right - 25, self.rect.y + (self.rect.height - arrow_surf.get_height()) // 2))

        # Render options dropdown list
        if self.expanded:
            total_h = len(self.options) * self._option_height
            container = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.width, total_h)
            # Fill container
            pygame.draw.rect(surface, (18, 22, 38), container, border_radius=4)
            pygame.draw.rect(surface, ACCENT, container, 2, border_radius=4)

            for i, (_, display_name) in enumerate(self.options):
                opt_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.bottom + i * self._option_height,
                    self.rect.width,
                    self._option_height,
                )
                if i == self._hover_idx:
                    pygame.draw.rect(surface, (30, 45, 75), opt_rect)
                
                text_color = TEXT_PRIMARY if (i == self._hover_idx or i == self.selected_idx) else TEXT_MUTED
                opt_surf = self.font.render(display_name, True, text_color)
                surface.blit(opt_surf, (opt_rect.x + 12, opt_rect.y + (opt_rect.height - opt_surf.get_height()) // 2))


class Slider:
    """A horizontal slider control with handle drag-and-drop support."""

    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        min_val: float,
        max_val: float,
        initial_val: float,
        font: pygame.font.Font,
        label: str = "",
    ) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.min_val = min_val
        self.max_val = max_val
        self.value = float(initial_val)
        self.font = font
        self.label = label

        self.track_rect = pygame.Rect(x, y + 20, w, 6)
        self.handle_radius = 8
        self._dragging = False

    @property
    def handle_x(self) -> int:
        """Calculate screen X coordinate of handle thumb."""
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        return int(self.x + ratio * self.w)

    def handle_event(self, event: pygame.event.Event, offset_x: int = 0, offset_y: int = 0) -> None:
        """Process slider drag mouse interactions."""
        mx, my = pygame.mouse.get_pos()
        mx -= offset_x
        my -= offset_y

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                hx = self.handle_x
                # Clicked near handle
                dist = math.hypot(mx - hx, my - (self.y + 23))
                if dist <= self.handle_radius + 4 or self.track_rect.collidepoint(mx, my):
                    self._dragging = True
                    self._update_val(mx)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:
                self._update_val(mx)

    def _update_val(self, mx: int) -> None:
        """Update value based on mouse X placement."""
        ratio = max(0.0, min(1.0, (mx - self.x) / self.w))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def render(self, surface: pygame.Surface) -> None:
        """Render slider track, drag handle thumb, and value text."""
        # Render Title + Value label
        label_surf = self.font.render(f"{self.label}: {self.value:.1f}", True, TEXT_PRIMARY)
        surface.blit(label_surf, (self.x, self.y))

        # Render track
        pygame.draw.rect(surface, (40, 45, 65), self.track_rect, border_radius=3)
        
        # Fill active track portion
        active_rect = pygame.Rect(self.x, self.track_rect.y, self.handle_x - self.x, self.track_rect.height)
        pygame.draw.rect(surface, ACCENT, active_rect, border_radius=3)

        # Render handle thumb
        color = ACCENT_HOVER if self._dragging else ACCENT
        pygame.draw.circle(surface, color, (self.handle_x, self.track_rect.centery), self.handle_radius)
        pygame.draw.circle(surface, (255, 255, 255), (self.handle_x, self.track_rect.centery), 3)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Wraps text to fit within a given max_width pixel boundary using the font."""
    words = text.split(" ")
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


class StatRow:
    """A key-value statistical row renderer."""

    def __init__(self, label: str, value: str, font: pygame.font.Font) -> None:
        self.label = label
        self.value = value
        self.font = font

    def render(self, surface: pygame.Surface, x: int, y: int) -> int:
        """Draw label on the left and value on the right. Returns next y coordinate."""
        lbl_surf = self.font.render(self.label, True, TEXT_MUTED)
        
        # Max width available for the value is 280 (content width) - (label width + 10 padding)
        # We assume total content width is 280 (x starts at 20, right boundary is 300)
        max_val_w = 280 - (lbl_surf.get_width() + 10)
        
        val_w = self.font.size(self.value)[0]
        if val_w <= max_val_w:
            val_surf = self.font.render(self.value, True, TEXT_PRIMARY)
            surface.blit(lbl_surf, (x, y))
            # Right-align the value to x + 280 (which is 300 on the panel)
            surface.blit(val_surf, (x + 280 - val_surf.get_width(), y))
            return y + max(lbl_surf.get_height(), val_surf.get_height()) + 5
        else:
            # Value is too long, wrap it to subsequent lines
            wrapped = wrap_text(self.value, self.font, 280)
            surface.blit(lbl_surf, (x, y))
            curr_y = y + lbl_surf.get_height() + 4
            for line in wrapped:
                val_surf = self.font.render(line, True, TEXT_PRIMARY)
                surface.blit(val_surf, (x + 20, curr_y))
                curr_y += val_surf.get_height() + 4
            return curr_y


class InGameMenu:
    """An overlay pause menu with Resume, Level Select, and Exit options."""

    def __init__(self, bus: Any, state_machine: Any) -> None:
        self._bus = bus
        self._sm = state_machine
        self.active = False

        self._bold_font = pygame.font.SysFont("consolas", 16, bold=True)
        self._title_font = pygame.font.SysFont("consolas", 24, bold=True)

        # The small menu button on the top-right of the game surface (960x720)
        # Shifted slightly left to stay clear of the LEVEL text in GameScene (Level text is at x=840)
        self.menu_btn = Button(750, 10, 70, 30, "MENU", self._bold_font, (40, 45, 60), (60, 65, 80), (100, 100, 150))

        # Buttons in the overlay (centered at 960 // 2 = 480)
        button_w = 240
        button_h = 40
        self.resume_btn = Button(480 - button_w // 2, 280, button_w, button_h, "RESUME PLAY", self._bold_font, (30, 120, 60), (45, 150, 75), (70, 180, 100))
        self.level_select_btn = Button(480 - button_w // 2, 340, button_w, button_h, "LEVEL SELECT", self._bold_font, (30, 60, 120), (50, 90, 160), (80, 120, 200))
        self.exit_btn = Button(480 - button_w // 2, 400, button_w, button_h, "EXIT GAME", self._bold_font, (120, 30, 30), (160, 45, 45), (200, 60, 60))
        self._prev_state = None

    def open_menu(self) -> None:
        from core.state_machine import GameState
        self.active = True
        self._prev_state = self._sm.state
        if self._sm.state in (GameState.PLAYING, GameState.AI_RUNNING, GameState.AI_PAUSED):
            self._sm.transition(GameState.PAUSED)

    def close_menu(self) -> None:
        from core.state_machine import GameState
        self.active = False
        if self._prev_state is not None:
            self._sm.transition(self._prev_state)
            self._prev_state = None
        else:
            self._sm.transition(GameState.PLAYING)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process menu events. Returns True if the event was handled/consumed."""
        # Handle ESC key to toggle menu
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.active:
                self.close_menu()
            else:
                self.open_menu()
            return True

        if not self.active:
            # Check if MENU button clicked
            if self.menu_btn.handle_event(event):
                self.open_menu()
                return True
            return False

        # If active, intercept all mouse events
        self.resume_btn.handle_event(event)
        self.level_select_btn.handle_event(event)
        self.exit_btn.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.resume_btn.rect.collidepoint(mx, my):
                self.close_menu()
            elif self.level_select_btn.rect.collidepoint(mx, my):
                from core.state_machine import GameState
                self.active = False
                self._sm.transition(GameState.LEVEL_SELECT)
            elif self.exit_btn.rect.collidepoint(mx, my):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            return True # Consume all click events while active

        # Intercept other mouse motions/scroll/keys while active
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.KEYDOWN, pygame.KEYUP):
            return True

        return True

    def render(self, surface: pygame.Surface) -> None:
        """Draw the menu button or the full overlay."""
        # Always draw the small menu button
        self.menu_btn.render(surface)

        if self.active:
            # 1. Dark translucent overlay
            overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
            overlay.fill((10, 10, 20, 200))
            surface.blit(overlay, (0, 0))

            # 2. Draw dialog box
            box_w, box_h = 320, 260
            box_rect = pygame.Rect(480 - box_w // 2, 210, box_w, box_h)
            pygame.draw.rect(surface, (22, 22, 38), box_rect, border_radius=10)
            pygame.draw.rect(surface, (70, 70, 110), box_rect, 2, border_radius=10)

            # 3. Draw Title
            title_surf = self._title_font.render("GAME MENU", True, (255, 190, 50))
            surface.blit(title_surf, title_surf.get_rect(center=(480, 245)))

            # 4. Render buttons
            self.resume_btn.render(surface)
            self.level_select_btn.render(surface)
            self.exit_btn.render(surface)
