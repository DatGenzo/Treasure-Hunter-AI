"""
audio package — Plays placeholder beep sounds for game events.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_current_music = None

def play_music(filename: str, loop: int = -1) -> None:
    """Play background music using pygame.mixer.music."""
    global _current_music
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        import os
        filepath = os.path.join("assets", "audio", filename)
        if not os.path.exists(filepath):
            logger.warning(f"Music file not found: {filepath}. Please place your music file here.")
            return

        if _current_music != filename:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play(loop)
            _current_music = filename
    except Exception as e:
        logger.error(f"Failed to play music {filename}: {e}")

def stop_music() -> None:
    """Stop currently playing background music."""
    global _current_music
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            _current_music = None
    except Exception as e:
        logger.error(f"Failed to stop music: {e}")


def play_sound(event_name: str) -> None:
    """Play a standard winsound beep in a separate daemon thread to avoid blocking."""
    def _run() -> None:
        try:
            import winsound
            if event_name == "collect_item":
                winsound.Beep(523, 100)  # C5 beep
            elif event_name == "door_open":
                winsound.Beep(392, 100)  # G4
                winsound.Beep(523, 150)  # C5
            elif event_name == "level_complete":
                winsound.Beep(523, 120)  # C5
                winsound.Beep(659, 120)  # E5
                winsound.Beep(784, 120)  # G5
                winsound.Beep(1046, 250)  # C6
            elif event_name == "combat_hit":
                winsound.Beep(180, 120)  # Low-pitch hit thud
        except ImportError:
            # Non-Windows fallback (Linux/macOS)
            logger.debug("winsound not available on this platform.")
        except Exception as e:
            logger.debug("Failed to play sound beep: %s", e)

    threading.Thread(target=_run, daemon=True).start()
