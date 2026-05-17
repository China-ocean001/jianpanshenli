"""
Procedural pixel-art tree renderer.
All trees are drawn with pygame.draw – no image assets needed.

Visual states:
  stage 0: bare dirt patch
  stage 1: seed (tiny sprout)
  stage 2: small sapling
  stage 3: young tree
  stage 4: mature tree
  stage 5: giant tree (multi-canopy)

Health modifiers:
  healthy : green leaves
  sick    : yellow-brown leaves
  dead    : bare grey trunk only

Each tree is cached as a Surface of size (TREE_W, TREE_H).
"""

from __future__ import annotations
import math
import pygame
from typing import Dict, Tuple

from config import (
    C_TRUNK_HEALTHY, C_TRUNK_SICK, C_TRUNK_DEAD,
    C_LEAF_HEALTHY, C_LEAF_HEALTHY2, C_LEAF_SICK, C_LEAF_SICK2, C_LEAF_DEAD,
    C_DIRT, C_SEED, C_FLOWER, C_BUTTERFLY,
)
from shop import SKIN_PALETTES

TREE_W = 50
TREE_H = 52

# ── 人民万岁 skin font (lazy-loaded after pygame.init) ────────────────────────
_RMWY_FONT = None

def _get_rmwy_font() -> pygame.font.Font:
    global _RMWY_FONT
    if _RMWY_FONT is None:
        for name in ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial Unicode MS']:
            try:
                _RMWY_FONT = pygame.font.SysFont(name, 32, bold=True)
                break
            except Exception:
                pass
        if _RMWY_FONT is None:
            _RMWY_FONT = pygame.font.Font(None, 34)
    return _RMWY_FONT


_RMWY_STAGE_CHARS = {2: '人', 3: '民', 4: '万', 5: '岁'}


def _draw_rmwy_tree(surf: pygame.Surface, stage: int, health: float, dead: bool,
                    level_up_glow: bool = False, t: float = 0.0):
    """Render 人民万岁 skin: stages 2-5 show gold Chinese characters on deep-red cards."""
    if stage <= 1:
        # Stages 0-1 use normal rendering with empty palette
        draw_tree(surf, stage, health, dead, level_up_glow, t, {})
        return

    surf.fill((0, 0, 0, 0))
    cx = TREE_W // 2
    ground_y = TREE_H - 6

    char = _RMWY_STAGE_CHARS.get(stage, '岁')

    # Card background: deep crimson, dimmed when dead or sick
    card = pygame.Rect(2, 2, TREE_W - 4, TREE_H - 10)
    if dead:
        bg = (45, 12, 12)
    elif health < 0.4:
        bg = (90, 10, 10)
    else:
        bg = (128, 12, 12)
    pygame.draw.rect(surf, bg, card, border_radius=4)

    # Gold border (brighter on level-up)
    if dead:
        border_color = (70, 55, 45)
    elif level_up_glow:
        border_color = (255, 235, 60)
    else:
        border_color = (195, 155, 15)
    pygame.draw.rect(surf, border_color, card, 2, border_radius=4)

    # Gold character
    font = _get_rmwy_font()
    if dead:
        char_color = (90, 78, 58)
    elif health < 0.5:
        dim = 0.4 + 0.6 * (health / 0.5)
        char_color = tuple(int(c * dim) for c in (255, 215, 0))
    else:
        char_color = (255, 215, 0)

    ts = font.render(char, True, char_color)
    tx = card.x + (card.w - ts.get_width()) // 2
    ty = card.y + (card.h - ts.get_height()) // 2
    surf.blit(ts, (tx, ty))

    # Dark-red dirt patch at bottom
    pygame.draw.ellipse(surf, (70, 8, 8), (cx - 10, ground_y - 3, 20, 6))

    if level_up_glow:
        glow = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
        glow.fill((255, 200, 0, 55))
        surf.blit(glow, (0, 0))


# ── Rose skin drawing ──────────────────────────────────────────────────────────

def _rose_colors(health: float, dead: bool):
    """Returns (petal_outer, petal_inner, stem, leaf, center)."""
    if dead:
        return (88, 70, 58), (100, 82, 66), (42, 55, 30), (48, 62, 32), (110, 90, 55)
    h = ( (185, 40, 65), (215, 80, 100), (35, 110, 45), (45, 130, 55), (255, 210, 50) )
    s = ( (145, 85, 68), (165, 105, 78), (55, 80, 32),  (70, 100, 40), (185, 155, 35) )
    d = ( (100, 80, 68), (115, 92, 72),  (45, 58, 28),  (55, 68, 35),  (140, 115, 45) )
    if health >= 0.5:
        t = (health - 0.5) / 0.5
        return tuple(_lerp_color(s[i], h[i], t) for i in range(5))
    else:
        t = health / 0.5
        return tuple(_lerp_color(d[i], s[i], t) for i in range(5))


def _rose_leaf(surf, x, y, flip: bool, color):
    pts = [(x, y - 4), (x + (-5 if flip else 5), y - 1),
           (x + (-7 if flip else 7), y + 2), (x + (-5 if flip else 5), y + 5), (x, y + 3)]
    pygame.draw.polygon(surf, color, pts)


def _rose_head(surf, cx, cy, size, p_out, p_in, ctr):
    """Draw a stylised rose bloom centred at (cx, cy)."""
    off = max(2, int(size * 0.52))
    r   = max(3, int(size * 0.60))
    # Outer petal ring (4 cardinal)
    for dx, dy in ((0, -off), (off, 0), (0, off), (-off, 0)):
        pygame.draw.circle(surf, p_out, (cx + dx, cy + dy), r)
    # Diagonal petals
    d2  = max(2, int(size * 0.36))
    r2  = max(2, int(size * 0.44))
    for dx, dy in ((d2, -d2), (d2, d2), (-d2, d2), (-d2, -d2)):
        pygame.draw.circle(surf, p_in, (cx + dx, cy + dy), r2)
    # Inner bloom + centre
    pygame.draw.circle(surf, p_in,  (cx, cy), max(3, int(size * 0.50)))
    pygame.draw.circle(surf, ctr,   (cx, cy), max(2, int(size * 0.26)))


def _draw_rose_tree(surf: pygame.Surface, stage: int, health: float, dead: bool,
                    level_up_glow: bool = False, t: float = 0.0):
    surf.fill((0, 0, 0, 0))
    cx       = TREE_W // 2
    gy       = TREE_H - 6          # ground y
    sway     = int(math.sin(t * 1.5) * 1.5) if health > 0.5 and not dead else 0
    p_out, p_in, stem_c, leaf_c, ctr_c = _rose_colors(health, dead)

    # Dirt patch
    pygame.draw.ellipse(surf, _lerp_color((80, 60, 40), (60, 40, 25), 0 if dead else 1),
                        (cx - 14, gy - 4, 28, 8))

    if stage == 0:
        return

    if stage == 1:   # tiny sprout
        pygame.draw.line(surf, stem_c,  (cx, gy - 2), (cx, gy - 7), 2)
        pygame.draw.circle(surf, leaf_c, (cx, gy - 8), 2)
        return

    # Stage 2: small closed bud
    if stage == 2:
        sh   = 13
        sx   = cx + sway
        pygame.draw.line(surf, stem_c, (cx, gy - 2), (cx, gy - sh), 2)
        by   = gy - sh
        pygame.draw.ellipse(surf, p_out, (sx - 4, by - 7, 8, 10))
        pygame.draw.ellipse(surf, p_in,  (sx - 2, by - 5, 5, 6))
        return

    # Stage 3: half-open rose + one leaf pair
    if stage == 3:
        sh = 20
        pygame.draw.line(surf, stem_c, (cx, gy - 2), (cx, gy - sh), 2)
        # Leaf pair at mid-stem
        lm = gy - 11
        _rose_leaf(surf, cx - 1, lm, True,  leaf_c)
        _rose_leaf(surf, cx + 1, lm, False, leaf_c)
        if dead:
            pygame.draw.circle(surf, p_out, (cx + sway, gy - sh - 4), 5)
        else:
            # 3-petal half-open
            hy = gy - sh - 6
            for dx, dy in ((0, -4), (-4, 3), (4, 3)):
                pygame.draw.circle(surf, p_out, (cx + sway + dx, hy + dy), 6)
            pygame.draw.circle(surf, p_in,  (cx + sway, hy), 4)
            pygame.draw.circle(surf, ctr_c, (cx + sway, hy), 2)
        return

    # Stage 4: full bloom + two leaf pairs
    if stage == 4:
        sh = 28
        pygame.draw.line(surf, stem_c, (cx, gy - 2), (cx, gy - sh), 3)
        _rose_leaf(surf, cx - 1, gy - 10, True,  leaf_c)
        _rose_leaf(surf, cx + 1, gy - 10, False, leaf_c)
        _rose_leaf(surf, cx - 1, gy - 20, True,  leaf_c)
        _rose_leaf(surf, cx + 1, gy - 20, False, leaf_c)
        hy = gy - sh - 9
        if dead:
            pygame.draw.circle(surf, p_out, (cx + sway, hy), 7)
        else:
            _rose_head(surf, cx + sway, hy, 11, p_out, p_in, ctr_c)
        if level_up_glow:
            glow = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
            glow.fill((255, 80, 120, 45))
            surf.blit(glow, (0, 0))
        return

    # Stage 5: rose garden – 3 flowers
    # Main centre rose
    sh_m = 33
    pygame.draw.line(surf, stem_c, (cx, gy - 2), (cx, gy - sh_m), 3)
    _rose_leaf(surf, cx - 1, gy - 12, True,  leaf_c)
    _rose_leaf(surf, cx + 1, gy - 12, False, leaf_c)
    _rose_leaf(surf, cx - 1, gy - 23, True,  leaf_c)
    _rose_leaf(surf, cx + 1, gy - 23, False, leaf_c)
    if dead:
        pygame.draw.circle(surf, p_out, (cx + sway, gy - sh_m - 8), 8)
    else:
        _rose_head(surf, cx + sway, gy - sh_m - 8, 12, p_out, p_in, ctr_c)

    # Left side rose (shorter)
    lx  = cx - 12
    sh_l = 22
    pygame.draw.line(surf, stem_c, (lx, gy - 2), (lx, gy - sh_l), 2)
    _rose_leaf(surf, lx - 1, gy - 12, True, leaf_c)
    if dead:
        pygame.draw.circle(surf, p_out, (lx, gy - sh_l - 6), 6)
    else:
        _rose_head(surf, lx, gy - sh_l - 6, 8, p_out, p_in, ctr_c)

    # Right side closed bud
    rx  = cx + 11
    sh_r = 17
    pygame.draw.line(surf, stem_c, (rx, gy - 2), (rx, gy - sh_r), 2)
    _rose_leaf(surf, rx + 1, gy - 10, False, leaf_c)
    by_r = gy - sh_r
    pygame.draw.ellipse(surf, p_out, (rx - 4, by_r - 7, 8, 10))
    pygame.draw.ellipse(surf, p_in,  (rx - 2, by_r - 5, 5, 6))

    if level_up_glow:
        glow = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
        glow.fill((255, 80, 120, 45))
        surf.blit(glow, (0, 0))


def _leaf_colors(health: float, dead: bool, pal: dict) -> Tuple:
    if dead:
        return C_LEAF_DEAD, C_LEAF_DEAD
    lh1 = pal.get('leaf_h1', C_LEAF_HEALTHY)
    lh2 = pal.get('leaf_h2', C_LEAF_HEALTHY2)
    ls1 = pal.get('leaf_s1', C_LEAF_SICK)
    ls2 = pal.get('leaf_s2', C_LEAF_SICK2)
    if health < 0.5:
        frac = health / 0.5
        c1 = _lerp_color(C_LEAF_DEAD, ls1, frac)
        c2 = _lerp_color(C_LEAF_DEAD, ls2, frac)
        return c1, c2
    frac = (health - 0.5) / 0.5
    c1 = _lerp_color(ls1, lh1, frac)
    c2 = _lerp_color(ls2, lh2, frac)
    return c1, c2


def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _trunk_color(health: float, dead: bool, pal: dict):
    if dead:
        return C_TRUNK_DEAD
    th = pal.get('trunk', C_TRUNK_HEALTHY)
    if health < 0.5:
        frac = health / 0.5
        return _lerp_color(C_TRUNK_DEAD, C_TRUNK_SICK, frac)
    frac = (health - 0.5) / 0.5
    return _lerp_color(C_TRUNK_SICK, th, frac)


def draw_tree(surf: pygame.Surface, stage: int, health: float, dead: bool,
              level_up_glow: bool = False, t: float = 0.0, palette: dict = None):
    """
    Draw a tree onto surf starting at (0,0) in TREE_W×TREE_H space.
    t: time in seconds (for subtle animation).
    palette: optional color override dict (from SKIN_PALETTES).
    """
    pal = palette or {}
    surf.fill((0, 0, 0, 0))   # transparent
    cx = TREE_W // 2
    ground_y = TREE_H - 6
    trunk_color = _trunk_color(health, dead, pal)
    lc1, lc2 = _leaf_colors(health, dead, pal)
    dirt_color = pal.get('dirt', C_DIRT)

    if stage == 0:
        _draw_dirt(surf, cx, ground_y, dirt_color)
        return

    if stage == 1:   # seed
        _draw_dirt(surf, cx, ground_y, dirt_color)
        pygame.draw.circle(surf, C_SEED, (cx, ground_y - 4), 3)
        pygame.draw.line(surf, C_SEED, (cx, ground_y - 4), (cx, ground_y - 8), 1)
        return

    # Trunk height scales with stage
    trunk_heights = [0, 0, 10, 18, 26, 32]
    trunk_widths  = [0, 0,  2,  3,  4,  6]
    th = trunk_heights[stage]
    tw = trunk_widths[stage]

    # Draw trunk
    trunk_rect = pygame.Rect(cx - tw//2, ground_y - th, tw, th)
    pygame.draw.rect(surf, trunk_color, trunk_rect)

    if dead:
        # Just bare branches
        _draw_dead_branches(surf, cx, ground_y - th, stage, trunk_color)
        return

    sway = math.sin(t * 1.5) * 1.5 if health > 0.5 else 0

    if stage == 2:   # small sapling
        crown_y = ground_y - th - 8
        pygame.draw.circle(surf, lc1, (int(cx + sway), crown_y), 8)
        pygame.draw.circle(surf, lc2, (int(cx + sway) - 3, crown_y + 2), 5)

    elif stage == 3:   # young tree
        crown_y = ground_y - th - 10
        pygame.draw.circle(surf, lc2, (int(cx + sway), crown_y + 4), 11)
        pygame.draw.circle(surf, lc1, (int(cx + sway), crown_y), 13)

    elif stage == 4:   # mature tree
        crown_y = ground_y - th - 12
        pygame.draw.circle(surf, lc2, (int(cx + sway), crown_y + 6), 13)
        pygame.draw.circle(surf, lc1, (int(cx + sway), crown_y), 15)
        pygame.draw.circle(surf, lc2, (int(cx + sway) - 7, crown_y + 5), 9)
        pygame.draw.circle(surf, lc2, (int(cx + sway) + 7, crown_y + 5), 9)
        # Small flower
        if health > 0.7:
            pygame.draw.circle(surf, C_FLOWER, (int(cx + sway) + 10, crown_y + 2), 3)

    elif stage == 5:   # giant tree – three-tier canopy
        crown_y = ground_y - th - 14
        # Bottom tier (widest)
        pygame.draw.circle(surf, lc2, (int(cx + sway), crown_y + 10), 16)
        pygame.draw.circle(surf, lc2, (int(cx + sway) - 10, crown_y + 8), 12)
        pygame.draw.circle(surf, lc2, (int(cx + sway) + 10, crown_y + 8), 12)
        # Middle tier
        pygame.draw.circle(surf, lc1, (int(cx + sway), crown_y + 2), 15)
        pygame.draw.circle(surf, lc2, (int(cx + sway) - 7, crown_y),  10)
        pygame.draw.circle(surf, lc2, (int(cx + sway) + 7, crown_y),  10)
        # Top spire
        pygame.draw.circle(surf, lc1, (int(cx + sway), crown_y - 7), 10)
        # Flowers + butterfly
        if health > 0.7:
            pygame.draw.circle(surf, C_FLOWER, (int(cx + sway) - 13, crown_y + 2), 3)
            pygame.draw.circle(surf, C_FLOWER, (int(cx + sway) + 14, crown_y + 4), 3)
        if health > 0.85:
            bx = int(cx + sway + 16 + math.sin(t * 2) * 4)
            by = int(crown_y + 2 + math.cos(t * 2.5) * 3)
            pygame.draw.circle(surf, C_BUTTERFLY, (bx, by), 3)

    # Level-up glow overlay
    if level_up_glow:
        glow = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
        glow.fill((255, 255, 150, 60))
        surf.blit(glow, (0, 0))


def _draw_dirt(surf, cx, ground_y, color=None):
    pygame.draw.ellipse(surf, color or C_DIRT, (cx - 14, ground_y - 4, 28, 8))


def _draw_dead_branches(surf, cx, top_y, stage, color):
    if stage >= 3:
        pygame.draw.line(surf, color, (cx, top_y), (cx - 10, top_y - 8), 2)
        pygame.draw.line(surf, color, (cx, top_y), (cx + 8, top_y - 6), 2)
    if stage >= 4:
        pygame.draw.line(surf, color, (cx - 10, top_y - 8), (cx - 16, top_y - 14), 1)
        pygame.draw.line(surf, color, (cx + 8, top_y - 6), (cx + 14, top_y - 12), 1)


# ── Surface cache ─────────────────────────────────────────────────────────────
# Cached at fixed health=1.0 and health=0.25 per stage; animated version redrawn each frame.

_CACHE: Dict[Tuple, pygame.Surface] = {}


def get_tree_surface(stage: int, health: float, dead: bool,
                     level_up_glow: bool = False, t: float = 0.0,
                     skin_id: str = '') -> pygame.Surface:
    """
    For animated trees (stage 5, or level-up glow) this always redraws.
    For others, uses a discrete health-bucket cache for performance.
    """
    h_bucket = round(health, 1)

    if skin_id == 'rmwy':
        key = ('rmwy', stage, h_bucket, dead, level_up_glow)
        if key not in _CACHE:
            surf = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
            _draw_rmwy_tree(surf, stage, health, dead, level_up_glow, t)
            _CACHE[key] = surf
        return _CACHE[key]

    if skin_id == 'rose':
        key = ('rose', stage, h_bucket, dead, level_up_glow,
               int(t * 3) % 20 if stage == 5 else 0)
        if key not in _CACHE:
            surf = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
            _draw_rose_tree(surf, stage, health, dead, level_up_glow, t)
            _CACHE[key] = surf
        return _CACHE[key]

    palette = SKIN_PALETTES.get(skin_id, {})
    key = (stage, h_bucket, dead, level_up_glow,
           int(t * 3) % 30 if stage == 5 else 0, skin_id)

    if key not in _CACHE:
        surf = pygame.Surface((TREE_W, TREE_H), pygame.SRCALPHA)
        draw_tree(surf, stage, health, dead, level_up_glow, t, palette)
        _CACHE[key] = surf

    return _CACHE[key]


def clear_cache():
    _CACHE.clear()
