"""
StatsView: full-screen statistics and forest report view.
Replaces the forest grid when the user switches to the "统计" tab.
"""

from __future__ import annotations
import os
import math
from datetime import datetime, date
from typing import Optional, List, Tuple

import pygame

from config import (
    WINDOW_W, WINDOW_H, HUD_H, STATUS_H,
    KEY_RECTS, KEY_LABELS, GRID_X, GRID_Y, KEY_H,
    REPORTS_DIR,
    C_STATS_BG, C_STATS_PANEL, C_STATS_BORDER,
    C_STATS_TITLE, C_STATS_TEXT, C_STATS_DIM,
    C_HEATMAP_COLD, C_HEATMAP_HOT,
    C_CHART_BAR, C_CHART_LINE, C_CHART_GRID,
    C_HUD_TEXT, C_BAR_HP_HIGH, C_BAR_HP_MID, C_BAR_HP_LOW,
)
from forest import Forest
from database import Database

# ── Layout constants ──────────────────────────────────────────────────────────
_CONTENT_Y  = HUD_H + 6         # top of content area
_CONTENT_H  = WINDOW_H - HUD_H - STATUS_H - 6
_LEFT_X     = 8
_LEFT_W     = 340
_RIGHT_X    = _LEFT_X + _LEFT_W + 8
_RIGHT_W    = WINDOW_W - _RIGHT_X - 8
_HEATMAP_Y  = _CONTENT_Y + 390  # heatmap starts here
_HEATMAP_H  = 155
_HM_SCALE   = 0.43              # scale down keyboard for heatmap

_ACTIVE_ROWS    = 10   # visible rows in the leaderboard at once
_ACTIVE_ROW_H   = 20
# Panel rect for the leaderboard (used for scroll hit-testing)
_ACTIVE_PANEL   = pygame.Rect(_LEFT_X, _CONTENT_Y + 156, _LEFT_W, 225)

# Heatmap horizontal offset: centre the scaled keyboard in the window
_HM_KBD_W   = int((1172 - GRID_X) * _HM_SCALE)
_HM_X0      = (WINDOW_W - _HM_KBD_W) // 2


def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _draw_panel(surf, rect, title='', font_sm=None):
    """Draw a rounded dark panel with optional title."""
    pygame.draw.rect(surf, C_STATS_PANEL, rect, border_radius=6)
    pygame.draw.rect(surf, C_STATS_BORDER, rect, 1, border_radius=6)
    if title and font_sm:
        ts = font_sm.render(title, True, C_STATS_TITLE)
        surf.blit(ts, (rect.x + 8, rect.y + 6))


def _draw_txt(surf, font, text, x, y, color, right=False, center=False):
    s = font.render(text, True, color)
    if right:
        x -= s.get_width()
    elif center:
        x -= s.get_width() // 2
    surf.blit(s, (x, y))


class StatsView:
    def __init__(self, forest: Forest, db: Database,
                 font_med: pygame.font.Font, font_sm: pygame.font.Font):
        self.forest = forest
        self.db = db
        self.font_med = font_med
        self.font_sm = font_sm

        self._selected_key: Optional[str] = None
        self._active_list_cache: List[Tuple[str, int]] = []  # all keys sorted by weekly count
        self._active_scroll: int = 0
        self._endangered_cache: List[Tuple[str, float, int]] = []
        self._cache_timer = 0.0
        self._cache_ttl = 5.0      # refresh caches every 5 s
        self._hovered_row: Optional[str] = None

        # Save button rect
        self._save_btn  = pygame.Rect(_RIGHT_X,       _CONTENT_Y + 340, 180, 34)
        self._clear_btn = pygame.Rect(_RIGHT_X + 190, _CONTENT_Y + 340, 160, 34)
        self._save_flash = 0.0

        # Signal for main.py to open the clear dialog
        self.requested_clear: bool = False

        # List item rects for top_keys (built each draw call)
        self._list_rects: dict[str, pygame.Rect] = {}

        # Pre-rendered heatmap (invalidated on cache refresh)
        self._heatmap_surf: Optional[pygame.Surface] = None
        # Heatmap mode toggle: '1h' | 'today' | '7d'
        self._hm_mode: str = '7d'
        self._hm_btn_rects: dict = {}    # built in _draw_heatmap
        self._hm_live_timer: float = 0.0  # refresh timer for live modes

        self._refresh_caches()

    # ── Public API ──────────────────────────────────────────────────────────

    def update(self, dt: float):
        self._cache_timer += dt
        if self._cache_timer >= self._cache_ttl:
            self._refresh_caches()
            self._cache_timer = 0.0
        if self._save_flash > 0:
            self._save_flash -= dt
        # Live modes ('1h', 'today') rebuild heatmap every 10 s independently
        if self._hm_mode != '7d':
            self._hm_live_timer += dt
            if self._hm_live_timer >= 10.0:
                self._heatmap_surf = None
                self._build_heatmap()
                self._hm_live_timer = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Save button
            if self._save_btn.collidepoint(pos):
                self._do_save_report()
                self._save_flash = 1.0
                return True
            # Clear data button
            if self._clear_btn.collidepoint(pos):
                self.requested_clear = True
                return True
            # Heatmap mode toggle buttons
            for mode, rect in self._hm_btn_rects.items():
                if rect.collidepoint(pos):
                    if self._hm_mode != mode:
                        self._hm_mode = mode
                        self._heatmap_surf = None
                        self._build_heatmap()
                        self._hm_live_timer = 0.0
                    return True
            # List row click
            for key_name, rect in self._list_rects.items():
                if rect.collidepoint(pos):
                    self._selected_key = key_name
                    return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            mx, my = event.pos
            if _ACTIVE_PANEL.collidepoint(mx, my):
                self._scroll_active(-1 if event.button == 4 else 1)
                return True

        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if _ACTIVE_PANEL.collidepoint(mx, my):
                self._scroll_active(-event.y)
                return True

        elif event.type == pygame.MOUSEMOTION:
            self._hovered_row = None
            for key_name, rect in self._list_rects.items():
                if rect.collidepoint(event.pos):
                    self._hovered_row = key_name
        return False

    def _scroll_active(self, delta: int):
        total = len(self._active_list_cache)
        max_scroll = max(0, total - _ACTIVE_ROWS)
        self._active_scroll = max(0, min(self._active_scroll + delta, max_scroll))

    def draw(self, screen: pygame.Surface):
        # Background
        pygame.draw.rect(screen, C_STATS_BG,
                         (0, HUD_H, WINDOW_W, WINDOW_H - HUD_H - STATUS_H))

        self._draw_summary(screen)
        self._draw_top_active(screen)
        self._draw_key_detail(screen)
        self._draw_save_btn(screen)
        self._draw_clear_btn(screen)
        self._draw_heatmap(screen)

    # ── Left panel: Summary ─────────────────────────────────────────────────

    def _draw_summary(self, screen):
        panel = pygame.Rect(_LEFT_X, _CONTENT_Y, _LEFT_W, 148)
        _draw_panel(screen, panel, '森林总览', self.font_sm)

        s = self.db.get_forest_summary()
        items = [
            ('茂盛', s['healthy'],   C_BAR_HP_HIGH),
            ('生病', s['sick'],      C_BAR_HP_MID),
            ('枯死', s['dead'],      C_BAR_HP_LOW),
            ('未种', s['unplanted'], C_STATS_DIM),
        ]
        y = _CONTENT_Y + 26
        for i, (label, count, color) in enumerate(items):
            col = i % 2
            row = i // 2
            bx = _LEFT_X + 12 + col * (_LEFT_W // 2 - 8)
            by = y + row * 46
            pygame.draw.rect(screen, _darken(color, 0.25),
                             (bx, by, _LEFT_W // 2 - 16, 38), border_radius=4)
            _draw_txt(screen, self.font_med, str(count),
                      bx + (_LEFT_W // 2 - 16) // 2, by + 4, color, center=True)
            _draw_txt(screen, self.font_sm, label,
                      bx + (_LEFT_W // 2 - 16) // 2, by + 22, C_STATS_DIM, center=True)

        # Today total
        ty = _CONTENT_Y + 118
        _draw_txt(screen, self.font_sm,
                  f"今日总按键: {s['today_total']}  历史总计: {s['total_all']}",
                  _LEFT_X + 12, ty, C_STATS_TEXT)

    # ── Left panel: Active Leaderboard ─────────────────────────────────────

    def _draw_top_active(self, screen):
        total = len(self._active_list_cache)
        panel = _ACTIVE_PANEL
        _draw_panel(screen, panel, f'活跃榜  共 {total} 键', self.font_sm)

        self._list_rects.clear()

        # Clamp scroll
        max_scroll = max(0, total - _ACTIVE_ROWS)
        self._active_scroll = max(0, min(self._active_scroll, max_scroll))

        rows_top = _CONTENT_Y + 178
        rows_h   = _ACTIVE_ROWS * _ACTIVE_ROW_H          # 200 px

        # Clip to prevent rows bleeding outside the panel
        old_clip = screen.get_clip()
        clip = pygame.Rect(_LEFT_X + 2, rows_top, _LEFT_W - 4, rows_h)
        screen.set_clip(clip)

        visible = self._active_list_cache[self._active_scroll:
                                          self._active_scroll + _ACTIVE_ROWS]
        for i, (key_name, count) in enumerate(visible):
            rank = self._active_scroll + i + 1
            ry   = rows_top + i * _ACTIVE_ROW_H
            row_rect = pygame.Rect(_LEFT_X + 6, ry, _LEFT_W - 16, _ACTIVE_ROW_H)
            self._list_rects[key_name] = row_rect

            if key_name == self._selected_key:
                pygame.draw.rect(screen, (55, 90, 45), row_rect, border_radius=3)
            elif key_name == self._hovered_row:
                pygame.draw.rect(screen, (38, 55, 30), row_rect, border_radius=3)

            label  = KEY_LABELS.get(key_name, key_name.upper())
            tree   = self.forest.trees.get(key_name)
            custom = tree.custom_name if tree and tree.custom_name else ''
            display = f"{label}({custom})" if custom else label

            rank_color = (200, 180, 60) if rank <= 3 else C_STATS_DIM
            _draw_txt(screen, self.font_sm, f"{rank}.", _LEFT_X + 12, ry + 1, rank_color)
            _draw_txt(screen, self.font_sm, display, _LEFT_X + 34, ry + 1, C_STATS_TEXT)
            if count > 0:
                _draw_txt(screen, self.font_sm, f"{count:,}次",
                          _LEFT_X + _LEFT_W - 16, ry + 1, C_STATS_TEXT, right=True)
            else:
                _draw_txt(screen, self.font_sm, "—",
                          _LEFT_X + _LEFT_W - 16, ry + 1, C_STATS_DIM, right=True)

        screen.set_clip(old_clip)

        # Scrollbar
        if total > _ACTIVE_ROWS:
            sb_x = _LEFT_X + _LEFT_W - 6
            sb_w = 4
            pygame.draw.rect(screen, (38, 52, 32),
                             (sb_x, rows_top, sb_w, rows_h), border_radius=2)
            thumb_h = max(16, rows_h * _ACTIVE_ROWS // total)
            thumb_y = rows_top + (rows_h - thumb_h) * self._active_scroll // max_scroll
            pygame.draw.rect(screen, (90, 140, 75),
                             (sb_x, thumb_y, sb_w, thumb_h), border_radius=2)

        # ── Endangered header ──────────────────────────────────────────────
        end_panel = pygame.Rect(_LEFT_X, _CONTENT_Y + 389, _LEFT_W, 145)
        _draw_panel(screen, end_panel, '濒危树（健康度最低）', self.font_sm)

        y2 = _CONTENT_Y + 411
        for key_name, health, stage in self._endangered_cache[:6]:
            row_rect2 = pygame.Rect(_LEFT_X + 6, y2, _LEFT_W - 12, 18)
            self._list_rects[key_name] = row_rect2

            if key_name == self._selected_key:
                pygame.draw.rect(screen, (55, 90, 45), row_rect2, border_radius=3)
            elif key_name == self._hovered_row:
                pygame.draw.rect(screen, (38, 55, 30), row_rect2, border_radius=3)

            label = KEY_LABELS.get(key_name, key_name.upper())
            pct = health * 100
            hp_color = C_BAR_HP_HIGH if health > 0.6 else (C_BAR_HP_MID if health > 0.3 else C_BAR_HP_LOW)
            _draw_txt(screen, self.font_sm, label, _LEFT_X + 12, y2 + 1, C_STATS_TEXT)
            _draw_txt(screen, self.font_sm, f"{pct:.0f}%",
                      _LEFT_X + _LEFT_W - 8, y2 + 1, hp_color, right=True)
            bar_w = 70
            bx = _LEFT_X + _LEFT_W - 10 - bar_w - 32
            pygame.draw.rect(screen, (40, 52, 35), (bx, y2 + 5, bar_w, 8), border_radius=2)
            fw = max(2, int(bar_w * health))
            pygame.draw.rect(screen, hp_color, (bx, y2 + 5, fw, 8), border_radius=2)
            y2 += 20

    # ── Right panel: Key Detail ─────────────────────────────────────────────

    def _draw_key_detail(self, screen):
        panel = pygame.Rect(_RIGHT_X, _CONTENT_Y, _RIGHT_W, 330)
        _draw_panel(screen, panel, '', self.font_sm)

        if self._selected_key is None:
            # Instructions
            msgs = [
                "← 从左侧列表点击选择一个按键",
                "查看该键的详细统计数据：",
                "  • 今日 / 本周 / 本月按键次数",
                "  • 健康度变化趋势图",
                "  • 每日按键量柱状图",
            ]
            for i, m in enumerate(msgs):
                _draw_txt(screen, self.font_sm, m,
                          _RIGHT_X + 16, _CONTENT_Y + 16 + i * 22,
                          C_STATS_DIM if i > 0 else C_STATS_TITLE)
            return

        key = self._selected_key
        tree = self.forest.trees.get(key)
        label = KEY_LABELS.get(key, key.upper())
        custom = (tree.custom_name if tree and tree.custom_name else '').strip()
        title = f"{label}  {custom}" if custom else label

        x0 = _RIGHT_X + 12
        y0 = _CONTENT_Y + 10

        # Title row
        _draw_txt(screen, self.font_med, title, x0, y0, C_STATS_TITLE)

        if tree:
            stage_s = tree.stage_name
            hp_pct = f"{tree.health * 100:.0f}%"
            hp_color = (C_BAR_HP_HIGH if tree.health > 0.6
                        else C_BAR_HP_MID if tree.health > 0.3 else C_BAR_HP_LOW)
            _draw_txt(screen, self.font_sm,
                      f"阶段: {stage_s}  健康: {hp_pct}  总按键: {tree.total_presses:,}",
                      x0, y0 + 22, C_STATS_TEXT)

            # Day/week/month counts
            daily  = self.db.get_key_period_stats(key, 1)
            weekly = self.db.get_key_period_stats(key, 7)
            monthly= self.db.get_key_period_stats(key, 30)
            day_c   = sum(c for _,c in daily)
            week_c  = sum(c for _,c in weekly)
            month_c = sum(c for _,c in monthly)

            # Created-at
            if tree.last_used:
                days_old = (date.today() - tree.last_used.date()).days
                planted_str = f"最近使用: {days_old}天前"
            else:
                planted_str = "从未使用"

            period_items = [
                ("今日", day_c), ("本周", week_c), ("本月", month_c),
            ]
            py = y0 + 44
            for label_p, cnt in period_items:
                _draw_txt(screen, self.font_sm, label_p, x0, py, C_STATS_DIM)
                _draw_txt(screen, self.font_med, f"{cnt:,}", x0, py + 14, C_STATS_TEXT)
                x0 += 120
            x0 = _RIGHT_X + 12
            _draw_txt(screen, self.font_sm, planted_str, x0 + 360, py + 14, C_STATS_DIM)

            # Bar chart: last 14 days
            chart_y = _CONTENT_Y + 108
            chart_rect = pygame.Rect(x0, chart_y, _RIGHT_W - 24, 100)
            _draw_txt(screen, self.font_sm, "近14天按键量", x0, chart_y - 14, C_STATS_DIM)
            bar_data = self.db.get_key_period_stats(key, 14)
            self._draw_bar_chart(screen, bar_data, chart_rect, 14)

            # Line chart: health history (30 days)
            health_y = _CONTENT_Y + 220
            health_rect = pygame.Rect(x0, health_y, _RIGHT_W - 24, 90)
            _draw_txt(screen, self.font_sm, "近30天健康度变化", x0, health_y - 14, C_STATS_DIM)
            health_data = [(d, h) for d, h, _ in self.db.get_health_history(key, 30)]
            # Add current value
            if tree:
                health_data.append((date.today().isoformat(), tree.health))
            self._draw_line_chart(screen, health_data, health_rect)

    # ── Save button ─────────────────────────────────────────────────────────

    def _draw_save_btn(self, screen):
        btn = self._save_btn
        if self._save_flash > 0:
            frac = self._save_flash / 1.0
            bg = _lerp_color((30, 45, 25), (50, 140, 70), frac)
        else:
            bg = (35, 55, 30)
        pygame.draw.rect(screen, bg, btn, border_radius=6)
        pygame.draw.rect(screen, (80, 140, 65), btn, 1, border_radius=6)
        label = "✓ 已保存!" if self._save_flash > 0.5 else "📄 保存报告 PNG"
        ts = self.font_sm.render(label, True, (190, 240, 170))
        screen.blit(ts, (btn.x + (btn.w - ts.get_width()) // 2,
                          btn.y + (btn.h - ts.get_height()) // 2))

    def _draw_clear_btn(self, screen):
        btn = self._clear_btn
        pygame.draw.rect(screen, (55, 28, 22), btn, border_radius=6)
        pygame.draw.rect(screen, (160, 70, 50), btn, 1, border_radius=6)
        ts = self.font_sm.render("🗑 清除全部数据", True, (220, 120, 100))
        screen.blit(ts, (btn.x + (btn.w - ts.get_width()) // 2,
                          btn.y + (btn.h - ts.get_height()) // 2))

    # ── Heatmap ─────────────────────────────────────────────────────────────

    def _draw_heatmap(self, screen):
        hm_panel = pygame.Rect(0, _HEATMAP_Y - 4, WINDOW_W, _HEATMAP_H + 30)
        pygame.draw.rect(screen, C_STATS_PANEL, hm_panel)
        pygame.draw.line(screen, C_STATS_BORDER, (0, _HEATMAP_Y - 4), (WINDOW_W, _HEATMAP_Y - 4))

        mode_labels = {'1h': '1小时', 'today': '今日', '7d': '7天'}
        title_str = f"键盘热力图（{mode_labels[self._hm_mode]}按键量）"
        _draw_txt(screen, self.font_sm, title_str, 10, _HEATMAP_Y, C_STATS_TITLE)

        # Toggle buttons – three pills aligned to the right of the header row
        btn_w, btn_h, btn_gap = 52, 20, 4
        total_w = 3 * btn_w + 2 * btn_gap
        bx = WINDOW_W - total_w - 12
        by = _HEATMAP_Y - 1
        self._hm_btn_rects.clear()
        for mode in ('1h', 'today', '7d'):
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            self._hm_btn_rects[mode] = rect
            is_active = (self._hm_mode == mode)
            bg     = (55, 100, 50) if is_active else (30, 42, 22)
            border = (100, 180, 80) if is_active else (55, 75, 45)
            pygame.draw.rect(screen, bg, rect, border_radius=4)
            pygame.draw.rect(screen, border, rect, 1, border_radius=4)
            lbl_color = (220, 245, 200) if is_active else (130, 160, 120)
            ls = self.font_sm.render(mode_labels[mode], True, lbl_color)
            screen.blit(ls, (rect.x + (btn_w - ls.get_width()) // 2,
                             rect.y + (btn_h - ls.get_height()) // 2))
            bx += btn_w + btn_gap

        if self._heatmap_surf is not None:
            screen.blit(self._heatmap_surf, (_HM_X0, _HEATMAP_Y + 18))

    def _build_heatmap(self):
        """Build a scaled keyboard image coloured by activity for the current mode."""
        if self._hm_mode == '7d':
            counts = dict(self.db.get_top_keys(n=200, period_days=7))
        elif self._hm_mode == 'today':
            counts = {k: t.today_presses for k, t in self.forest.trees.items()}
        else:  # '1h'
            counts = self.forest.get_hour_presses()

        max_c = max(counts.values()) if counts else 1

        h_surf = pygame.Surface((_HM_KBD_W + 50, _HEATMAP_H), pygame.SRCALPHA)
        h_surf.fill((0, 0, 0, 0))

        font = self.font_sm
        for key_name, (rx, ry, rw, rh) in KEY_RECTS.items():
            hx = int((rx - GRID_X) * _HM_SCALE)
            hy = int((ry - GRID_Y) * _HM_SCALE)
            hw = max(1, int(rw * _HM_SCALE))
            hh = max(1, int(rh * _HM_SCALE))

            count = counts.get(key_name, 0)
            t = (count / max_c) ** 0.5   # sqrt for better visual distribution
            color = _lerp_color(C_HEATMAP_COLD, C_HEATMAP_HOT, t)

            pygame.draw.rect(h_surf, color, (hx, hy, hw, hh), border_radius=2)
            pygame.draw.rect(h_surf, (0, 0, 0, 80), (hx, hy, hw, hh), 1, border_radius=2)

            # Tiny label for larger keys
            if hw >= 16 and hh >= 14:
                lbl = KEY_LABELS.get(key_name, '')[:3]
                try:
                    ts = font.render(lbl, True, (0, 0, 0, 160))
                    lx = hx + (hw - ts.get_width()) // 2
                    ly = hy + (hh - ts.get_height()) // 2
                    h_surf.blit(ts, (lx, ly))
                except Exception:
                    pass

        self._heatmap_surf = h_surf

    # ── Charts ──────────────────────────────────────────────────────────────

    def _draw_bar_chart(self, screen, data: List[Tuple[str, int]],
                        rect: pygame.Rect, slots: int = 14):
        pygame.draw.rect(screen, (25, 35, 20), rect, border_radius=3)

        if not data:
            _draw_txt(screen, self.font_sm, "暂无数据",
                      rect.centerx, rect.centery, C_STATS_DIM, center=True)
            return

        max_v = max(c for _, c in data) or 1
        bar_w = max(2, (rect.w - 4) // slots - 1)
        x_step = (rect.w - 4) / slots

        # Grid line at half
        half_y = rect.y + rect.h // 2
        pygame.draw.line(screen, C_CHART_GRID,
                         (rect.x, half_y), (rect.x + rect.w, half_y))

        # Bars
        for i, (day, count) in enumerate(data[-slots:]):
            bh = max(2, int((count / max_v) * (rect.h - 4)))
            bx = int(rect.x + 2 + i * x_step)
            by = rect.y + rect.h - bh - 2
            pygame.draw.rect(screen, C_CHART_BAR, (bx, by, bar_w, bh), border_radius=1)

        # Max value label
        _draw_txt(screen, self.font_sm, str(max_v),
                  rect.x + rect.w - 2, rect.y + 2, C_STATS_DIM, right=True)

    def _draw_line_chart(self, screen, data: List[Tuple[str, float]],
                         rect: pygame.Rect):
        pygame.draw.rect(screen, (25, 35, 20), rect, border_radius=3)

        if len(data) < 2:
            _draw_txt(screen, self.font_sm, "数据不足",
                      rect.centerx, rect.centery, C_STATS_DIM, center=True)
            return

        # Horizontal guide lines at 0.5 and 1.0
        for frac in [0.5, 1.0]:
            gy = rect.y + rect.h - int(frac * (rect.h - 4)) - 2
            pygame.draw.line(screen, C_CHART_GRID, (rect.x, gy), (rect.x + rect.w, gy))

        n = len(data)
        pts = []
        for i, (_, health) in enumerate(data):
            px = rect.x + int(i / (n - 1) * (rect.w - 4)) + 2
            py = rect.y + rect.h - int(health * (rect.h - 4)) - 2
            pts.append((px, py))

        if len(pts) >= 2:
            pygame.draw.lines(screen, C_CHART_LINE, False, pts, 2)
            for pt in pts[::max(1, n // 10)]:
                pygame.draw.circle(screen, C_CHART_LINE, pt, 2)

        # 50% label
        mid_y = rect.y + (rect.h - 4) // 2 + 2
        pygame.draw.line(screen, (55, 75, 50), (rect.x, mid_y), (rect.x + rect.w, mid_y))
        _draw_txt(screen, self.font_sm, "50%",
                  rect.x + rect.w - 2, mid_y - 12, C_STATS_DIM, right=True)

    # ── Save PNG report ─────────────────────────────────────────────────────

    def _do_save_report(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(REPORTS_DIR, f"report_{ts_str}.png")

        surf = pygame.Surface((WINDOW_W, WINDOW_H))
        surf.fill(C_STATS_BG)

        # Title block
        title_s = self.font_med.render(
            f"键盘森林报告  {datetime.now().strftime('%Y-%m-%d %H:%M')}", True, C_STATS_TITLE)
        surf.blit(title_s, (16, 8))

        # Forest summary
        s = self.db.get_forest_summary()
        summary_str = (f"茂盛: {s['healthy']}  生病: {s['sick']}  "
                       f"枯死: {s['dead']}  未种: {s['unplanted']}  "
                       f"今日: {s['today_total']}键  历史: {s['total_all']}键")
        ss = self.font_sm.render(summary_str, True, C_STATS_TEXT)
        surf.blit(ss, (16, 32))

        # Top active keys (column)
        top = self.db.get_top_keys(n=10, period_days=7)
        surf.blit(self.font_sm.render("── 本周最活跃 Top 10 ──", True, C_STATS_TITLE), (16, 56))
        for i, (kn, cnt) in enumerate(top):
            lbl = KEY_LABELS.get(kn, kn.upper())
            row_s = self.font_sm.render(f"  {i+1}. {lbl:<10} {cnt:,}次", True, C_STATS_TEXT)
            surf.blit(row_s, (16, 74 + i * 18))

        # Endangered
        end = self.db.get_endangered_keys(n=10)
        surf.blit(self.font_sm.render("── 濒危树 ──", True, C_STATS_TITLE), (260, 56))
        for i, (kn, health, _stage) in enumerate(end):
            lbl = KEY_LABELS.get(kn, kn.upper())
            row_s = self.font_sm.render(
                f"  {lbl:<10} {health*100:.0f}%", True, C_STATS_TEXT)
            surf.blit(row_s, (260, 74 + i * 18))

        # Heatmap
        self._build_heatmap()
        if self._heatmap_surf:
            hm_label = self.font_sm.render("── 键盘热力图 ──", True, C_STATS_TITLE)
            surf.blit(hm_label, (16, 260))
            surf.blit(self._heatmap_surf, (_HM_X0, 278))

        pygame.image.save(surf, path)
        self.forest._notify(f"报告已保存: {path}")

    # ── Cache helpers ───────────────────────────────────────────────────────

    def _refresh_caches(self):
        # All keys that have press data, sorted by weekly count desc
        db_rows = self.db.get_top_keys(n=len(KEY_RECTS), period_days=7)
        db_key_set = {k for k, _ in db_rows}
        # Append keys with no press data at the end (count = 0)
        remaining = [(k, 0) for k in KEY_RECTS if k not in db_key_set]
        self._active_list_cache = db_rows + remaining

        self._endangered_cache = self.db.get_endangered_keys(n=6)
        self._heatmap_surf = None   # invalidate heatmap; rebuild on next draw
        self._build_heatmap()


def _darken(color, factor):
    return tuple(max(0, int(c * factor)) for c in color[:3])
