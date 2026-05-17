"""
GroveView: gallery of all graduated trees (trees_grown > 0).
Click a card to see key stats.
"""

from __future__ import annotations
import pygame
from typing import Optional, List, Tuple

from config import (
    WINDOW_W, WINDOW_H, HUD_H, STATUS_H, KEY_LABELS,
    C_STATS_BG, C_STATS_PANEL, C_STATS_BORDER, C_STATS_TITLE,
    C_STATS_TEXT, C_STATS_DIM, C_HUD_TEXT,
    C_BAR_BG, C_BAR_XP, C_BAR_HP_HIGH, C_BAR_HP_MID, C_BAR_HP_LOW,
)
from forest import Forest
from renderer.tree_sprites import get_tree_surface, TREE_W, TREE_H

_CONTENT_Y = HUD_H + 4
_CONTENT_H = WINDOW_H - HUD_H - STATUS_H
_CARD_W    = 150
_CARD_H    = 140
_CARD_GAP  = 10
_COLS      = (WINDOW_W - _CARD_GAP) // (_CARD_W + _CARD_GAP)
_GRID_W    = _COLS * (_CARD_W + _CARD_GAP) - _CARD_GAP
_GRID_X0   = (WINDOW_W - _GRID_W) // 2

_SPRITE_SCALE = 1.4
_SW = int(TREE_W * _SPRITE_SCALE)
_SH = int(TREE_H * _SPRITE_SCALE)


class GroveView:
    def __init__(self, forest: Forest, font_med: pygame.font.Font,
                 font_sm: pygame.font.Font):
        self.forest = forest
        self.font_med = font_med
        self.font_sm = font_sm

        self._scroll_y: int = 0
        self._selected: Optional[str] = None   # key_name of detail popup
        self._card_rects: List[Tuple[str, pygame.Rect]] = []
        self._close_rect: Optional[pygame.Rect] = None

    def update(self, dt: float):
        pass

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Close popup
                if self._selected:
                    if self._close_rect and self._close_rect.collidepoint(event.pos):
                        self._selected = None
                        return True
                    # Click outside popup → close
                    popup_rect = self._popup_rect()
                    if not popup_rect.collidepoint(event.pos):
                        self._selected = None
                    return True
                # Click card
                for key_name, rect in self._card_rects:
                    if rect.collidepoint(event.pos):
                        self._selected = key_name
                        return True
            elif event.button == 4:   # scroll up
                self._scroll_y = max(0, self._scroll_y - 40)
                return True
            elif event.button == 5:   # scroll down
                self._scroll_y = min(self._max_scroll(), self._scroll_y + 40)
                return True
        return False

    def draw(self, screen: pygame.Surface):
        screen.fill(C_STATS_BG)

        # Collect graduated trees, sorted best-first
        grad_trees = sorted(
            [t for t in self.forest.trees.values() if t.trees_grown > 0],
            key=lambda t: (-t.trees_grown, -t.total_presses)
        )

        # Header
        title = f"树场 · 已毕业 {len(grad_trees)} 棵"
        ts = self.font_med.render(title, True, C_STATS_TITLE)
        screen.blit(ts, (12, _CONTENT_Y + 4))

        if not grad_trees:
            hint = self.font_sm.render("当任意一棵树达到满级后继续积累经验，即可毕业迁入树场", True, C_STATS_DIM)
            screen.blit(hint, (WINDOW_W // 2 - hint.get_width() // 2, WINDOW_H // 2))
            return

        self._card_rects.clear()
        start_y = _CONTENT_Y + 30 - self._scroll_y

        for idx, tree in enumerate(grad_trees):
            col = idx % _COLS
            row = idx // _COLS
            cx = _GRID_X0 + col * (_CARD_W + _CARD_GAP)
            cy = start_y + row * (_CARD_H + _CARD_GAP)

            card_rect = pygame.Rect(cx, cy, _CARD_W, _CARD_H)
            # Clip to content area
            if cy + _CARD_H < _CONTENT_Y + 30 or cy > WINDOW_H - STATUS_H:
                self._card_rects.append((tree.key_name, card_rect))
                continue
            self._card_rects.append((tree.key_name, card_rect))
            self._draw_card(screen, tree, card_rect)

        # Detail popup
        if self._selected:
            self._draw_popup(screen)

    def _draw_card(self, screen: pygame.Surface, tree, rect: pygame.Rect):
        is_sel = (tree.key_name == self._selected)
        bg = (50, 70, 40) if is_sel else (35, 48, 26)
        border = (130, 200, 100) if is_sel else C_STATS_BORDER
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 1, border_radius=6)

        # Tree sprite centred in top part
        raw = get_tree_surface(tree.stage, tree.health, tree.is_dead, False, 0.0,
                               skin_id=tree.skin_id)
        sprite = pygame.transform.scale(raw, (_SW, _SH))
        sx = rect.x + (rect.w - _SW) // 2
        sy = rect.y + 8
        screen.blit(sprite, (sx, sy))

        # Key name
        label = KEY_LABELS.get(tree.key_name, tree.key_name.upper())
        display = tree.custom_name if tree.custom_name else label
        name_s = self.font_sm.render(display[:12], True, C_STATS_TITLE)
        screen.blit(name_s, (rect.x + rect.w // 2 - name_s.get_width() // 2,
                              rect.y + _SH + 12))

        # Trees grown badge
        badge_text = f"×{tree.trees_grown} 棵"
        badge_s = self.font_sm.render(badge_text, True, (120, 230, 120))
        screen.blit(badge_s, (rect.x + rect.w // 2 - badge_s.get_width() // 2,
                               rect.y + _SH + 26))

        # Stage dot
        stage_text = f"阶段 {tree.stage}"
        stage_s = self.font_sm.render(stage_text, True, C_STATS_DIM)
        screen.blit(stage_s, (rect.x + rect.w // 2 - stage_s.get_width() // 2,
                               rect.y + _SH + 42))

    def _popup_rect(self) -> pygame.Rect:
        w, h = 360, 300
        return pygame.Rect((WINDOW_W - w) // 2, (WINDOW_H - h) // 2, w, h)

    def _draw_popup(self, screen: pygame.Surface):
        tree = self.forest.trees.get(self._selected)
        if tree is None:
            return

        rect = self._popup_rect()
        popup_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        popup_surf.fill((28, 40, 20, 240))
        screen.blit(popup_surf, rect.topleft)
        pygame.draw.rect(screen, (90, 150, 70), rect, 2, border_radius=8)

        # Close button
        close_rect = pygame.Rect(rect.right - 28, rect.top + 8, 20, 20)
        self._close_rect = close_rect
        pygame.draw.rect(screen, (80, 50, 50), close_rect, border_radius=3)
        _draw_text(screen, self.font_sm, "✕", close_rect.centerx, close_rect.centery,
                   (220, 130, 130), center=True)

        label = KEY_LABELS.get(self._selected, self._selected.upper())
        display = tree.custom_name if tree.custom_name else label
        from key_tree import STAGE_NAMES
        x = rect.x + 14
        y = rect.y + 14

        _draw_text(screen, self.font_med, display, x, y, C_STATS_TITLE)
        y += 24
        _draw_text(screen, self.font_sm,
                   f"按键: {self._selected.upper()}  · 阶段: {STAGE_NAMES[tree.stage]}",
                   x, y, C_STATS_TEXT)
        y += 18
        _draw_text(screen, self.font_sm, f"已长成大树: {tree.trees_grown} 棵",
                   x, y, (120, 230, 120))
        y += 18
        _draw_text(screen, self.font_sm, f"历史总敲击: {tree.total_presses:,}",
                   x, y, C_STATS_TEXT)
        y += 18
        _draw_text(screen, self.font_sm, f"今日敲击: {tree.today_presses}",
                   x, y, C_STATS_TEXT)
        y += 22

        # Health bar
        _draw_text(screen, self.font_sm, "健康度", x, y, C_STATS_DIM)
        y += 16
        hp = tree.health
        hp_color = C_BAR_HP_HIGH if hp > 0.6 else (C_BAR_HP_MID if hp > 0.3 else C_BAR_HP_LOW)
        bw = rect.w - 28
        _draw_bar(screen, x, y, bw, 12, hp, hp_color, f"{hp*100:.0f}%", self.font_sm)
        y += 22

        # XP bar
        from key_tree import MAX_STAGE
        from config import STAGE_XP_THRESHOLDS, GRADUATION_XP
        _draw_text(screen, self.font_sm, "当前经验", x, y, C_STATS_DIM)
        y += 16
        xp_next = GRADUATION_XP if tree.stage == MAX_STAGE else (
            STAGE_XP_THRESHOLDS[tree.stage - 1] if tree.stage > 0 else 1
        )
        frac = min(1.0, tree.experience / xp_next) if xp_next else 1.0
        _draw_bar(screen, x, y, bw, 12, frac, C_BAR_XP,
                  f"{tree.experience:.0f}/{xp_next:.0f}", self.font_sm)
        y += 22

        # Misc
        _draw_text(screen, self.font_sm,
                   f"经验倍率: ×{tree.xp_multiplier:.1f}" +
                   ("  [永久]" if tree.permanent_xp_boost else ""),
                   x, y, (160, 200, 140))
        y += 18
        if tree.was_dead:
            _draw_text(screen, self.font_sm, "🌱 曾经枯死后重生", x, y, (180, 150, 80))

    def _max_scroll(self) -> int:
        trees_count = sum(1 for t in self.forest.trees.values() if t.trees_grown > 0)
        rows = (trees_count + _COLS - 1) // _COLS
        total_h = rows * (_CARD_H + _CARD_GAP) + 30
        return max(0, total_h - _CONTENT_H)


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _draw_text(surf, font, text, x, y, color, center=False, right=False):
    s = font.render(text, True, color)
    if center:
        x -= s.get_width() // 2
    elif right:
        x -= s.get_width()
    surf.blit(s, (x, y))


def _draw_bar(surf, x, y, w, h, frac, fill_color, label, font):
    pygame.draw.rect(surf, C_BAR_BG, (x, y, w, h), border_radius=3)
    if frac > 0:
        fw = max(4, int(w * frac))
        pygame.draw.rect(surf, fill_color, (x, y, fw, h), border_radius=3)
    pygame.draw.rect(surf, (60, 80, 55), (x, y, w, h), 1, border_radius=3)
    ls = font.render(label, True, (210, 230, 200))
    surf.blit(ls, (x + w // 2 - ls.get_width() // 2, y))
