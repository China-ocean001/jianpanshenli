"""
AchievementView: 2-column gallery of all 18 achievements.
Unlocked cards are bright; locked ones are dimmed.
"""

from __future__ import annotations
import pygame
from typing import List

from config import (
    WINDOW_W, WINDOW_H, HUD_H, STATUS_H,
    C_STATS_BG, C_STATS_PANEL, C_STATS_BORDER,
    C_STATS_TITLE, C_STATS_TEXT, C_STATS_DIM,
)
from forest import Forest
from achievements import Achievement

_CONTENT_Y = HUD_H + 4
_CONTENT_H = WINDOW_H - HUD_H - STATUS_H
_COLS      = 2
_GAP       = 10
_CARD_W    = (WINDOW_W - (_COLS + 1) * _GAP) // _COLS   # ~590
_CARD_H    = 72
_X0        = _GAP
_COL_STEP  = _CARD_W + _GAP

# Colours
_C_UNLOCKED_BG     = (38, 55, 28)
_C_UNLOCKED_BORDER = (90, 170, 70)
_C_LOCKED_BG       = (26, 34, 20)
_C_LOCKED_BORDER   = (50, 62, 40)
_C_GOLD            = (220, 185, 60)
_C_SIDE_EFFECT     = (100, 190, 255)


class AchievementView:
    def __init__(self, forest: Forest, font_med: pygame.font.Font,
                 font_sm: pygame.font.Font):
        self.forest = forest
        self.font_med = font_med
        self.font_sm = font_sm
        self._scroll_y: int = 0

    def update(self, dt: float):
        pass

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self._scroll_y = max(0, self._scroll_y - 40)
                return True
            if event.button == 5:
                self._scroll_y = min(self._max_scroll(), self._scroll_y + 40)
                return True
        return False

    def draw(self, screen: pygame.Surface):
        screen.fill(C_STATS_BG)

        achs: List[Achievement] = self.forest.achievements.achievements
        unlocked = sum(1 for a in achs if a.unlocked)

        # Header
        hdr = f"成就  {unlocked}/{len(achs)} 已解锁"
        ts = self.font_med.render(hdr, True, C_STATS_TITLE)
        screen.blit(ts, (12, _CONTENT_Y + 4))

        # Progress bar
        bar_x, bar_y, bar_w, bar_h = 12, _CONTENT_Y + 26, WINDOW_W - 24, 8
        pygame.draw.rect(screen, (40, 55, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        if len(achs):
            fw = int(bar_w * unlocked / len(achs))
            if fw > 0:
                pygame.draw.rect(screen, _C_GOLD,
                                 (bar_x, bar_y, fw, bar_h), border_radius=4)
        pygame.draw.rect(screen, C_STATS_BORDER, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

        start_y = _CONTENT_Y + 42 - self._scroll_y

        for idx, ach in enumerate(achs):
            col = idx % _COLS
            row = idx // _COLS
            cx = _X0 + col * _COL_STEP
            cy = start_y + row * (_CARD_H + _GAP)
            card_rect = pygame.Rect(cx, cy, _CARD_W, _CARD_H)

            if cy + _CARD_H < _CONTENT_Y + 42 or cy > WINDOW_H - STATUS_H:
                continue
            self._draw_card(screen, ach, card_rect)

    def _draw_card(self, screen: pygame.Surface, ach: Achievement, rect: pygame.Rect):
        if ach.unlocked:
            bg     = _C_UNLOCKED_BG
            border = _C_UNLOCKED_BORDER
            name_color = _C_GOLD
            icon   = "🏆"
        else:
            bg     = _C_LOCKED_BG
            border = _C_LOCKED_BORDER
            name_color = C_STATS_DIM
            icon   = "🔒"

        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 1, border_radius=6)

        # Icon
        icon_s = self.font_sm.render(icon, True, name_color)
        screen.blit(icon_s, (rect.x + 10, rect.y + (rect.h - icon_s.get_height()) // 2))

        # Name + side-effect tag
        tx = rect.x + 36
        name_s = self.font_med.render(ach.name, True, name_color)
        screen.blit(name_s, (tx, rect.y + 10))
        tx += name_s.get_width() + 8

        if ach.side_effect:
            tag = " 特效 "
            tag_s = self.font_sm.render(tag, True, _C_SIDE_EFFECT)
            tag_rect = pygame.Rect(tx, rect.y + 12, tag_s.get_width() + 6, 18)
            pygame.draw.rect(screen, (20, 40, 70), tag_rect, border_radius=3)
            pygame.draw.rect(screen, _C_SIDE_EFFECT, tag_rect, 1, border_radius=3)
            screen.blit(tag_s, (tag_rect.x + 3, tag_rect.y + 1))

        # Description
        desc_color = C_STATS_TEXT if ach.unlocked else C_STATS_DIM
        desc_s = self.font_sm.render(ach.description, True, desc_color)
        screen.blit(desc_s, (rect.x + 36, rect.y + 32))

        # Unlock date (right side)
        if ach.unlocked and ach.unlocked_at:
            date_s = self.font_sm.render(ach.unlocked_at, True, C_STATS_DIM)
            screen.blit(date_s, (rect.right - date_s.get_width() - 10, rect.y + 10))

    def _max_scroll(self) -> int:
        from achievements import ALL_ACHIEVEMENTS
        rows = (len(ALL_ACHIEVEMENTS) + _COLS - 1) // _COLS
        total_h = rows * (_CARD_H + _GAP) + 42
        return max(0, total_h - _CONTENT_H)
