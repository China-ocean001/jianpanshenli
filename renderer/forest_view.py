"""
ForestView: renders the keyboard-layout grid with per-key trees.
"""

from __future__ import annotations
import pygame
from typing import Optional

from config import (
    KEY_RECTS, KEY_LABELS,
    KEY_H, FLASH_DURATION,
    WINDOW_W, WINDOW_H, STATUS_H,
    C_KEY_LABEL_DEAD,
)
from forest import Forest
from renderer.tree_sprites import get_tree_surface, TREE_W, TREE_H
from shop import BG_THEMES

# Scale tree to fit inside the (smaller) key cell
_TREE_DISPLAY_H = KEY_H - 14    # leave room for label at bottom
_TREE_SCALE = _TREE_DISPLAY_H / TREE_H
_TREE_DISPLAY_W = max(1, int(TREE_W * _TREE_SCALE))

# Vertical centre of the empty space below the keyboard grid
_GRID_BOTTOM = max(ry + rh for _, (_, ry, _, rh) in KEY_RECTS.items())
_OVERLAY_Y   = _GRID_BOTTOM + (WINDOW_H - STATUS_H - _GRID_BOTTOM) // 2

# Lazy-loaded large font for background text overlay
_OVERLAY_FONT = None


def _get_overlay_font() -> pygame.font.Font:
    global _OVERLAY_FONT
    if _OVERLAY_FONT is None:
        for name in ('Microsoft YaHei', 'SimHei', 'SimSun'):
            try:
                _OVERLAY_FONT = pygame.font.SysFont(name, 62, bold=True)
                break
            except Exception:
                pass
        if _OVERLAY_FONT is None:
            _OVERLAY_FONT = pygame.font.Font(None, 68)
    return _OVERLAY_FONT


class ForestView:
    def __init__(self, forest: Forest, font: pygame.font.Font, shop=None):
        self.forest = forest
        self.font = font
        self.shop = shop

        self._flash_timers: dict[str, float] = {}
        self._hovered: Optional[str] = None
        self._t = 0.0

    def _th(self) -> dict:
        if self.shop:
            return self.shop.get_theme()
        return BG_THEMES['default']

    # ── Public API ─────────────────────────────────────────────────────────

    def flash_key(self, key_name: str):
        self._flash_timers[key_name] = FLASH_DURATION

    def update(self, dt: float):
        self._t += dt
        for key in list(self._flash_timers):
            self._flash_timers[key] -= dt
            if self._flash_timers[key] <= 0:
                del self._flash_timers[key]

    def handle_mouse_move(self, pos):
        self._hovered = self._key_at(pos)

    def key_at(self, pos) -> Optional[str]:
        return self._key_at(pos)

    def draw(self, screen: pygame.Surface):
        pest_keys = self.forest.events.pest_affected_keys()
        for key_name, (rx, ry, rw, rh) in KEY_RECTS.items():
            tree  = self.forest.trees.get(key_name)
            flash = key_name in self._flash_timers
            hov   = key_name == self._hovered
            pest  = key_name in pest_keys
            self._draw_cell(screen, key_name, rx, ry, rw, rh, tree, flash, hov, pest)
        self._draw_theme_overlay(screen)

    # ── Internal ───────────────────────────────────────────────────────────

    def _draw_theme_overlay(self, screen: pygame.Surface):
        """Draw decorative text watermark below the keyboard for themed backgrounds."""
        if not self.shop:
            return
        bg_id = self.shop.active_bg_id
        if bg_id == 'rmwy':
            text, color, alpha = '人民万岁', (255, 215, 0), 130
        elif bg_id == 's520':
            text, color, alpha = '520', (255, 245, 240), 110
        else:
            return
        font = _get_overlay_font()
        ts = font.render(text, True, color)
        ts.set_alpha(alpha)
        screen.blit(ts, ((WINDOW_W - ts.get_width()) // 2,
                          _OVERLAY_Y - ts.get_height() // 2))

    def _draw_cell(self, screen, key_name, rx, ry, rw, rh, tree, flash, hovered, pest=False):
        th = self._th()
        C_CELL_BG     = th['cell_bg']
        C_CELL_BORDER = th['cell_border']
        C_CELL_HOVER  = th['cell_hover']
        C_CELL_FLASH  = th['cell_flash']
        C_CELL_DEAD   = th['cell_dead']
        C_KEY_LABEL   = th['key_label']

        if tree and tree.is_dead:
            bg = C_CELL_DEAD
        elif hovered:
            bg = C_CELL_HOVER
        elif flash:
            frac = self._flash_timers.get(key_name, 0) / FLASH_DURATION
            bg = _lerp_color(C_CELL_BG, C_CELL_FLASH, frac)
        else:
            bg = C_CELL_BG

        pygame.draw.rect(screen, bg, (rx, ry, rw, rh), border_radius=3)
        if pest:
            border_color = (210, 115, 35)  # orange pest border
        elif flash:
            border_color = C_CELL_FLASH
        else:
            border_color = C_CELL_BORDER
        pygame.draw.rect(screen, border_color, (rx, ry, rw, rh), 2 if pest else 1, border_radius=3)

        if tree is None:
            return

        # Tree sprite – scaled to fit cell
        raw_surf = get_tree_surface(tree.stage, tree.health, tree.is_dead,
                                    tree.level_up_timer > 0, self._t,
                                    skin_id=tree.skin_id)
        tree_surf = pygame.transform.scale(raw_surf, (_TREE_DISPLAY_W, _TREE_DISPLAY_H))

        tx = rx + (rw - _TREE_DISPLAY_W) // 2
        ty = ry + 2
        screen.blit(tree_surf, (tx, ty))

        # Small pest dot indicator (top-right corner of cell)
        if pest:
            pygame.draw.circle(screen, (220, 100, 30), (rx + rw - 4, ry + 4), 3)

        # Key label – bottom of cell
        label = KEY_LABELS.get(key_name, key_name[:4].upper())
        label_color = C_KEY_LABEL_DEAD if tree.is_dead else C_KEY_LABEL
        txt = self.font.render(label, True, label_color)
        lx = rx + (rw - txt.get_width()) // 2
        ly = ry + rh - txt.get_height() - 1
        screen.blit(txt, (lx, ly))

    def _key_at(self, pos) -> Optional[str]:
        mx, my = pos
        for key_name, (rx, ry, rw, rh) in KEY_RECTS.items():
            if rx <= mx < rx + rw and ry <= my < ry + rh:
                return key_name
        return None


def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
