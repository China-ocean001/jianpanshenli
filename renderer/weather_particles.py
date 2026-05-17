"""
Weather particle system: Rain, Drought, Normal sky effects.
"""

from __future__ import annotations
import math
import random
import pygame

from climate import ClimateState
from config import (
    WINDOW_W, WINDOW_H,
    C_SKY_TOP, C_SKY_BOT,
    C_SKY_RAIN_TOP, C_SKY_RAIN_BOT,
    C_SKY_DROUGHT_TOP, C_SKY_DROUGHT_BOT,
    C_GROUND, C_GROUND_DROUGHT,
    C_DROUGHT_CRACK,
)

_RAIN_DROP_COUNT = 120


def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Raindrop:
    __slots__ = ('x', 'y', 'speed', 'length', 'alpha')

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, WINDOW_W)
        self.y = random.uniform(-200, 0)
        self.speed = random.uniform(400, 700)
        self.length = random.randint(8, 18)
        self.alpha = random.randint(100, 200)

    def update(self, dt: float):
        self.y += self.speed * dt
        self.x -= self.speed * 0.15 * dt   # slight diagonal
        if self.y > WINDOW_H:
            self.reset()


class WeatherParticles:
    def __init__(self):
        self._drops = [Raindrop() for _ in range(_RAIN_DROP_COUNT)]
        self._crack_surf: pygame.Surface | None = None
        self._t = 0.0

    # ── Main draw call ────────────────────────────────────────────────────

    def update_and_draw(self, screen: pygame.Surface, dt: float,
                        climate: ClimateState, intensity: float = 1.0,
                        theme: dict = None):
        self._t += dt
        self._draw_sky(screen, climate, intensity, theme)

        if climate == ClimateState.RAIN:
            self._draw_rain(screen, dt, intensity)
        elif climate == ClimateState.DROUGHT:
            self._draw_drought(screen, intensity)

    # ── Sky gradient ──────────────────────────────────────────────────────

    def _draw_sky(self, screen, climate, intensity, theme=None):
        base_top = theme['sky_top'] if theme else C_SKY_TOP
        base_bot = theme['sky_bot'] if theme else C_SKY_BOT
        ground_c = theme['ground']  if theme else C_GROUND

        if climate == ClimateState.RAIN:
            top = _lerp_color(base_top, C_SKY_RAIN_TOP, intensity)
            bot = _lerp_color(base_bot, C_SKY_RAIN_BOT, intensity)
        elif climate == ClimateState.DROUGHT:
            top = _lerp_color(base_top, C_SKY_DROUGHT_TOP, intensity)
            bot = _lerp_color(base_bot, C_SKY_DROUGHT_BOT, intensity)
        else:
            top = base_top
            bot = base_bot

        sky_h = WINDOW_H - 40   # leave ground strip
        for y in range(sky_h):
            t = y / sky_h
            color = _lerp_color(top, bot, t)
            pygame.draw.line(screen, color, (0, y), (WINDOW_W, y))

        # Ground strip
        ground_color = C_GROUND_DROUGHT if climate == ClimateState.DROUGHT else ground_c
        pygame.draw.rect(screen, ground_color, (0, sky_h, WINDOW_W, 40))

    # ── Rain ──────────────────────────────────────────────────────────────

    def _draw_rain(self, screen, dt, intensity):
        active_count = int(_RAIN_DROP_COUNT * intensity)
        rain_surf = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        for drop in self._drops[:active_count]:
            drop.update(dt)
            color = (150, 190, 255, int(drop.alpha * intensity))
            ex = int(drop.x - drop.length * 0.15)
            ey = int(drop.y + drop.length)
            pygame.draw.line(rain_surf, color,
                             (int(drop.x), int(drop.y)), (ex, ey), 1)
        screen.blit(rain_surf, (0, 0))

    # ── Drought ───────────────────────────────────────────────────────────

    def _draw_drought(self, screen, intensity):
        # Heat shimmer: horizontal wavy distortion suggestion
        shimmer_surf = pygame.Surface((WINDOW_W, 30), pygame.SRCALPHA)
        for x in range(0, WINDOW_W, 4):
            alpha = int(30 * intensity * abs(math.sin(x * 0.05 + self._t * 2)))
            color = (255, 140, 40, alpha)
            pygame.draw.line(shimmer_surf, color,
                             (x, 0), (x, 30))
        screen.blit(shimmer_surf, (0, WINDOW_H - 70))

        # Crack lines on ground
        if self._crack_surf is None or True:   # regenerate
            self._crack_surf = self._make_crack_surface(intensity)
        alpha_surf = self._crack_surf.copy()
        alpha_surf.set_alpha(int(180 * intensity))
        screen.blit(alpha_surf, (0, WINDOW_H - 42))

    def _make_crack_surface(self, intensity) -> pygame.Surface:
        surf = pygame.Surface((WINDOW_W, 42), pygame.SRCALPHA)
        random.seed(42)   # deterministic cracks
        n_cracks = int(8 * intensity)
        for _ in range(n_cracks):
            x = random.randint(0, WINDOW_W)
            y = random.randint(5, 35)
            for __ in range(3):
                dx = random.randint(-30, 30)
                dy = random.randint(-8, 8)
                pygame.draw.line(surf, C_DROUGHT_CRACK + (180,), (x, y), (x+dx, y+dy), 1)
                x += dx; y += dy
        random.seed()    # restore randomness
        return surf
