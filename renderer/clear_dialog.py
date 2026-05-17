"""
ClearDataDialog: two-step confirmation overlay before wiping all data.
Usage:
    dialog = ClearDataDialog(font_med, font_sm)
    dialog.open()              # trigger from a button

    # In event loop:
    action = dialog.handle_event(event)
    if action == 'clear':   db.clear_all_data(); forest.reload_after_clear()
    if action == 'cancel':  pass  # already closed

    # In render loop (draw last, on top of everything):
    dialog.draw(screen)
"""

from __future__ import annotations
import pygame
from typing import Optional

from config import WINDOW_W, WINDOW_H

_OVERLAY_ALPHA = 160
_DLG_W = 480
_DLG_H = 230

# Colours
_C_BG      = (22, 28, 18)
_C_BORDER1 = (160, 120, 40)   # step-1 amber
_C_BORDER2 = (200, 60,  40)   # step-2 red
_C_TITLE   = (230, 210, 160)
_C_TITLE2  = (240, 110,  90)
_C_TEXT    = (180, 200, 165)
_C_BTN_OK  = (55,  130,  45)
_C_BTN_OK2 = (160,  40,  30)
_C_BTN_CA  = (50,   55,  42)
_C_BTN_TXT = (220, 245, 210)
_C_BTN_CA_TXT = (160, 180, 150)
_C_WARN    = (220, 140, 50)
_C_WARN2   = (240,  80, 60)


class ClearDataDialog:
    def __init__(self, font_med: pygame.font.Font, font_sm: pygame.font.Font):
        self.font_med = font_med
        self.font_sm  = font_sm
        self._step    = 0    # 0=hidden, 1=first confirm, 2=second confirm
        self._ok_rect:  Optional[pygame.Rect] = None
        self._can_rect: Optional[pygame.Rect] = None

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        return self._step > 0

    def open(self):
        self._step = 1

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        Returns:
            'clear'  – user confirmed twice, proceed with deletion
            'cancel' – user cancelled at any step
            None     – event consumed but no final action yet
        """
        if not self.active:
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None   # swallow no non-click events here

        pos = event.pos

        # Dismiss on click outside the dialog
        dlg_rect = self._dialog_rect()
        if not dlg_rect.collidepoint(pos):
            self._step = 0
            return 'cancel'

        if self._ok_rect and self._ok_rect.collidepoint(pos):
            if self._step == 1:
                self._step = 2
                return None        # advance to step 2
            else:
                self._step = 0
                return 'clear'    # both confirmations done

        if self._can_rect and self._can_rect.collidepoint(pos):
            self._step = 0
            return 'cancel'

        return None   # click inside dialog but not on a button

    def draw(self, screen: pygame.Surface):
        if not self.active:
            return

        # Dim the whole screen
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, _OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        dlg = self._dialog_rect()
        border_color = _C_BORDER1 if self._step == 1 else _C_BORDER2
        pygame.draw.rect(screen, _C_BG, dlg, border_radius=10)
        pygame.draw.rect(screen, border_color, dlg, 2, border_radius=10)

        x = dlg.x + 20
        y = dlg.y + 18

        if self._step == 1:
            self._draw_step1(screen, x, y, dlg)
        else:
            self._draw_step2(screen, x, y, dlg)

    # ── Step rendering ─────────────────────────────────────────────────────

    def _draw_step1(self, screen, x, y, dlg):
        _txt(screen, self.font_med, "⚠  清除所有数据", x, y, _C_TITLE)
        y += 28
        _txt(screen, self.font_sm, "此操作将永久删除：", x, y, _C_TEXT)
        y += 18
        for line in ("• 所有按键树的成长数据和经验", "• 所有按键记录和统计", "• 所有成就和进度"):
            _txt(screen, self.font_sm, line, x + 10, y, _C_WARN)
            y += 16
        y += 8
        _txt(screen, self.font_sm, "数据清除后无法恢复，确定继续？", x, y, _C_TEXT)

        btn_y = dlg.bottom - 46
        ok_rect  = pygame.Rect(dlg.x + 20,             btn_y, 170, 32)
        can_rect = pygame.Rect(dlg.right - 190,        btn_y, 170, 32)
        self._ok_rect  = ok_rect
        self._can_rect = can_rect

        pygame.draw.rect(screen, _C_BTN_OK,  ok_rect,  border_radius=5)
        pygame.draw.rect(screen, _C_BTN_CA,  can_rect, border_radius=5)
        _txt(screen, self.font_sm, "确认，继续",
             ok_rect.centerx,  ok_rect.centery,  _C_BTN_TXT,   center=True)
        _txt(screen, self.font_sm, "取消",
             can_rect.centerx, can_rect.centery, _C_BTN_CA_TXT, center=True)

    def _draw_step2(self, screen, x, y, dlg):
        _txt(screen, self.font_med, "⛔  最后确认", x, y, _C_TITLE2)
        y += 28
        _txt(screen, self.font_sm, "你即将清除全部数据，这是第二次确认。", x, y, _C_TEXT)
        y += 20
        _txt(screen, self.font_sm, "所有树木将枯萎，所有记录将消失。", x, y, _C_WARN2)
        y += 20
        _txt(screen, self.font_sm, "⚠  此操作不可逆，请谨慎！", x, y, _C_WARN2)
        y += 20
        _txt(screen, self.font_sm, "点击「取消」回到游戏。", x, y, _C_TEXT)

        btn_y = dlg.bottom - 46
        ok_rect  = pygame.Rect(dlg.x + 20,      btn_y, 210, 32)
        can_rect = pygame.Rect(dlg.right - 190,  btn_y, 170, 32)
        self._ok_rect  = ok_rect
        self._can_rect = can_rect

        pygame.draw.rect(screen, _C_BTN_OK2, ok_rect,  border_radius=5)
        pygame.draw.rect(screen, _C_BTN_CA,  can_rect, border_radius=5)
        _txt(screen, self.font_sm, "我确定，清除全部数据",
             ok_rect.centerx,  ok_rect.centery,  _C_BTN_TXT,    center=True)
        _txt(screen, self.font_sm, "取消，回到游戏",
             can_rect.centerx, can_rect.centery, _C_BTN_CA_TXT, center=True)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _dialog_rect(self) -> pygame.Rect:
        return pygame.Rect(
            (WINDOW_W - _DLG_W) // 2,
            (WINDOW_H - _DLG_H) // 2,
            _DLG_W, _DLG_H
        )


def _txt(surf, font, text, x, y, color, center=False, right=False):
    s = font.render(text, True, color)
    if center:
        x -= s.get_width() // 2
        y -= s.get_height() // 2
    elif right:
        x -= s.get_width()
    surf.blit(s, (x, y))
