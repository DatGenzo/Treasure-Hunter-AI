"""
particle.py — Visual particle effects system for treasure collects and level wins.
"""

from __future__ import annotations

import random
from typing import List, Tuple

import pygame

from utils.vec2 import Vec2


class Particle:
    """A single colored visual particle that fades out over time."""

    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int], life: float) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = random.randint(2, 5)

    def update(self, dt: float) -> bool:
        """Move particle and decay life. Returns True if particle is still active."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0.0

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Render particle with alpha transparency based on remaining life."""
        alpha = int(255 * max(0.0, self.life / self.max_life))
        
        # Draw translucent particle using a temp surface
        p_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (*self.color, alpha), (self.size, self.size), self.size)
        
        surface.blit(p_surf, (self.x - self.size - camera_offset.x, self.y - self.size - camera_offset.y))


class ParticleSystem:
    """Manages active particles in the level."""

    def __init__(self) -> None:
        self._particles: List[Particle] = []

    def spawn_collect(self, x: float, y: float, color: Tuple[int, int, int]) -> None:
        """Burst 15 particles outwards when an item is collected."""
        for _ in range(15):
            angle = random.uniform(0.0, 2.0 * 3.14159)
            speed = random.uniform(40.0, 100.0)
            vx = speed * float(random.choice([-1, 1])) * random.uniform(0.5, 1.0)
            vy = speed * float(random.choice([-1, 1])) * random.uniform(0.5, 1.0)
            
            # Simple polar speed vector
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            
            self._particles.append(
                Particle(x, y, vx, vy, color, life=random.uniform(0.3, 0.7))
            )

    def spawn_level_complete(self, center_x: float, center_y: float) -> None:
        """Spawn a fountain of green particles for victory feedback."""
        for _ in range(80):
            vx = random.uniform(-150.0, 150.0)
            vy = random.uniform(-250.0, -50.0)  # burst upwards
            color = (
                random.randint(50, 100),
                random.randint(180, 255),
                random.randint(80, 150),
            )
            self._particles.append(
                Particle(center_x, center_y, vx, vy, color, life=random.uniform(1.0, 2.0))
            )

    def update(self, dt: float) -> None:
        """Update and clean up dead particles."""
        self._particles = [p for p in self._particles if p.update(dt)]

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Render all active particles."""
        for p in self._particles:
            p.render(surface, camera_offset)


# Include math module for cos/sin calculations
import math
