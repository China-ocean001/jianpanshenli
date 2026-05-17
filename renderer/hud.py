"""
HUD: top bar and bottom status bar.
Shows climate state, daily stats, and toast notifications.
"""

from __future__ import annotations
import pygame
from typing import List

from config import (
    WINDOW_W, WINDOW_H, HUD_H, STATUS_H,
    C_HUD_BG, C_HUD_TEXT, C_STATUS_BG, C_STATUS_TEXT,
    C_CHIP_NORMAL, C_CHIP_RAIN, C_CHIP_DROUGHT,
)
from forest import Forest
from climate import ClimateState

_TOAST_DURATION = 3.5


class _Toast:
    __slots__ = ('text', 'timer')

    def __init__(self, text: str):
        self.text = text
        self.timer = _TOAST_DURATION


class HUD:
    def __init__(self, forest: Forest, shop, font_med: pygame.font.Font,
                 font_sm: pygame.font.Font):
        self.forest = forest
        self.shop = shop
        self.font_med = font_med
        self.font_sm = font_sm
        self._toasts: List[_Toast] = []
        self._prev_notifications: list = []
        # Tab button rects
        self._tab_rects: dict = {
            'forest':      pygame.Rect(156, 10, 68, 34),
            'stats':       pygame.Rect(230, 10, 68, 34),
            'grove':       pygame.Rect(304, 10, 68, 34),
            'achievement': pygame.Rect(378, 10, 68, 34),
            'shop':        pygame.Rect(452, 10, 68, 34),
        }

    def hit_test_tab(self, pos) -> str | None:
        """Returns 'forest' or 'stats' if pos hits a tab button, else None."""
        for name, rect in self._tab_rects.items():
            if rect.collidepoint(pos):
                return name
        return None

    def update(self, dt: float):
        if self.forest.notifications != self._prev_notifications:
            new = self.forest.notifications[len(self._prev_notifications):]
            for msg in new:
                self._toasts.append(_Toast(msg))
            self._prev_notifications = list(self.forest.notifications)
        for t in self._toasts[:]:
            t.timer -= dt
        self._toasts = [t for t in self._toasts if t.timer > 0]

    def draw(self, screen: pygame.Surface, active_view: str = 'forest'):
        self._draw_top_bar(screen, active_view)
        self._draw_bottom_bar(screen, active_view)
        self._draw_toasts(screen)

    # ── Top bar ───────────────────────────────────────────────────────────

    def _draw_top_bar(self, screen, active_view):
        pygame.draw.rect(screen, C_HUD_BG, (0, 0, WINDOW_W, HUD_H))
        pygame.draw.line(screen, (50, 70, 40), (0, HUD_H - 1), (WINDOW_W, HUD_H - 1))

        _draw_text(screen, self.font_med, "键盘森林", 16, 10, C_HUD_TEXT)

        # Tab buttons
        tab_labels = {'forest': '🌳 森林', 'stats': '📊 统计',
                      'grove': '🌲 树场', 'achievement': '🏆 成就',
                      'shop': '🏪 商店'}
        for name, rect in self._tab_rects.items():
            is_active = (active_view == name)
            bg = (55, 90, 45) if is_active else (30, 42, 22)
            border = (100, 160, 80) if is_active else (55, 75, 45)
            pygame.draw.rect(screen, bg, rect, border_radius=5)
            pygame.draw.rect(screen, border, rect, 1, border_radius=5)
            label_color = (220, 245, 200) if is_active else (140, 175, 125)
            ts = self.font_sm.render(tab_labels[name], True, label_color)
            screen.blit(ts, (rect.x + (rect.w - ts.get_width()) // 2,
                              rect.y + (rect.h - ts.get_height()) // 2))

        # Gold coin display
        if self.shop is not None:
            coin_str = f"🪙 {self.shop.coins}"
            coin_surf = self.font_sm.render(coin_str, True, (255, 215, 80))
            screen.blit(coin_surf, (532, 20))

        # Climate chip (only in forest view)
        if active_view == 'forest':
            climate_label = self.forest.climate.state_label
            chip_color = {
                ClimateState.NORMAL:  C_CHIP_NORMAL,
                ClimateState.RAIN:    C_CHIP_RAIN,
                ClimateState.DROUGHT: C_CHIP_DROUGHT,
            }[self.forest.climate.state]
            _draw_chip(screen, self.font_sm, f"天气: {climate_label}",
                       WINDOW_W // 2, 28, chip_color)

            if self.forest.climate.state == ClimateState.RAIN:
                remaining = int(self.forest.climate._rain_remaining)
                _draw_text(screen, self.font_sm,
                           f"暴雨剩余 {remaining // 60}:{remaining % 60:02d}",
                           WINDOW_W // 2 + 130, 20, (150, 180, 255))

        # Stats (right side, always visible)
        stats = self.forest.get_stats()
        stat_str = (f"今日: {stats['today_total']}键  "
                    f"茂盛: {stats['healthy']}  "
                    f"生病: {stats['sick']}  "
                    f"枯死: {stats['dead']}")
        _draw_text(screen, self.font_sm, stat_str, WINDOW_W - 14, 20, C_STATUS_TEXT, right=True)

    # ── Bottom bar ────────────────────────────────────────────────────────

    def _draw_bottom_bar(self, screen, active_view):
        y = WINDOW_H - STATUS_H
        pygame.draw.rect(screen, C_STATUS_BG, (0, y, WINDOW_W, STATUS_H))
        pygame.draw.line(screen, (40, 60, 35), (0, y), (WINDOW_W, y))
        if active_view == 'forest':
            hint = "点击按键查看详情  |  持续高频打字触发暴雨  |  2小时闲置触发干旱"
        elif active_view == 'stats':
            hint = "点击左侧列表查看单键详情  |  点击「保存报告」生成PNG快照"
        elif active_view == 'grove':
            hint = "展示所有已毕业的大树  |  点击树卡查看详细信息"
        elif active_view == 'shop':
            hint = "已毕业大树每天可领取金币  |  购买皮肤后点击「应用」再选择目标按键"
        else:
            hint = "点击成就卡可查看解锁条件  |  滚轮上下浏览"

        ev = self.forest.events
        if ev.active_event:
            # Left side: event chip
            lbl   = ev.event_label()
            col   = ev.event_color()
            chip_s = self.font_sm.render(lbl, True, (240, 250, 235))
            chip_w = chip_s.get_width() + 14
            chip_h = chip_s.get_height() + 6
            chip_y = y + (STATUS_H - chip_h) // 2
            pygame.draw.rect(screen, col, (4, chip_y, chip_w, chip_h), border_radius=4)
            screen.blit(chip_s, (4 + 7, chip_y + 3))
            # Right side: hint text
            hint_x = chip_w + 14
            hint_s = self.font_sm.render(hint, True, C_STATUS_TEXT)
            if hint_x + hint_s.get_width() < WINDOW_W - 4:
                screen.blit(hint_s, (hint_x, y + (STATUS_H - hint_s.get_height()) // 2))
        else:
            _draw_text(screen, self.font_sm, hint, WINDOW_W // 2, y + 10, C_STATUS_TEXT, center=True)

    # ── Toasts ────────────────────────────────────────────────────────────

    def _draw_toasts(self, screen):
        if not self._toasts:
            return
        base_y = HUD_H + 10
        for i, toast in enumerate(self._toasts[-3:]):
            frac = min(1.0, toast.timer / 0.5)          # fade-in first 0.5 s
            fade = min(1.0, toast.timer / 0.8)           # fade-out last 0.8 s
            alpha = int(220 * frac * fade)
            w = self.font_sm.size(toast.text)[0] + 20
            h = 22
            tx = (WINDOW_W - w) // 2
            ty = base_y + i * 28
            toast_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            toast_surf.fill((30, 50, 25, alpha))
            pygame.draw.rect(toast_surf, (80, 140, 70, alpha), (0, 0, w, h), 1, border_radius=4)
            ts = self.font_sm.render(toast.text, True, (210, 240, 200))
            ts.set_alpha(alpha)
            toast_surf.blit(ts, (10, 3))
            screen.blit(toast_surf, (tx, ty))


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_text(surf, font, text, x, y, color, center=False, right=False):
    s = font.render(text, True, color)
    if center:
        x -= s.get_width() // 2
    elif right:
        x -= s.get_width()
    surf.blit(s, (x, y))


def _draw_chip(surf, font, text, cx, cy, bg_color):
    s = font.render(text, True, (240, 250, 235))
    w, h = s.get_width() + 16, s.get_height() + 6
    rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
    pygame.draw.rect(surf, bg_color, rect, border_radius=5)
    surf.blit(s, (rect.x + 8, rect.y + 3))
