"""
All constants, 104-key keyboard layout, and color palette for Keyboard Forest.
"""

# ── Window & display ──────────────────────────────────────────────────────────
WINDOW_W, WINDOW_H = 1200, 760
WINDOW_TITLE = "键盘森林"
TARGET_FPS = 60

# ── Persistence ───────────────────────────────────────────────────────────────
DB_PATH = "keyboard_forest.db"
SAVE_INTERVAL_S = 30.0

# ── KeyTree growth ────────────────────────────────────────────────────────────
# Incremental XP required per stage (stage N-1 → stage N).
# Total to first max: 500+5000+50000+200000 = 255,500 XP.
# A key pressed 500 times/day takes ~1.4 years to reach stage 5.
STAGE_XP_THRESHOLDS = [500, 5_000, 50_000, 200_000]
# Once at stage 5, each additional 200,000 XP graduates the tree → new seed planted.
GRADUATION_XP = 200_000
BASE_XP_PER_PRESS = 1.0
HIGH_FREQ_TOP20_MULT = 1.5
HIGH_FREQ_TOP40_MULT = 1.2
FREQ_RECALC_INTERVAL_S = 60.0
FREQ_LOOKBACK_DAYS = 7

# ── KeyTree health / decay ────────────────────────────────────────────────────
HEALTH_DECAY_START_H = 24.0
HEALTH_DECAY_PER_H = 0.05
HEALTH_SICK_THRESHOLD = 0.5
HEALTH_CHECK_INTERVAL_S = 60.0

# ── Climate ───────────────────────────────────────────────────────────────────
RAIN_RATE_THRESHOLD = 3.0
RAIN_SUSTAIN_S = 60.0
RAIN_DURATION_S = 600.0
RAIN_XP_MULT = 2.0
DROUGHT_IDLE_S = 7200.0
DROUGHT_RECOVER_RATE = 0.8
DROUGHT_RECOVER_WINDOW_S = 300.0
DROUGHT_XP_MULT = 0.3

# ── Keyboard visual grid ──────────────────────────────────────────────────────
KEY_UNIT = 50        # px per unit step
KEY_W    = 47        # actual 1u key pixel width
KEY_H    = 44        # actual key pixel height
KEY_GAP  = 3         # gap between keys
ROW_STEP = KEY_H + KEY_GAP   # = 47, vertical step between rows

GRID_X   = 16        # main keyboard left edge
GRID_Y   = 62        # keyboard top (below HUD)

# Derived tall/wide variants
TALL_H   = KEY_H * 2 + KEY_GAP   # 91 – used for numpad +/Enter
WIDE_W   = KEY_W * 2 + KEY_GAP   # 97 – used for numpad 0

# ── UI layout ─────────────────────────────────────────────────────────────────
HUD_H        = 56
STATUS_H     = 38
DETAIL_W     = 300
FLASH_DURATION    = 0.25
DETAIL_ANIM_SPEED = 900

# Reports directory
REPORTS_DIR = "reports"

# ── Pixel-art color palette ───────────────────────────────────────────────────
C_SKY_TOP        = (135, 206, 235)
C_SKY_BOT        = (180, 230, 220)
C_SKY_RAIN_TOP   = ( 70,  80, 100)
C_SKY_RAIN_BOT   = (100, 110, 130)
C_SKY_DROUGHT_TOP= (200, 130,  50)
C_SKY_DROUGHT_BOT= (220, 170,  90)
C_GROUND         = (139, 115,  85)
C_GROUND_DROUGHT = (160, 120,  60)

C_CELL_BG        = ( 40,  50,  35)
C_CELL_BORDER    = ( 60,  75,  50)
C_CELL_HOVER     = ( 80, 100,  65)
C_CELL_FLASH     = (255, 240, 120)
C_CELL_DEAD      = ( 45,  40,  35)
C_KEY_LABEL      = (200, 220, 190)
C_KEY_LABEL_DEAD = (100,  95,  90)

C_TRUNK_HEALTHY  = ( 90,  55,  20)
C_TRUNK_SICK     = ( 80,  60,  30)
C_TRUNK_DEAD     = ( 70,  65,  60)
C_LEAF_HEALTHY   = ( 60, 180,  50)
C_LEAF_HEALTHY2  = ( 45, 155,  35)
C_LEAF_SICK      = (180, 170,  40)
C_LEAF_SICK2     = (150, 140,  30)
C_LEAF_DEAD      = ( 75,  70,  65)
C_DIRT           = (110,  85,  55)
C_SEED           = ( 80, 120,  50)
C_FLOWER         = (255, 200,  80)
C_BUTTERFLY      = (200, 140, 240)

C_HUD_BG         = ( 25,  35,  20)
C_HUD_TEXT       = (210, 230, 200)
C_STATUS_BG      = ( 20,  28,  16)
C_STATUS_TEXT    = (170, 190, 155)
C_DETAIL_BG      = ( 30,  42,  25, 230)
C_DETAIL_TITLE   = (200, 235, 185)
C_BAR_BG         = ( 50,  60,  45)
C_BAR_XP         = ( 80, 200, 100)
C_BAR_HP_HIGH    = ( 80, 200,  80)
C_BAR_HP_MID     = (220, 180,  50)
C_BAR_HP_LOW     = (220,  70,  50)

C_RAIN           = (150, 190, 255, 160)
C_DROUGHT_CRACK  = (120,  90,  50)

C_CHIP_RAIN      = ( 60, 120, 220)
C_CHIP_DROUGHT   = (200, 100,  30)
C_CHIP_NORMAL    = ( 60, 160,  80)

# Stats view colours
C_STATS_BG       = ( 18,  25,  14)
C_STATS_PANEL    = ( 28,  38,  22)
C_STATS_BORDER   = ( 55,  75,  45)
C_STATS_TITLE    = (180, 230, 160)
C_STATS_TEXT     = (160, 200, 145)
C_STATS_DIM      = (110, 140, 100)
C_HEATMAP_COLD   = ( 35,  45,  30)
C_HEATMAP_HOT    = ( 40, 200,  60)
C_CHART_BAR      = ( 60, 170,  80)
C_CHART_LINE     = (100, 220, 120)
C_CHART_GRID     = ( 45,  60,  38)

# ── 104-key layout builder ────────────────────────────────────────────────────
# Row Y positions (shared across all sections)
_ROW_Y = [GRID_Y + i * ROW_STEP for i in range(7)]
# _ROW_Y[0]=62  [1]=109  [2]=156  [3]=203  [4]=250  [5]=297  [6]=344


def _place_key(rects, name, x, y, w=None, h=None):
    """Add a key to rects dict with given pixel position. Default size = KEY_W×KEY_H."""
    if name is None:
        return
    rects[name] = (x, y, w if w is not None else KEY_W, h if h is not None else KEY_H)


def _place_row(rects, keys, x0, y):
    """
    Walk a list of (name, width_units) left-to-right and register each key.
    name=None is a spacer (no key registered but space consumed).
    """
    x = x0
    for name, wu in keys:
        pw = int(round(wu * KEY_UNIT)) - KEY_GAP
        if name is not None:
            rects[name] = (x, y, pw, KEY_H)
        x += int(round(wu * KEY_UNIT))


def _build_key_rects():
    rects = {}

    # ── Section A: Main keyboard ─────────────────────────────────────────
    A = GRID_X

    # Row 0 – Escape + Function keys
    _place_row(rects, [
        ('esc', 1.0), (None, 0.5),
        ('f1', 1.0), ('f2', 1.0), ('f3', 1.0), ('f4', 1.0), (None, 0.25),
        ('f5', 1.0), ('f6', 1.0), ('f7', 1.0), ('f8', 1.0), (None, 0.25),
        ('f9', 1.0), ('f10', 1.0), ('f11', 1.0), ('f12', 1.0),
    ], A, _ROW_Y[0])

    # Row 1 – Number row
    _place_row(rects, [
        ('`', 1.0), ('1', 1.0), ('2', 1.0), ('3', 1.0), ('4', 1.0),
        ('5', 1.0), ('6', 1.0), ('7', 1.0), ('8', 1.0), ('9', 1.0),
        ('0', 1.0), ('-', 1.0), ('=', 1.0), ('backspace', 2.0),
    ], A, _ROW_Y[1])

    # Row 2 – QWERTY
    _place_row(rects, [
        ('tab', 1.5),
        ('q', 1.0), ('w', 1.0), ('e', 1.0), ('r', 1.0), ('t', 1.0),
        ('y', 1.0), ('u', 1.0), ('i', 1.0), ('o', 1.0), ('p', 1.0),
        ('[', 1.0), (']', 1.0), ('\\', 1.5),
    ], A, _ROW_Y[2])

    # Row 3 – Home row
    _place_row(rects, [
        ('caps_lock', 1.75),
        ('a', 1.0), ('s', 1.0), ('d', 1.0), ('f', 1.0), ('g', 1.0),
        ('h', 1.0), ('j', 1.0), ('k', 1.0), ('l', 1.0), (';', 1.0),
        ("'", 1.0), ('enter', 2.25),
    ], A, _ROW_Y[3])

    # Row 4 – ZXCV
    _place_row(rects, [
        ('shift', 2.25),
        ('z', 1.0), ('x', 1.0), ('c', 1.0), ('v', 1.0), ('b', 1.0),
        ('n', 1.0), ('m', 1.0), (',', 1.0), ('.', 1.0), ('/', 1.0),
        ('shift_r', 2.75),
    ], A, _ROW_Y[4])

    # Row 5 – Modifiers
    _place_row(rects, [
        ('ctrl', 1.5), ('win', 1.25), ('alt', 1.25), ('space', 6.0),
        ('alt_r', 1.25), ('win_r', 1.25), ('menu', 1.25), ('ctrl_r', 1.5),
    ], A, _ROW_Y[5])

    # ── Section B: Navigation cluster ────────────────────────────────────
    B = 800   # section x start

    # Row 0 – system keys
    _place_key(rects, 'print_screen', B,       _ROW_Y[0])
    _place_key(rects, 'scroll_lock',  B + 50,  _ROW_Y[0])
    _place_key(rects, 'pause',        B + 100, _ROW_Y[0])

    # Row 2 – insert group
    _place_key(rects, 'insert',   B,       _ROW_Y[2])
    _place_key(rects, 'home',     B + 50,  _ROW_Y[2])
    _place_key(rects, 'page_up',  B + 100, _ROW_Y[2])

    # Row 3 – delete group
    _place_key(rects, 'delete', B,       _ROW_Y[3])
    _place_key(rects, 'end',    B + 50,  _ROW_Y[3])
    _place_key(rects, 'page_down', B + 100, _ROW_Y[3])

    # Rows 5–6 – arrow keys (inverted-T)
    _place_key(rects, 'up',    B + 50,  _ROW_Y[5])
    _place_key(rects, 'left',  B,       _ROW_Y[6])
    _place_key(rects, 'down',  B + 50,  _ROW_Y[6])
    _place_key(rects, 'right', B + 100, _ROW_Y[6])

    # ── Section C: Numpad ─────────────────────────────────────────────────
    C = 975   # section x start

    # Row 2
    _place_key(rects, 'num_lock',     C,        _ROW_Y[2])
    _place_key(rects, 'np_divide',    C + 50,   _ROW_Y[2])
    _place_key(rects, 'np_multiply',  C + 100,  _ROW_Y[2])
    _place_key(rects, 'np_subtract',  C + 150,  _ROW_Y[2])

    # Row 3 (np_add is tall: spans rows 3-4)
    _place_key(rects, 'np_7',    C,        _ROW_Y[3])
    _place_key(rects, 'np_8',    C + 50,   _ROW_Y[3])
    _place_key(rects, 'np_9',    C + 100,  _ROW_Y[3])
    _place_key(rects, 'np_add',  C + 150,  _ROW_Y[3], h=TALL_H)

    # Row 4
    _place_key(rects, 'np_4', C,        _ROW_Y[4])
    _place_key(rects, 'np_5', C + 50,   _ROW_Y[4])
    _place_key(rects, 'np_6', C + 100,  _ROW_Y[4])

    # Row 5 (np_enter is tall: spans rows 5-6)
    _place_key(rects, 'np_1',    C,        _ROW_Y[5])
    _place_key(rects, 'np_2',    C + 50,   _ROW_Y[5])
    _place_key(rects, 'np_3',    C + 100,  _ROW_Y[5])
    _place_key(rects, 'np_enter', C + 150, _ROW_Y[5], h=TALL_H)

    # Row 6 (np_0 is wide: spans 2 cols)
    _place_key(rects, 'np_0',      C,        _ROW_Y[6], w=WIDE_W)
    _place_key(rects, 'np_decimal', C + 100, _ROW_Y[6])

    return rects


KEY_RECTS: dict = _build_key_rects()
ALL_KEYS:  list = list(KEY_RECTS.keys())   # 104 keys

# ── Display labels ────────────────────────────────────────────────────────────
KEY_LABELS: dict = {
    'esc': 'Esc', 'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
    'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
    'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12',
    '`': '`', '-': '-', '=': '=', 'backspace': '←',
    'tab': 'Tab', '[': '[', ']': ']', '\\': '\\',
    'caps_lock': 'Caps', ';': ';', "'": "'", 'enter': '↩',
    'shift': 'Shift', ',': ',', '.': '.', '/': '/', 'shift_r': 'Shift',
    'ctrl': 'Ctrl', 'win': 'Win', 'alt': 'Alt', 'space': 'Space',
    'alt_r': 'Alt', 'win_r': 'Win', 'menu': 'Menu', 'ctrl_r': 'Ctrl',
    'print_screen': 'PrtSc', 'scroll_lock': 'ScrLk', 'pause': 'Pause',
    'insert': 'Ins', 'home': 'Home', 'page_up': 'PgUp',
    'delete': 'Del', 'end': 'End', 'page_down': 'PgDn',
    'up': '↑', 'down': '↓', 'left': '←', 'right': '→',
    'num_lock': 'NumLk', 'np_divide': '/', 'np_multiply': '*',
    'np_subtract': '-', 'np_add': '+', 'np_enter': '↩',
    'np_0': '0', 'np_1': '1', 'np_2': '2', 'np_3': '3',
    'np_4': '4', 'np_5': '5', 'np_6': '6', 'np_7': '7',
    'np_8': '8', 'np_9': '9', 'np_decimal': '.',
}
# Letters and digits use their own character as label
for _c in 'abcdefghijklmnopqrstuvwxyz':
    KEY_LABELS[_c] = _c.upper()
for _c in '1234567890':
    KEY_LABELS[_c] = _c

# ── Legacy KEY_ROWS (kept for label lookup compatibility) ─────────────────────
# Not used for position calculation any more.
KEY_ROWS = []   # intentionally empty – use KEY_RECTS / KEY_LABELS instead
