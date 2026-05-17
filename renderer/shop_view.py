"""
ShopView: gold coin collection, skin shop, consumable shop.
"""

from __future__ import annotations
import os
import pygame
from typing import Optional, List, Tuple

from config import (
    WINDOW_W, WINDOW_H, HUD_H, STATUS_H, KEY_LABELS,
    C_STATS_BG, C_STATS_BORDER, C_STATS_TITLE, C_STATS_TEXT, C_STATS_DIM,
)
from forest import Forest
from renderer.tree_sprites import get_tree_surface, TREE_W, TREE_H
from shop import (ShopSystem, SKIN_ITEMS, CONSUMABLE_ITEMS, ITEM_MAP, SKIN_SWATCH,
                  BG_ITEMS, BG_THEMES, BG_SWATCH)

_CONTENT_Y = HUD_H + 4
_CONTENT_H = WINDOW_H - HUD_H - STATUS_H

# Left panel – skins / backgrounds (sub-tabbed)
_LEFT_X   = 8
_LEFT_W   = 565
_CARD_W   = 270
_CARD_H   = 128
_BG_CARD_H = 100
_CARD_GAP = 12
_CARD_COL = [_LEFT_X, _LEFT_X + _CARD_W + _CARD_GAP]  # 2 columns
_CARD_ROW0 = _CONTENT_Y + 40   # leaves room for sub-tabs at top

# Sub-tab buttons (inside left panel header)
_TAB_SKIN_RECT = pygame.Rect(_LEFT_X,      _CONTENT_Y + 4, 90, 26)
_TAB_BG_RECT   = pygame.Rect(_LEFT_X + 94, _CONTENT_Y + 4, 90, 26)

# Right panel – coins + consumables
_RIGHT_X  = _LEFT_X + _LEFT_W + 18
_RIGHT_W  = WINDOW_W - _RIGHT_X - 8

# Key picker strip
_PICKER_H = 105
_PICKER_Y = WINDOW_H - STATUS_H - _PICKER_H

# Mini tree preview in skin card
_SP_SCALE = 0.60
_SPW = int(TREE_W * _SP_SCALE)
_SPH = int(TREE_H * _SP_SCALE)

# Colours
_C_GOLD      = (255, 215, 80)
_C_BUY       = (55, 115, 45)
_C_BUY_ACT   = (90, 175, 70)
_C_USE       = (75, 45, 140)
_C_USE_ACT   = (120, 80, 200)
_C_OWN       = (35, 60, 35)
_C_APPLY     = (95, 55, 175)
_C_APPLY_ACT = (130, 85, 220)


class ShopView:
    def __init__(self, forest: Forest, shop: ShopSystem,
                 font_med: pygame.font.Font, font_sm: pygame.font.Font):
        self.forest   = forest
        self.shop     = shop
        self.font_med = font_med
        self.font_sm  = font_sm

        # Pending action state
        self._pending_skin_id: Optional[str]  = None

        # Recharge overlay
        self._show_recharge:       bool                   = False
        self._recharge_imgs:       Optional[tuple]        = None   # lazy (wx_surf, zfb_surf)
        self._recharge_close_rect: Optional[pygame.Rect]  = None
        self._recharge_btn_rect:   Optional[pygame.Rect]  = None
        self._pending_item_id: Optional[str]  = None

        # Sub-tab state: 'skin' | 'bg'
        self._left_tab: str = 'skin'

        # Status toast
        self._status_msg:   str   = ''
        self._status_timer: float = 0.0

        # Hit-test rects (rebuilt each draw)
        self._skin_btn_rects: List[Tuple[str, pygame.Rect, str]] = []  # (id, rect, 'buy'|'apply')
        self._bg_btn_rects:   List[Tuple[str, pygame.Rect, str]] = []  # (bg_id, rect, 'buy'|'apply')
        self._cons_buy_rects: List[Tuple[str, pygame.Rect]] = []
        self._cons_use_rects: List[Tuple[str, pygame.Rect]] = []
        self._collect_rect:   Optional[pygame.Rect] = None
        self._picker_chips:   List[Tuple[str, pygame.Rect]] = []
        self._cancel_rect:    Optional[pygame.Rect] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        if self._status_timer > 0:
            self._status_timer -= dt

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Recharge overlay absorbs all clicks
            if self._show_recharge:
                if self._recharge_close_rect and self._recharge_close_rect.collidepoint(event.pos):
                    self._show_recharge = False
                return True
            return self._on_click(event.pos)
        return False

    # ── Event handling ────────────────────────────────────────────────────────

    def _on_click(self, pos) -> bool:
        # Recharge button
        if self._recharge_btn_rect and self._recharge_btn_rect.collidepoint(pos):
            self._show_recharge = True
            return True

        # Sub-tab toggle
        if _TAB_SKIN_RECT.collidepoint(pos):
            self._left_tab = 'skin'
            return True
        if _TAB_BG_RECT.collidepoint(pos):
            self._left_tab = 'bg'
            return True

        # Cancel picker
        if self._cancel_rect and self._cancel_rect.collidepoint(pos):
            self._pending_skin_id = None
            self._pending_item_id = None
            return True

        # Key picker chips
        if self._pending_skin_id or self._pending_item_id:
            for key_name, rect in self._picker_chips:
                if rect.collidepoint(pos):
                    self._execute_pending(key_name)
                    return True
            return True   # absorb clicks while picker is open

        # Collect coins
        if self._collect_rect and self._collect_rect.collidepoint(pos):
            gained = self.shop.collect_daily_coins(self.forest.trees)
            if gained > 0:
                self._toast(f"领取成功！获得 {gained} 枚金币 🪙")
                self.forest._notify(f"🪙 收取 {gained} 枚金币！")
            else:
                self._toast("今日已领取，明日再来！")
            return True

        # Skin buttons
        for item_id, rect, action in self._skin_btn_rects:
            if rect.collidepoint(pos):
                if action == 'buy':
                    if self.shop.buy(item_id):
                        self._toast(f"购买成功！{ITEM_MAP[item_id].name} 已解锁 🎨")
                    else:
                        self._toast("金币不足！")
                else:  # apply
                    self._pending_skin_id = item_id
                    self._pending_item_id = None
                    self._toast("请在下方选择要换装的按键…")
                return True

        # Background buttons
        for bg_id, rect, action in self._bg_btn_rects:
            if rect.collidepoint(pos):
                if action == 'buy':
                    if self.shop.buy_bg(bg_id):
                        name = next(b.name for b in BG_ITEMS if b.bg_id == bg_id)
                        self._toast(f"购买成功！{name} 背景已解锁")
                        self.forest._notify(f"🏞 背景「{name}」已解锁！")
                    else:
                        self._toast("金币不足！")
                else:  # apply
                    self.shop.apply_bg(bg_id)
                    name = next(b.name for b in BG_ITEMS if b.bg_id == bg_id)
                    self._toast(f"已切换到「{name}」背景")
                return True

        # Consumable buy
        for item_id, rect in self._cons_buy_rects:
            if rect.collidepoint(pos):
                if self.shop.buy(item_id):
                    self._toast(f"购买成功！{ITEM_MAP[item_id].name} ×1")
                else:
                    self._toast("金币不足！")
                return True

        # Consumable use
        for item_id, rect in self._cons_use_rects:
            if rect.collidepoint(pos):
                item = ITEM_MAP[item_id]
                if item.target:
                    self._pending_item_id = item_id
                    self._pending_skin_id = None
                    self._toast("请在下方选择目标按键…")
                else:
                    result = self.shop.use_consumable(item_id, None, self.forest)
                    self._toast(result.removeprefix('ok:'))
                return True

        return False

    def _execute_pending(self, key_name: str):
        if self._pending_skin_id:
            result = self.shop.apply_skin(self._pending_skin_id, key_name, self.forest)
            self._toast(result.removeprefix('ok:'))
        elif self._pending_item_id:
            result = self.shop.use_consumable(self._pending_item_id, key_name, self.forest)
            self._toast(result.removeprefix('ok:'))
        self._pending_skin_id = None
        self._pending_item_id = None

    def _toast(self, msg: str):
        self._status_msg   = msg
        self._status_timer = 3.5

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        screen.fill(C_STATS_BG)

        # Clear hit-test lists
        self._skin_btn_rects.clear()
        self._bg_btn_rects.clear()
        self._cons_buy_rects.clear()
        self._cons_use_rects.clear()
        self._picker_chips.clear()
        self._cancel_rect  = None
        self._collect_rect = None

        self._draw_left(screen)
        self._draw_right(screen)

        if self._pending_skin_id or self._pending_item_id:
            self._draw_picker(screen)

        if self._show_recharge:
            self._draw_recharge(screen)

        if self._status_timer > 0 and self._status_msg:
            self._draw_toast(screen)

    # ── Left panel (skins / backgrounds) ─────────────────────────────────────

    def _draw_left(self, screen: pygame.Surface):
        # Sub-tab buttons
        for rect, label, tab_id in [
            (_TAB_SKIN_RECT, '🎨 皮肤', 'skin'),
            (_TAB_BG_RECT,   '🏞 背景', 'bg'),
        ]:
            active = (self._left_tab == tab_id)
            bg  = (55, 90, 45) if active else (28, 40, 22)
            bdr = (100, 160, 80) if active else (50, 68, 42)
            pygame.draw.rect(screen, bg,  rect, border_radius=5)
            pygame.draw.rect(screen, bdr, rect, 1, border_radius=5)
            lc = (220, 245, 200) if active else (140, 175, 125)
            ts = self.font_sm.render(label, True, lc)
            screen.blit(ts, (rect.x + (rect.w - ts.get_width()) // 2,
                              rect.y + (rect.h - ts.get_height()) // 2))

        pygame.draw.line(screen, C_STATS_BORDER,
                         (_LEFT_X, _CARD_ROW0 - 6), (_LEFT_X + _LEFT_W, _CARD_ROW0 - 6))

        if self._left_tab == 'skin':
            for idx, item in enumerate(SKIN_ITEMS):
                col = idx % 2
                row = idx // 2
                cx  = _CARD_COL[col]
                cy  = _CARD_ROW0 + row * (_CARD_H + _CARD_GAP)
                self._draw_skin_card(screen, item, pygame.Rect(cx, cy, _CARD_W, _CARD_H))
        else:
            self._draw_bg_cards(screen)

    def _draw_skin_card(self, screen: pygame.Surface, item, rect: pygame.Rect):
        owned      = self.shop.owns_skin(item.id)
        is_pending = (self._pending_skin_id == item.id)

        bg     = (45, 65, 38) if owned else (28, 38, 22)
        border = (200, 200, 80) if is_pending else ((88, 150, 68) if owned else (50, 68, 42))
        bw     = 2 if is_pending else 1
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, bw, border_radius=6)

        # Swatch + mini tree (left ~64px)
        sw_rect = pygame.Rect(rect.x + 6, rect.y + 6, 60, rect.h - 12)
        swatch  = SKIN_SWATCH.get(item.skin_id, (60, 180, 50))
        pygame.draw.rect(screen, _dim(swatch, 0.55), sw_rect, border_radius=4)
        pygame.draw.rect(screen, border, sw_rect, 1, border_radius=4)

        ts = get_tree_surface(4, 1.0, False, skin_id=item.skin_id)
        ts_s = pygame.transform.scale(ts, (_SPW, _SPH))
        screen.blit(ts_s, (sw_rect.x + (sw_rect.w - _SPW) // 2,
                            sw_rect.y + (sw_rect.h - _SPH) // 2))

        # Text area
        tx = rect.x + 72
        ty = rect.y + 8
        name_c = (220, 245, 200) if owned else (155, 195, 140)
        _t(screen, self.font_med, item.name,        tx, ty,      name_c)
        _t(screen, self.font_sm,  item.description, tx, ty + 20, C_STATS_DIM)
        _t(screen, self.font_sm,  f"🪙 {item.price}", tx, ty + 38, _C_GOLD)

        # Button(s) at bottom-right of card
        btn_y  = rect.bottom - 30
        btn_x  = tx
        btn_w  = rect.right - tx - 6

        if not owned:
            can   = self.shop.can_afford(item.id)
            b_bg  = _C_BUY_ACT if can else (38, 50, 32)
            b_bdr = (110, 185, 80) if can else (55, 70, 48)
            br    = pygame.Rect(btn_x, btn_y, btn_w, 24)
            pygame.draw.rect(screen, b_bg, br, border_radius=4)
            pygame.draw.rect(screen, b_bdr, br, 1, border_radius=4)
            lbl = "购买" if can else f"需 {item.price}🪙"
            _t(screen, self.font_sm, lbl, br.centerx, br.centery,
               (215, 245, 200) if can else (100, 120, 88), center=True)
            if can:
                self._skin_btn_rects.append((item.id, br, 'buy'))
        else:
            # [✓已拥有] side-by-side with [应用 ▸]
            half = (btn_w - 6) // 2
            ow_r = pygame.Rect(btn_x,         btn_y, half, 24)
            ap_r = pygame.Rect(btn_x + half + 6, btn_y, btn_w - half - 6, 24)

            pygame.draw.rect(screen, _C_OWN, ow_r, border_radius=4)
            pygame.draw.rect(screen, (65, 110, 65), ow_r, 1, border_radius=4)
            _t(screen, self.font_sm, "✓已拥有", ow_r.centerx, ow_r.centery,
               (120, 200, 120), center=True)

            a_bg  = _C_APPLY_ACT if is_pending else _C_APPLY
            a_bdr = (170, 125, 245)
            pygame.draw.rect(screen, a_bg, ap_r, border_radius=4)
            pygame.draw.rect(screen, a_bdr, ap_r, 1, border_radius=4)
            _t(screen, self.font_sm, "应用 ▸", ap_r.centerx, ap_r.centery,
               (235, 215, 255), center=True)
            self._skin_btn_rects.append((item.id, ap_r, 'apply'))

    # ── Background cards ──────────────────────────────────────────────────────

    def _draw_bg_cards(self, screen: pygame.Surface):
        for idx, item in enumerate(BG_ITEMS):
            col = idx % 2
            row = idx // 2
            cx  = _CARD_COL[col]
            cy  = _CARD_ROW0 + row * (_BG_CARD_H + _CARD_GAP)
            self._draw_bg_card(screen, item, pygame.Rect(cx, cy, _CARD_W, _BG_CARD_H))

    def _draw_bg_card(self, screen: pygame.Surface, item: 'BgItem', rect: pygame.Rect):
        owned   = item.bg_id in self.shop.owned_bgs
        active  = (item.bg_id == self.shop.active_bg_id)
        theme   = BG_THEMES[item.bg_id]

        bg     = (45, 65, 38) if owned else (28, 38, 22)
        border = (220, 200, 80) if active else ((88, 150, 68) if owned else (50, 68, 42))
        bw     = 2 if active else 1
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, bw, border_radius=6)

        # Mini keyboard preview (left ~70px)
        prev_rect = pygame.Rect(rect.x + 6, rect.y + 6, 62, rect.h - 12)
        self._draw_bg_preview(screen, theme, prev_rect)
        if active:
            _t(screen, self.font_sm, "✓", prev_rect.x + 2, prev_rect.y + 2, (255, 230, 60))

        # Text area
        tx = rect.x + 74
        ty = rect.y + 8
        name_c = (220, 245, 200) if owned else (155, 195, 140)
        _t(screen, self.font_med, item.name,  tx, ty,      name_c)
        _t(screen, self.font_sm,  item.desc,  tx, ty + 20, C_STATS_DIM)
        if item.price == 0:
            _t(screen, self.font_sm, "免费", tx, ty + 38, (150, 220, 140))
        else:
            _t(screen, self.font_sm, f"🪙 {item.price}", tx, ty + 38, _C_GOLD)

        # Buttons
        btn_y  = rect.bottom - 28
        btn_x  = tx
        btn_w  = rect.right - tx - 6

        if not owned:
            can   = item.price == 0 or self.shop.coins >= item.price
            b_bg  = _C_BUY_ACT if can else (38, 50, 32)
            b_bdr = (110, 185, 80) if can else (55, 70, 48)
            br    = pygame.Rect(btn_x, btn_y, btn_w, 22)
            pygame.draw.rect(screen, b_bg, br, border_radius=4)
            pygame.draw.rect(screen, b_bdr, br, 1, border_radius=4)
            lbl = "获取" if item.price == 0 else ("购买" if can else f"需 {item.price}🪙")
            _t(screen, self.font_sm, lbl, br.centerx, br.centery,
               (215, 245, 200) if can else (100, 120, 88), center=True)
            if can:
                self._bg_btn_rects.append((item.bg_id, br, 'buy'))
        else:
            half  = (btn_w - 6) // 2
            ow_r  = pygame.Rect(btn_x,              btn_y, half, 22)
            ap_r  = pygame.Rect(btn_x + half + 6,   btn_y, btn_w - half - 6, 22)

            pygame.draw.rect(screen, _C_OWN, ow_r, border_radius=4)
            pygame.draw.rect(screen, (65, 110, 65), ow_r, 1, border_radius=4)
            _t(screen, self.font_sm, "✓已拥有", ow_r.centerx, ow_r.centery,
               (120, 200, 120), center=True)

            a_active = active
            a_bg  = (55, 45, 130) if a_active else _C_APPLY
            a_bdr = (145, 125, 235) if a_active else (130, 85, 220)
            pygame.draw.rect(screen, a_bg, ap_r, border_radius=4)
            pygame.draw.rect(screen, a_bdr, ap_r, 1, border_radius=4)
            lbl_a = "✓使用中" if a_active else "应用 ▸"
            _t(screen, self.font_sm, lbl_a, ap_r.centerx, ap_r.centery,
               (200, 190, 255), center=True)
            if not a_active:
                self._bg_btn_rects.append((item.bg_id, ap_r, 'apply'))

    def _draw_bg_preview(self, screen, theme: dict, rect: pygame.Rect):
        """Tiny keyboard layout preview using the theme's colors."""
        pygame.draw.rect(screen, theme['sky_top'], rect, border_radius=3)
        kw, kh, kg = 12, 8, 2
        for row in range(3):
            cols = 4 if row < 2 else 3
            off_x = (rect.w - cols * (kw + kg) + kg) // 2
            for col in range(cols):
                kx = rect.x + off_x + col * (kw + kg)
                ky = rect.y + 6 + row * (kh + kg + 2)
                pygame.draw.rect(screen, theme['cell_bg'],     (kx, ky, kw, kh), border_radius=1)
                pygame.draw.rect(screen, theme['cell_border'], (kx, ky, kw, kh), 1, border_radius=1)

    # ── Right panel (coins + consumables) ────────────────────────────────────

    def _draw_right(self, screen: pygame.Surface):
        x = _RIGHT_X
        w = _RIGHT_W
        y = _CONTENT_Y + 4

        # ── Coin section ──
        _t(screen, self.font_sm, "🪙  每日金币收取", x, y, C_STATS_TITLE)
        pygame.draw.line(screen, C_STATS_BORDER, (x, y + 18), (x + w, y + 18))
        y += 24

        _t(screen, self.font_med, f"当前金币：{self.shop.coins}", x, y, _C_GOLD)
        rch_r = pygame.Rect(x + w - 72, y, 72, 20)
        pygame.draw.rect(screen, (55, 35, 95), rch_r, border_radius=4)
        pygame.draw.rect(screen, (120, 80, 200), rch_r, 1, border_radius=4)
        _t(screen, self.font_sm, "充值 💳", rch_r.centerx, rch_r.centery,
           (210, 185, 255), center=True)
        self._recharge_btn_rect = rch_r
        y += 22

        can_col    = self.shop.can_collect_today()
        alive_grad = sum(
            1 for t in self.forest.trees.values()
            if t.trees_grown > 0 and t.stage > 0 and t.health > 0
        )
        if alive_grad == 0:
            btn_lbl = "暂无已毕业大树可领取"
            btn_ok  = False
        elif can_col:
            btn_lbl = f"领取今日金币  (+{alive_grad} 🪙)"
            btn_ok  = True
        else:
            btn_lbl = "今日已领取  ✓  明日再来"
            btn_ok  = False

        col_rect = pygame.Rect(x, y, w, 30)
        c_bg  = (60, 130, 50) if btn_ok else (32, 44, 28)
        c_bdr = (95, 185, 72) if btn_ok else (52, 70, 44)
        pygame.draw.rect(screen, c_bg, col_rect, border_radius=5)
        pygame.draw.rect(screen, c_bdr, col_rect, 1, border_radius=5)
        _t(screen, self.font_sm, btn_lbl, col_rect.centerx, col_rect.centery,
           (215, 245, 195) if btn_ok else (100, 128, 90), center=True)
        if btn_ok:
            self._collect_rect = col_rect

        y += 42
        pygame.draw.line(screen, C_STATS_BORDER, (x, y), (x + w, y))
        y += 8

        _t(screen, self.font_sm, "消耗品", x, y, C_STATS_TITLE)
        y += 20

        for item in CONSUMABLE_ITEMS:
            self._draw_cons_row(screen, item, x, y, w)
            y += 68

    def _draw_cons_row(self, screen: pygame.Surface, item, x, y, w):
        qty     = self.shop.get_inventory(item.id)
        row_bg  = (30, 42, 24)
        row_bdr = C_STATS_BORDER
        rr = pygame.Rect(x, y, w, 62)
        pygame.draw.rect(screen, row_bg, rr, border_radius=5)
        pygame.draw.rect(screen, row_bdr, rr, 1, border_radius=5)

        _t(screen, self.font_sm, item.name,        x + 8, y + 8,  (200, 232, 185))
        _t(screen, self.font_sm, item.description, x + 8, y + 26, C_STATS_DIM)
        _t(screen, self.font_sm, f"🪙 {item.price}", x + 8, y + 44, _C_GOLD)

        qty_c = (120, 228, 120) if qty > 0 else (140, 100, 100)
        _t(screen, self.font_sm, f"库存: {qty}/99", x + w - 256, y + 44, qty_c)

        # Buy button (disabled + labelled when at cap)
        buy_r = pygame.Rect(x + w - 166, y + 14, 68, 26)
        at_cap = qty >= 99
        can   = self.shop.can_afford(item.id) and not at_cap
        b_bg  = _C_BUY_ACT if can else (38, 50, 30)
        b_bdr = (105, 180, 75) if can else (58, 72, 48)
        pygame.draw.rect(screen, b_bg, buy_r, border_radius=4)
        pygame.draw.rect(screen, b_bdr, buy_r, 1, border_radius=4)
        buy_lbl = "已满 99" if at_cap else ("购买" if can else "购买")
        _t(screen, self.font_sm, buy_lbl, buy_r.centerx, buy_r.centery,
           (215, 245, 200) if can else (98, 118, 88), center=True)
        if can:
            self._cons_buy_rects.append((item.id, buy_r))

        # Use button
        use_r = pygame.Rect(x + w - 90, y + 14, 80, 26)
        can_u = qty > 0
        u_bg  = _C_USE_ACT if can_u else (36, 32, 52)
        u_bdr = (145, 100, 210) if can_u else (65, 58, 86)
        pygame.draw.rect(screen, u_bg, use_r, border_radius=4)
        pygame.draw.rect(screen, u_bdr, use_r, 1, border_radius=4)
        lbl_u = ("选键使用" if item.target else "使用") if can_u else "无库存"
        _t(screen, self.font_sm, lbl_u, use_r.centerx, use_r.centery,
           (225, 205, 255) if can_u else (88, 78, 108), center=True)
        if can_u:
            self._cons_use_rects.append((item.id, use_r))

    # ── Key picker ────────────────────────────────────────────────────────────

    def _draw_picker(self, screen: pygame.Surface):
        # Semi-transparent overlay strip
        ov = pygame.Surface((WINDOW_W, _PICKER_H), pygame.SRCALPHA)
        ov.fill((18, 26, 14, 230))
        screen.blit(ov, (0, _PICKER_Y))
        pygame.draw.line(screen, (75, 130, 65), (0, _PICKER_Y), (WINDOW_W, _PICKER_Y), 2)

        # Title
        if self._pending_skin_id:
            name = ITEM_MAP[self._pending_skin_id].name
            title = f"选择要换装 [{name}] 的按键树："
        else:
            name = ITEM_MAP[self._pending_item_id].name
            title = f"选择 [{name}] 的目标按键树："
        _t(screen, self.font_sm, title, 10, _PICKER_Y + 5, (200, 230, 185))

        # Cancel button
        can_r = pygame.Rect(WINDOW_W - 68, _PICKER_Y + 3, 60, 22)
        pygame.draw.rect(screen, (80, 48, 48), can_r, border_radius=4)
        _t(screen, self.font_sm, "取消", can_r.centerx, can_r.centery,
           (230, 148, 148), center=True)
        self._cancel_rect = can_r

        # Candidate keys
        if self._pending_skin_id:
            cands = [(k, t) for k, t in self.forest.trees.items() if t.stage > 0]
        else:
            if self._pending_item_id == 'potion':
                cands = [(k, t) for k, t in self.forest.trees.items()
                         if t.stage > 0 and t.health < 1.0]
            else:
                cands = [(k, t) for k, t in self.forest.trees.items() if t.stage > 0]

        chip_x = 10
        chip_y = _PICKER_Y + 26
        chip_h = 22

        for key_name, tree in sorted(cands, key=lambda kv: kv[0]):
            label   = KEY_LABELS.get(key_name, key_name[:5].upper())
            chip_w  = max(30, self.font_sm.size(label)[0] + 10)
            if chip_x + chip_w > WINDOW_W - 78:
                chip_x  = 10
                chip_y += chip_h + 4
                if chip_y + chip_h > _PICKER_Y + _PICKER_H - 4:
                    break
            cr = pygame.Rect(chip_x, chip_y, chip_w, chip_h)
            hp = tree.health
            c_bg  = (38, 88, 38) if hp > 0.5 else ((88, 58, 28) if hp > 0 else (80, 38, 38))
            c_bdr = (75, 140, 65)
            pygame.draw.rect(screen, c_bg, cr, border_radius=3)
            pygame.draw.rect(screen, c_bdr, cr, 1, border_radius=3)
            _t(screen, self.font_sm, label, cr.centerx, cr.centery, (210, 242, 195), center=True)
            self._picker_chips.append((key_name, cr))
            chip_x += chip_w + 4

    # ── Recharge overlay ─────────────────────────────────────────────────────

    def _load_recharge_imgs(self):
        if self._recharge_imgs is not None:
            return
        try:
            _assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
            wx  = pygame.image.load(os.path.join(_assets, 'wx.jpg')).convert()
            zfb = pygame.image.load(os.path.join(_assets, 'zhifubao.jpg')).convert()
            sz = (270, 270)
            self._recharge_imgs = (pygame.transform.scale(wx, sz),
                                   pygame.transform.scale(zfb, sz))
        except Exception:
            self._recharge_imgs = ()   # failed – show placeholder text

    def _draw_recharge(self, screen: pygame.Surface):
        self._load_recharge_imgs()

        # Full-screen dark overlay
        ov = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        screen.blit(ov, (0, 0))

        # Panel
        pw, ph = 680, 480
        px = (WINDOW_W - pw) // 2
        py = (WINDOW_H - ph) // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((18, 24, 44, 248))
        pygame.draw.rect(panel, (88, 105, 200), (0, 0, pw, ph), 2, border_radius=12)
        screen.blit(panel, (px, py))

        # Close button
        close_r = pygame.Rect(px + pw - 36, py + 8, 28, 28)
        pygame.draw.rect(screen, (80, 48, 48), close_r, border_radius=4)
        pygame.draw.rect(screen, (165, 88, 88), close_r, 1, border_radius=4)
        _t(screen, self.font_sm, "✕", close_r.centerx, close_r.centery,
           (230, 140, 140), center=True)
        self._recharge_close_rect = close_r

        # Title
        _t(screen, self.font_med, "充值金币", px + pw // 2, py + 22,
           (215, 215, 255), center=True)

        # Rate description
        _t(screen, self.font_sm,
           "🪙  1元人民币 = 1枚金币 · 支付后24小时内到账",
           px + pw // 2, py + 56, (175, 200, 255), center=True)

        # QR images
        img_top = py + 90
        if self._recharge_imgs and len(self._recharge_imgs) == 2:
            wx_s, zfb_s = self._recharge_imgs
            gap   = 30
            total = wx_s.get_width() + zfb_s.get_width() + gap
            wx_x  = px + (pw - total) // 2
            zfb_x = wx_x + wx_s.get_width() + gap

            # thin border around each QR
            pygame.draw.rect(screen, (70, 85, 160),
                             (wx_x - 2, img_top - 2,
                              wx_s.get_width() + 4, wx_s.get_height() + 4), 1)
            pygame.draw.rect(screen, (70, 85, 160),
                             (zfb_x - 2, img_top - 2,
                              zfb_s.get_width() + 4, zfb_s.get_height() + 4), 1)

            screen.blit(wx_s,  (wx_x,  img_top))
            screen.blit(zfb_s, (zfb_x, img_top))

            lbl_y = img_top + wx_s.get_height() + 10
            _t(screen, self.font_sm, "微信支付",
               wx_x + wx_s.get_width() // 2, lbl_y, (100, 220, 120), center=True)
            _t(screen, self.font_sm, "支付宝",
               zfb_x + zfb_s.get_width() // 2, lbl_y, (80, 155, 255), center=True)
        else:
            _t(screen, self.font_sm, "（二维码图片加载失败）",
               px + pw // 2, img_top + 100, (155, 140, 140), center=True)

    # ── Status toast ──────────────────────────────────────────────────────────

    def _draw_toast(self, screen: pygame.Surface):
        alpha = int(255 * min(1.0, self._status_timer / 0.4))
        w = self.font_sm.size(self._status_msg)[0] + 24
        h = 26
        sx = (WINDOW_W - w) // 2
        sy = HUD_H + 8
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((28, 52, 22, alpha))
        pygame.draw.rect(surf, (78, 148, 68, alpha), (0, 0, w, h), 1, border_radius=4)
        ts = self.font_sm.render(self._status_msg, True, (210, 248, 195))
        ts.set_alpha(alpha)
        surf.blit(ts, (12, 4))
        screen.blit(surf, (sx, sy))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _t(surf, font, text, x, y, color, center=False, right=False):
    s = font.render(text, True, color)
    if center:
        x -= s.get_width() // 2
        y -= s.get_height() // 2
    elif right:
        x -= s.get_width()
    surf.blit(s, (x, y))


def _dim(color, factor: float) -> tuple:
    return tuple(int(c * factor) for c in color)
