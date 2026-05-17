"""
DetailView: right-side panel showing per-key stats.
Slides in/out with animation when a key is clicked.
"""

from __future__ import annotations
import pygame
from typing import Optional

from config import (
    WINDOW_W, WINDOW_H, HUD_H, STATUS_H,
    DETAIL_W, DETAIL_ANIM_SPEED,
    C_DETAIL_BG, C_DETAIL_TITLE,
    C_BAR_BG, C_BAR_XP, C_BAR_HP_HIGH, C_BAR_HP_MID, C_BAR_HP_LOW,
    C_HUD_TEXT, C_STATUS_TEXT,
    HIGH_FREQ_TOP20_MULT, HIGH_FREQ_TOP40_MULT,
)
from forest import Forest
from renderer.tree_sprites import get_tree_surface, TREE_W, TREE_H
from shop import SKIN_ID_TO_NAME, SKIN_ITEMS, SKIN_SWATCH
from events import EVENT_META

_TREE_LARGE_SCALE = 2.0
_LTW = int(TREE_W * _TREE_LARGE_SCALE)
_LTH = int(TREE_H * _TREE_LARGE_SCALE)

_PANEL_H = WINDOW_H - HUD_H - STATUS_H


class DetailView:
    def __init__(self, forest: Forest, font_med: pygame.font.Font,
                 font_sm: pygame.font.Font, shop=None):
        self.forest = forest
        self.font_med = font_med
        self.font_sm = font_sm
        self.shop = shop

        self._target_key: Optional[str] = None
        self._slide_x: float = WINDOW_W
        self._target_slide_x: float = WINDOW_W
        self._open = False
        self._editing_name = False
        self._name_input = ""
        self._ime_composition = ""
        self._close_rect: Optional[pygame.Rect] = None
        self._name_rect: Optional[pygame.Rect] = None
        self._skin_chip_rects: list = []   # [(skin_id, pygame.Rect), ...]
        self._apply_all_rect: Optional[pygame.Rect] = None

    # ── Public API ──────────────────────────────────────────────────────────

    def open(self, key_name: str):
        if self._editing_name:
            self._commit_name()
            self._editing_name = False
            self._ime_composition = ""
            pygame.key.stop_text_input()
        self._target_key = key_name
        self._target_slide_x = WINDOW_W - DETAIL_W
        self._open = True
        tree = self.forest.trees.get(key_name)
        if tree:
            self._name_input = tree.custom_name

    def close(self):
        self._target_slide_x = WINDOW_W
        self._open = False
        if self._editing_name:
            self._editing_name = False
            self._ime_composition = ""
            pygame.key.stop_text_input()

    def toggle(self, key_name: str):
        if self._open and self._target_key == key_name:
            self.close()
        else:
            self.open(key_name)

    @property
    def is_open(self) -> bool:
        return self._open

    def update(self, dt: float):
        diff = self._target_slide_x - self._slide_x
        step = DETAIL_ANIM_SPEED * dt
        if abs(diff) <= step:
            self._slide_x = self._target_slide_x
        else:
            self._slide_x += step if diff > 0 else -step

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if event was consumed."""
        if not self._open:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self._close_rect and self._close_rect.collidepoint(mx, my):
                self.close()
                return True
            panel_x = int(self._slide_x)
            if panel_x <= mx <= panel_x + DETAIL_W:
                # Skin chip click (must check before name rect)
                for skin_id, rect in self._skin_chip_rects:
                    if rect.collidepoint(mx, my):
                        self._apply_skin_to_current(skin_id)
                        return True
                # Apply-all button
                if self._apply_all_rect and self._apply_all_rect.collidepoint(mx, my):
                    self._apply_skin_to_all()
                    return True
                if self._name_rect and self._name_rect.collidepoint(mx, my):
                    if not self._editing_name:
                        self._editing_name = True
                        self._ime_composition = ""
                        pygame.key.start_text_input()
                else:
                    if self._editing_name:
                        self._commit_name()
                        self._editing_name = False
                        self._ime_composition = ""
                        pygame.key.stop_text_input()
                return True

        if self._editing_name:
            # Committed text from keyboard or IME
            if event.type == pygame.TEXTINPUT:
                if len(self._name_input) + len(event.text) <= 20:
                    self._name_input += event.text
                self._ime_composition = ""
                return True

            # IME composition preview (not yet committed)
            if event.type == pygame.TEXTEDITING:
                self._ime_composition = event.text
                return True

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self._commit_name()
                    self._editing_name = False
                    self._ime_composition = ""
                    pygame.key.stop_text_input()
                elif event.key == pygame.K_BACKSPACE:
                    if self._ime_composition:
                        self._ime_composition = ""
                    else:
                        self._name_input = self._name_input[:-1]
                return True

        return False

    def draw(self, screen: pygame.Surface):
        if self._slide_x >= WINDOW_W:
            return

        self._skin_chip_rects = []   # rebuild each frame

        panel_x = int(self._slide_x)
        panel_rect = pygame.Rect(panel_x, HUD_H, DETAIL_W, _PANEL_H)

        bg_surf = pygame.Surface((DETAIL_W, _PANEL_H), pygame.SRCALPHA)
        bg_surf.fill((30, 42, 25, 230))
        screen.blit(bg_surf, (panel_x, HUD_H))
        pygame.draw.rect(screen, (60, 85, 50), panel_rect, 1)

        tree = self.forest.trees.get(self._target_key)
        if tree is None:
            return

        y = HUD_H + 14
        x = panel_x + 12
        w = DETAIL_W - 24

        # Close button
        close_rect = pygame.Rect(panel_x + DETAIL_W - 28, HUD_H + 8, 20, 20)
        self._close_rect = close_rect
        pygame.draw.rect(screen, (80, 50, 50), close_rect, border_radius=3)
        _draw_text(screen, self.font_sm, "✕", close_rect.centerx, close_rect.centery,
                   (220, 130, 130), center=True)

        # Large tree sprite
        large_surf = pygame.transform.scale(
            get_tree_surface(tree.stage, tree.health, tree.is_dead, False, 0.0,
                             skin_id=tree.skin_id),
            (_LTW, _LTH)
        )
        screen.blit(large_surf, (panel_x + (DETAIL_W - _LTW) // 2, y))
        y += _LTH + 8

        # Stage name
        _draw_text(screen, self.font_med, tree.stage_name, panel_x + DETAIL_W // 2, y,
                   C_DETAIL_TITLE, center=True)
        y += 20

        # Key label
        key_display = self._target_key.upper() if self._target_key else ""
        _draw_text(screen, self.font_sm, f"按键: {key_display}", x, y, C_HUD_TEXT)
        y += 18

        # Custom name input (supports Chinese via IME)
        if self._editing_name:
            name_color = (160, 220, 160)
        else:
            name_color = (140, 180, 140)
        name_rect = pygame.Rect(x, y, w, 22)
        self._name_rect = name_rect
        pygame.draw.rect(screen, (40, 60, 35), name_rect, border_radius=3)
        if self._editing_name:
            pygame.draw.rect(screen, (100, 180, 100), name_rect, 1, border_radius=3)
        if self._editing_name and self._ime_composition:
            # Show committed text + IME composition in yellow + cursor
            pre_surf = self.font_sm.render(self._name_input, True, name_color)
            cmp_surf = self.font_sm.render(self._ime_composition + "|", True, (220, 240, 100))
            screen.blit(pre_surf, (x + 4, y + 3))
            screen.blit(cmp_surf, (x + 4 + pre_surf.get_width(), y + 3))
        elif self._editing_name:
            _draw_text(screen, self.font_sm, self._name_input + "|", x + 4, y + 3, name_color)
        else:
            _draw_text(screen, self.font_sm, tree.custom_name or "(点击命名)", x + 4, y + 3, name_color)
        y += 28

        # XP progress bar
        _draw_label(screen, self.font_sm, "经验值", x, y, w)
        y += 16
        xp_for_next = tree.xp_for_next_stage
        if xp_for_next and xp_for_next > 0:
            frac = min(1.0, tree.experience / xp_for_next)
            xp_label = (f"毕业进度 {tree.experience:.0f}/{xp_for_next:.0f}"
                        if tree.stage == 5 else f"{tree.experience:.0f}/{xp_for_next:.0f}")
        else:
            frac, xp_label = 1.0, "—"
        _draw_bar(screen, x, y, w, 12, frac, C_BAR_XP, xp_label, self.font_sm)
        y += 22

        # Health bar
        _draw_label(screen, self.font_sm, "健康度", x, y, w)
        y += 16
        hp = tree.health
        hp_color = C_BAR_HP_HIGH if hp > 0.6 else (C_BAR_HP_MID if hp > 0.3 else C_BAR_HP_LOW)
        _draw_bar(screen, x, y, w, 12, hp, hp_color, f"{hp*100:.0f}%", self.font_sm)
        y += 20

        # ── XP multiplier breakdown ──────────────────────────────────────
        _draw_divider(screen, x, panel_x + DETAIL_W - 12, y)
        y += 5
        _draw_text(screen, self.font_sm, "经验加成分析", x, y, (160, 200, 150))
        y += 17

        ev = self.forest.events
        em = ev.xp_mult(self._target_key, tree)
        climate = self.forest.climate

        # Frequency tier row
        if tree.permanent_xp_boost:
            freq_reason = f"Ctrl守护者成就 ×{tree.xp_multiplier:.1f}"
            freq_color  = (200, 240, 160)
        elif tree.xp_multiplier >= HIGH_FREQ_TOP20_MULT:
            freq_reason = f"高频按键前10% ×{tree.xp_multiplier:.1f}"
            freq_color  = (180, 230, 160)
        elif tree.xp_multiplier >= HIGH_FREQ_TOP40_MULT:
            freq_reason = f"较高频前20% ×{tree.xp_multiplier:.1f}"
            freq_color  = (165, 210, 155)
        else:
            freq_reason = "普通频率 ×1.0"
            freq_color  = (150, 175, 140)
        _draw_kv(screen, self.font_sm, "频率等级", freq_reason, x, panel_x + DETAIL_W - 12, y, freq_color)
        y += 17

        # Climate row
        cm = climate.xp_multiplier
        cli_reason = f"{climate.state_label} ×{cm:.1f}"
        cli_color  = (150, 180, 255) if cm > 1.0 else ((230, 155, 90) if cm < 1.0 else (150, 175, 140))
        _draw_kv(screen, self.font_sm, "气候效果", cli_reason, x, panel_x + DETAIL_W - 12, y, cli_color)
        y += 17

        # Event row
        active = ev.active_event
        if active:
            ev_name = EVENT_META[active]['name']
            if em != 1.0:
                ev_reason = f"{ev_name} ×{em:.2f}"
                ev_color  = (230, 210, 100) if em > 1.0 else (235, 140, 80)
            else:
                ev_reason = f"{ev_name} (未影响此键)"
                ev_color  = (130, 155, 130)
            _draw_kv(screen, self.font_sm, "当前事件", ev_reason, x, panel_x + DETAIL_W - 12, y, ev_color)
            y += 17

        # Total multiplier
        total_mult = tree.xp_multiplier * cm * em
        _draw_divider(screen, x, panel_x + DETAIL_W - 12, y)
        y += 5
        total_color = (120, 235, 120) if total_mult > 1.0 else ((235, 125, 80) if total_mult < 1.0 else (180, 200, 170))
        _draw_kv(screen, self.font_sm, "综合倍率", f"×{total_mult:.2f}", x,
                 panel_x + DETAIL_W - 12, y, total_color)
        y += 20

        # ── Basic stats ──────────────────────────────────────────────────
        _draw_divider(screen, x, panel_x + DETAIL_W - 12, y)
        y += 5
        for lbl, val in [
            ("今日按键", str(tree.today_presses)),
            ("历史总计", str(tree.total_presses)),
            ("已长成",   f"{tree.trees_grown} 棵大树"),
            ("外观",     SKIN_ID_TO_NAME.get(tree.skin_id, tree.skin_id or '默认绿')),
        ]:
            _draw_kv(screen, self.font_sm, lbl, val, x, panel_x + DETAIL_W - 12, y, (200, 230, 190))
            y += 17

        # ── Skin switcher ────────────────────────────────────────────────
        _draw_divider(screen, x, panel_x + DETAIL_W - 12, y)
        y += 5
        _draw_text(screen, self.font_sm, "外观切换", x, y, (160, 200, 150))
        y += 17

        owned_ids = self.shop.get_owned_skin_ids() if self.shop else ['']
        all_skins = [('', '默认')] + [(it.skin_id, it.name) for it in SKIN_ITEMS]
        sw_w, sw_h = 58, 32    # swatch size
        sw_gap = 4
        per_row = 4
        for idx, (sid, sname) in enumerate(all_skins):
            col = idx % per_row
            row = idx // per_row
            sx = x + col * (sw_w + sw_gap)
            sy = y + row * (sw_h + 14)
            srect = pygame.Rect(sx, sy, sw_w, sw_h)
            owned = sid in owned_ids
            active = (sid == tree.skin_id)
            base_c = SKIN_SWATCH.get(sid, (60, 180, 50))
            fill_c = base_c if owned else tuple(max(0, c - 100) for c in base_c)
            pygame.draw.rect(screen, fill_c, srect, border_radius=3)
            border_c = (255, 230, 80) if active else ((130, 180, 120) if owned else (55, 65, 50))
            bw = 2 if active else 1
            pygame.draw.rect(screen, border_c, srect, bw, border_radius=3)
            if not owned:
                ls = self.font_sm.render("🔒", True, (120, 110, 100))
                screen.blit(ls, (sx + (sw_w - ls.get_width()) // 2,
                                  sy + (sw_h - ls.get_height()) // 2))
            lbl_c = (220, 240, 200) if owned else (100, 100, 95)
            ls2 = self.font_sm.render(sname[:4], True, lbl_c)
            screen.blit(ls2, (sx + (sw_w - ls2.get_width()) // 2, sy + sw_h + 1))
            if owned:
                self._skin_chip_rects.append((sid, srect))

        rows_needed = (len(all_skins) + per_row - 1) // per_row
        y += rows_needed * (sw_h + 14) + 6

        # One-click apply-all button
        all_btn = pygame.Rect(x, y, w, 22)
        self._apply_all_rect = all_btn
        skin_name = SKIN_ID_TO_NAME.get(tree.skin_id, tree.skin_id or '默认绿')
        pygame.draw.rect(screen, (42, 52, 105), all_btn, border_radius=3)
        pygame.draw.rect(screen, (90, 110, 195), all_btn, 1, border_radius=3)
        _draw_text(screen, self.font_sm, f"一键换装·全部按键（{skin_name}）",
                   x + w // 2, y + 2, (200, 215, 255), center=True)
        y += 28
        pest_info = ev.get_pest_info(self._target_key)
        if pest_info:
            y += 4
            pygame.draw.line(screen, (200, 118, 42), (x, y), (panel_x + DETAIL_W - 12, y))
            y += 5
            _draw_text(screen, self.font_sm, "🐛 虫害侵袭中", x, y, (230, 145, 60))
            y += 17

            _draw_label(screen, self.font_sm, "驱虫进度", x, y, w)
            y += 16
            hits_done = pest_info['hits_total'] - pest_info['hits_remaining']
            _draw_bar(screen, x, y, w, 12, hits_done / pest_info['hits_total'],
                      (220, 145, 50),
                      f"还需{pest_info['hits_remaining']}次 ({hits_done}/{pest_info['hits_total']})",
                      self.font_sm)
            y += 20

            rem   = int(pest_info['time_remaining'])
            drain = int(pest_info['next_drain_in'])
            _draw_kv(screen, self.font_sm, "事件剩余",  f"{rem//60}:{rem%60:02d}",
                     x, panel_x + DETAIL_W - 12, y, (200, 165, 100))
            y += 17
            _draw_kv(screen, self.font_sm, "下次扣经验", f"{drain}秒后 (-5)",
                     x, panel_x + DETAIL_W - 12, y, (180, 140, 80))

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _commit_name(self):
        if self._target_key:
            tree = self.forest.trees.get(self._target_key)
            if tree:
                tree.custom_name = self._name_input.strip()
                self.forest.db.update_custom_name(self._target_key, tree.custom_name)

    def _apply_skin_to_current(self, skin_id: str):
        if self._target_key is None:
            return
        if self.shop:
            self.shop.apply_skin_by_palette_id(skin_id, self._target_key, self.forest)
        else:
            tree = self.forest.trees.get(self._target_key)
            if tree:
                tree.skin_id = skin_id
                from renderer.tree_sprites import clear_cache
                clear_cache()

    def _apply_skin_to_all(self):
        tree = self.forest.trees.get(self._target_key) if self._target_key else None
        if tree is None:
            return
        skin_id = tree.skin_id
        if self.shop:
            self.shop.apply_skin_all_trees(skin_id, self.forest)
        else:
            from renderer.tree_sprites import clear_cache
            for t in self.forest.trees.values():
                if t.stage > 0:
                    t.skin_id = skin_id
            clear_cache()


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _draw_text(surf, font, text, x, y, color, center=False, right=False):
    s = font.render(text, True, color)
    if center:
        x -= s.get_width() // 2
    elif right:
        x -= s.get_width()
    surf.blit(s, (x, y))


def _draw_label(surf, font, text, x, y, w):
    s = font.render(text, True, (150, 180, 150))
    surf.blit(s, (x, y))


def _draw_kv(surf, font, key, value, lx, rx, y, val_color):
    """Draw a key=left, value=right aligned pair."""
    ks = font.render(key,   True, C_STATUS_TEXT)
    vs = font.render(value, True, val_color)
    surf.blit(ks, (lx, y))
    surf.blit(vs, (rx - vs.get_width(), y))


def _draw_divider(surf, x1, x2, y):
    pygame.draw.line(surf, (60, 85, 55), (x1, y), (x2, y))


def _draw_bar(surf, x, y, w, h, frac, fill_color, label, font):
    pygame.draw.rect(surf, C_BAR_BG, (x, y, w, h), border_radius=3)
    if frac > 0:
        fw = max(4, int(w * frac))
        pygame.draw.rect(surf, fill_color, (x, y, fw, h), border_radius=3)
    pygame.draw.rect(surf, (60, 80, 55), (x, y, w, h), 1, border_radius=3)
    ls = font.render(label, True, (210, 230, 200))
    surf.blit(ls, (x + w // 2 - ls.get_width() // 2, y))
