"""
Shop system: gold coin production, skin unlocks, and consumable items.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional


# ── Skin palettes ─────────────────────────────────────────────────────────────
# Keys: leaf_h1/h2 (healthy leaf colors), leaf_s1/s2 (sick), trunk, dirt
SKIN_PALETTES: Dict[str, Dict] = {
    '': {},   # default – uses config colors
    'autumn': {
        'leaf_h1': (220, 140,  60), 'leaf_h2': (180, 100,  40),
        'leaf_s1': (160,  90,  40), 'leaf_s2': (130,  70,  30),
        'trunk':   (100,  70,  50), 'dirt':    (110,  80,  55),
    },
    'snow': {
        'leaf_h1': (220, 240, 255), 'leaf_h2': (180, 210, 240),
        'leaf_s1': (180, 200, 220), 'leaf_s2': (150, 180, 210),
        'trunk':   (120, 100,  90), 'dirt':    (200, 220, 240),
    },
    'sakura': {
        'leaf_h1': (255, 180, 200), 'leaf_h2': (230, 150, 180),
        'leaf_s1': (200, 140, 160), 'leaf_s2': (170, 120, 140),
        'trunk':   (130,  90,  80), 'dirt':    (200, 160, 150),
    },
    'golden': {
        'leaf_h1': (255, 220,  50), 'leaf_h2': (220, 180,  30),
        'leaf_s1': (200, 170,  40), 'leaf_s2': (170, 140,  30),
        'trunk':   (120,  90,  50), 'dirt':    (160, 130,  60),
    },
    'crystal': {
        'leaf_h1': (100, 220, 255), 'leaf_h2': ( 60, 180, 240),
        'leaf_s1': ( 80, 170, 200), 'leaf_s2': ( 60, 140, 170),
        'trunk':   ( 80, 140, 180), 'dirt':    (100, 160, 200),
    },
    'obsidian': {
        'leaf_h1': ( 80,  60, 120), 'leaf_h2': ( 60,  40, 100),
        'leaf_s1': ( 60,  50,  90), 'leaf_s2': ( 50,  40,  80),
        'trunk':   ( 50,  40,  70), 'dirt':    ( 70,  55,  90),
    },
    'rmwy': {},   # special text rendering in tree_sprites – no palette used
    'rose': {
        'leaf_h1': (185,  40,  65), 'leaf_h2': (155,  25,  50),
        'leaf_s1': (175,  90,  75), 'leaf_s2': (145,  70,  60),
        'trunk':   ( 35, 100,  45), 'dirt':    (115,  90,  65),
    },
}

# Preview swatch color for shop UI (shown as a color block)
SKIN_SWATCH: Dict[str, tuple] = {
    '':         ( 60, 180,  50),
    'autumn':   (220, 140,  60),
    'snow':     (220, 240, 255),
    'sakura':   (255, 180, 200),
    'golden':   (255, 220,  50),
    'crystal':  (100, 220, 255),
    'obsidian': ( 80,  60, 120),
    'rmwy':     (130,  12,  12),
    'rose':     (185,  40,  65),
}


@dataclass
class ShopItem:
    id: str
    name: str
    description: str
    price: int
    category: str    # 'skin' | 'consumable'
    skin_id: str = ''
    target: bool = False   # consumables that require selecting a key


SHOP_ITEMS: List[ShopItem] = [
    # Skins (free → increasing cost)
    ShopItem('skin_rmwy',     '人民万岁装', '四个成长阶段化身人民万岁金字',    0,   'skin', 'rmwy'),
    ShopItem('skin_autumn',   '秋叶装',      '树叶变为橙黄秋色',               15,  'skin', 'autumn'),
    ShopItem('skin_snow',     '白雪装',      '树冠披上冰晶白雪',               25,  'skin', 'snow'),
    ShopItem('skin_sakura',   '樱花装',      '树叶化为粉白樱花',               50,  'skin', 'sakura'),
    ShopItem('skin_golden',   '黄金装',      '树木闪耀夺目金光',              100,  'skin', 'golden'),
    ShopItem('skin_crystal',  '水晶装',      '树冠晶莹蓝光环绕',              200,  'skin', 'crystal'),
    ShopItem('skin_obsidian', '黑曜装',      '深紫神秘暗夜之树',              500,  'skin', 'obsidian'),
    ShopItem('skin_rose',     '玫瑰花装',    '深红玫瑰花冠，娇艳欲滴',        999,  'skin', 'rose'),
    # Consumables
    ShopItem('potion',        '急救营养液',  '立即将一棵树恢复至满血',    20,  'consumable', target=True),
    ShopItem('rain_card',     '暴雨调控卡',  '立即开启10分钟暴雨（经验×3）',25,'consumable'),
    ShopItem('drought_card',  '驱旱卡',      '消除当前干旱，恢复晴天',    35,  'consumable'),
    ShopItem('xp_card_s',     '生长卡(小)',  '为选定按键增加5000经验',    30,  'consumable', target=True),
    ShopItem('xp_card_m',     '生长卡(中)',  '为选定按键增加50000经验',   80,  'consumable', target=True),
    ShopItem('xp_card_l',     '生长卡(大)',  '为选定按键增加200000经验', 200,  'consumable', target=True),
]

ITEM_MAP: Dict[str, ShopItem] = {it.id: it for it in SHOP_ITEMS}
SKIN_ITEMS = [it for it in SHOP_ITEMS if it.category == 'skin']
CONSUMABLE_ITEMS = [it for it in SHOP_ITEMS if it.category == 'consumable']

# skin_id (palette key like 'autumn') → display name
SKIN_ID_TO_NAME: Dict[str, str] = {'': '默认绿'}
SKIN_ID_TO_NAME.update({it.skin_id: it.name for it in SKIN_ITEMS})

# skin_id → shop item id (for reverse lookup in detail view)
SKIN_ID_TO_ITEM_ID: Dict[str, str] = {it.skin_id: it.id for it in SKIN_ITEMS}


# ── Background themes ─────────────────────────────────────────────────────────

@dataclass
class BgItem:
    bg_id: str
    name:  str
    price: int
    desc:  str


BG_ITEMS: List[BgItem] = [
    BgItem('default', '翠绿森林',    0,    '默认绿意森林，清新自然'),
    BgItem('rmwy',    '人民万岁',    0,    '深红底色，金字辉映，人民力量'),
    BgItem('dusk',    '暮色余晖',    30,   '紫红暮色，温暖静谧'),
    BgItem('ocean',   '深海秘境',    80,   '幽蓝深海，宁静神秘'),
    BgItem('desert',  '黄沙大漠',    180,  '金黄沙漠，苍茫辽阔'),
    BgItem('galaxy',  '星河璀璨',    350,  '深邃星空，璀璨银河'),
    BgItem('s520',    '520爱你',     520,  '粉色浪漫，爱你每一天'),
    BgItem('volcano', '熔岩炽野',    600,  '炽热熔岩，赤焰之地'),
    BgItem('mystic',  '幽境仙林',    1000, '飘渺仙境，梦幻紫光'),
]

# Color scheme for each background — affects sky, ground, and key-cell colors
BG_THEMES: Dict[str, Dict] = {
    'default': {
        'sky_top':     (135, 206, 235), 'sky_bot':  (180, 230, 220),
        'ground':      (139, 115,  85),
        'cell_bg':     ( 40,  50,  35), 'cell_border': ( 60,  75,  50),
        'cell_hover':  ( 80, 100,  65), 'cell_flash':  (255, 240, 120),
        'cell_dead':   ( 45,  40,  35), 'key_label':   (200, 220, 190),
    },
    'rmwy': {
        'sky_top':     (140,  15,  15), 'sky_bot':  (100,  10,  10),
        'ground':      ( 75,   8,   8),
        'cell_bg':     ( 65,   8,   8), 'cell_border': (160,  35,  25),
        'cell_hover':  (185,  52,  30), 'cell_flash':  (255, 215,   0),
        'cell_dead':   ( 50,  18,  15), 'key_label':   (255, 215,   0),
    },
    'dusk': {
        'sky_top':     (175,  70, 110), 'sky_bot':  (220, 130,  75),
        'ground':      (100,  65,  55),
        'cell_bg':     ( 55,  30,  46), 'cell_border': ( 85,  52,  70),
        'cell_hover':  (100,  65,  85), 'cell_flash':  (230, 130, 160),
        'cell_dead':   ( 48,  36,  44), 'key_label':   (215, 165, 190),
    },
    'ocean': {
        'sky_top':     ( 15,  40,  90), 'sky_bot':  ( 30,  72, 135),
        'ground':      ( 20,  40,  70),
        'cell_bg':     ( 18,  36,  68), 'cell_border': ( 32,  62, 105),
        'cell_hover':  ( 42,  75, 122), 'cell_flash':  ( 80, 155, 225),
        'cell_dead':   ( 28,  40,  58), 'key_label':   (130, 185, 235),
    },
    'desert': {
        'sky_top':     (225, 165,  60), 'sky_bot':  (245, 205, 105),
        'ground':      (185, 145,  80),
        'cell_bg':     ( 70,  54,  25), 'cell_border': (105,  82,  42),
        'cell_hover':  (122,  96,  52), 'cell_flash':  (230, 185,  85),
        'cell_dead':   ( 58,  52,  38), 'key_label':   (225, 200, 135),
    },
    'galaxy': {
        'sky_top':     (  5,   5,  20), 'sky_bot':  ( 15,  15,  45),
        'ground':      ( 18,  18,  40),
        'cell_bg':     ( 14,  16,  42), 'cell_border': ( 30,  35,  80),
        'cell_hover':  ( 38,  44,  98), 'cell_flash':  (105,  85, 230),
        'cell_dead':   ( 26,  26,  48), 'key_label':   (165, 155, 235),
    },
    's520': {
        'sky_top':     (255, 195, 185), 'sky_bot':  (255, 225, 215),
        'ground':      (215, 155, 145),
        'cell_bg':     (190, 115, 110), 'cell_border': (225, 155, 150),
        'cell_hover':  (240, 175, 170), 'cell_flash':  (255, 100, 140),
        'cell_dead':   (170, 118, 118), 'key_label':   (255, 240, 240),
    },
    'volcano': {
        'sky_top':     ( 60,  10,   5), 'sky_bot':  (105,  32,  12),
        'ground':      ( 80,  20,  10),
        'cell_bg':     ( 50,  16,  12), 'cell_border': ( 85,  30,  22),
        'cell_hover':  (100,  38,  28), 'cell_flash':  (240, 105,  45),
        'cell_dead':   ( 48,  30,  28), 'key_label':   (245, 165, 105),
    },
    'mystic': {
        'sky_top':     ( 35,  15,  62), 'sky_bot':  ( 62,  32,  95),
        'ground':      ( 45,  25,  72),
        'cell_bg':     ( 32,  18,  52), 'cell_border': ( 62,  40,  98),
        'cell_hover':  ( 75,  50, 115), 'cell_flash':  (185, 125, 255),
        'cell_dead':   ( 40,  30,  52), 'key_label':   (205, 165, 250),
    },
}

# Swatch color for shop preview (use cell_bg as a representative mid-tone)
BG_SWATCH: Dict[str, tuple] = {
    bg_id: BG_THEMES[bg_id]['cell_bg'] for bg_id in BG_THEMES
}


class ShopSystem:
    def __init__(self, db):
        self.db = db
        self._coins: int = 0
        self._last_collect_date: str = ''
        self._inventory: Dict[str, int] = {}
        self.active_bg_id: str = 'default'
        self.owned_bgs: set = {'default'}
        self.load()

    def load(self):
        self._coins = int(self.db.get_app_stat('coin_balance', '0'))
        self._last_collect_date = self.db.get_app_stat('last_coin_collect', '')
        for item in SHOP_ITEMS:
            self._inventory[item.id] = int(self.db.get_app_stat(f'inv_{item.id}', '0'))
        self.active_bg_id = self.db.get_app_stat('active_bg', 'default')
        owned_raw = self.db.get_app_stat('owned_bgs', 'default')
        self.owned_bgs = set(owned_raw.split(',')) if owned_raw else set()
        self.owned_bgs.add('default')   # default is always owned

    def save(self):
        self.db.set_app_stat('coin_balance', str(self._coins))
        self.db.set_app_stat('last_coin_collect', self._last_collect_date)
        for item_id, qty in self._inventory.items():
            self.db.set_app_stat(f'inv_{item_id}', str(qty))
        self.db.set_app_stat('active_bg',  self.active_bg_id)
        self.db.set_app_stat('owned_bgs',  ','.join(sorted(self.owned_bgs)))

    # ── Coins ────────────────────────────────────────────────────────────────

    @property
    def coins(self) -> int:
        return self._coins

    def can_collect_today(self) -> bool:
        return self._last_collect_date != date.today().isoformat()

    def collect_daily_coins(self, trees) -> int:
        """Award 1 coin per alive graduated tree. Returns coins gained (0 if already collected)."""
        if not self.can_collect_today():
            return 0
        count = sum(
            1 for t in trees.values()
            if t.trees_grown > 0 and t.stage > 0 and t.health > 0
        )
        if count > 0:
            self._coins += count
            self._last_collect_date = date.today().isoformat()
            self.save()
        return count

    # ── Buying ───────────────────────────────────────────────────────────────

    def can_afford(self, item_id: str) -> bool:
        item = ITEM_MAP.get(item_id)
        return item is not None and self._coins >= item.price

    def owns_skin(self, skin_item_id: str) -> bool:
        return self._inventory.get(skin_item_id, 0) > 0

    def get_inventory(self, item_id: str) -> int:
        return self._inventory.get(item_id, 0)

    def buy(self, item_id: str) -> bool:
        """Purchase one unit. Returns True on success."""
        item = ITEM_MAP.get(item_id)
        if item is None or self._coins < item.price:
            return False
        # Skins: only buy once (inventory capped at 1)
        if item.category == 'skin' and self._inventory.get(item_id, 0) >= 1:
            return False
        # Consumables: capped at 99
        if item.category == 'consumable' and self._inventory.get(item_id, 0) >= 99:
            return False
        self._coins -= item.price
        self._inventory[item_id] = self._inventory.get(item_id, 0) + 1
        self.save()
        return True

    # ── Using ────────────────────────────────────────────────────────────────

    def use_consumable(self, item_id: str, key_name: Optional[str], forest) -> str:
        """
        Apply a consumable. Returns a human-readable result string.
        'ok' prefix means success; any other prefix is an error message.
        """
        qty = self._inventory.get(item_id, 0)
        if qty <= 0:
            return "库存不足"
        item = ITEM_MAP.get(item_id)
        if item is None or item.category != 'consumable':
            return "无效物品"

        if item_id == 'potion':
            if not key_name:
                return "请选择目标按键"
            tree = forest.trees.get(key_name)
            if tree is None or tree.stage == 0:
                return "该按键还未种植"
            if tree.health >= 1.0:
                return "该树木已满血，无需治疗"
            tree.health = 1.0
            self._inventory[item_id] -= 1
            self.save()
            forest._notify(f"💊 {tree.display_name} 已恢复满血！")
            return f"ok:{tree.display_name} 已恢复满血！"

        elif item_id == 'rain_card':
            from climate import ClimateState
            if forest.climate.state == ClimateState.RAIN:
                return "当前已在暴雨中"
            forest.climate._force_rain(600)
            self._inventory[item_id] -= 1
            self.save()
            forest._notify("🌧 暴雨调控卡生效！人工降雨10分钟")
            return "ok:人工暴雨已开启（10分钟）"

        elif item_id == 'drought_card':
            from climate import ClimateState
            if forest.climate.state != ClimateState.DROUGHT:
                return "当前没有干旱，无法使用"
            forest.climate._end_drought()
            self._inventory[item_id] -= 1
            self.save()
            forest._notify("☀ 驱旱卡生效！干旱已解除")
            return "ok:干旱已驱散！"

        elif item_id in ('xp_card_s', 'xp_card_m', 'xp_card_l'):
            if not key_name:
                return "请选择目标按键"
            tree = forest.trees.get(key_name)
            if tree is None or tree.stage == 0:
                return "该按键还未种植"
            xp_map = {'xp_card_s': 5_000, 'xp_card_m': 50_000, 'xp_card_l': 200_000}
            xp = xp_map[item_id]
            tree.experience += xp
            tree._check_level_up()
            self._inventory[item_id] -= 1
            self.save()
            forest._notify(f"⚡ {tree.display_name} 获得 {xp:,} 经验！")
            return f"ok:{tree.display_name} 获得 {xp:,} 经验！"

        return "使用失败"

    def apply_skin(self, skin_item_id: str, key_name: str, forest) -> str:
        """Apply a skin to a tree. Returns status string."""
        item = ITEM_MAP.get(skin_item_id)
        if item is None or item.category != 'skin':
            return "无效皮肤"
        if self._inventory.get(skin_item_id, 0) <= 0:
            return "尚未拥有该皮肤"
        tree = forest.trees.get(key_name)
        if tree is None:
            return "无效按键"
        tree.skin_id = item.skin_id
        forest._notify(f"🎨 {tree.display_name} 换上 {item.name}！")
        from renderer.tree_sprites import clear_cache
        clear_cache()
        return f"ok:{tree.display_name} 换上 {item.name}！"

    def apply_skin_by_palette_id(self, skin_id: str, key_name: str, forest) -> str:
        """Apply a skin using its palette id (e.g. 'autumn'). '' resets to default."""
        tree = forest.trees.get(key_name)
        if tree is None:
            return "无效按键"
        if skin_id == '':
            tree.skin_id = ''
            forest._notify(f"🎨 {tree.display_name} 换回默认外观")
            from renderer.tree_sprites import clear_cache
            clear_cache()
            return "ok:已换回默认外观"
        item_id = SKIN_ID_TO_ITEM_ID.get(skin_id)
        if item_id is None:
            return "无效皮肤"
        return self.apply_skin(item_id, key_name, forest)

    def apply_skin_all_trees(self, skin_id: str, forest) -> str:
        """Apply a skin to every planted tree. '' resets all to default."""
        if skin_id != '':
            item_id = SKIN_ID_TO_ITEM_ID.get(skin_id)
            if item_id is None:
                return "无效皮肤"
            if self._inventory.get(item_id, 0) <= 0:
                return "尚未拥有该皮肤"
        for tree in forest.trees.values():
            if tree.stage > 0:
                tree.skin_id = skin_id
        from renderer.tree_sprites import clear_cache
        clear_cache()
        name = SKIN_ID_TO_NAME.get(skin_id, skin_id or '默认绿')
        forest._notify(f"🎨 全部按键已换上 {name}！")
        return f"ok:全部换装 {name}！"

    def get_owned_skin_ids(self) -> List[str]:
        """Returns palette ids of all owned skins ('' = default, always included)."""
        result = ['']
        for item in SKIN_ITEMS:
            if self._inventory.get(item.id, 0) > 0:
                result.append(item.skin_id)
        return result

    # ── Background ───────────────────────────────────────────────────────────

    def get_theme(self) -> dict:
        return BG_THEMES.get(self.active_bg_id, BG_THEMES['default'])

    def buy_bg(self, bg_id: str) -> bool:
        item = next((b for b in BG_ITEMS if b.bg_id == bg_id), None)
        if item is None or bg_id in self.owned_bgs or self._coins < item.price:
            return False
        self._coins -= item.price
        self.owned_bgs.add(bg_id)
        self.save()
        return True

    def apply_bg(self, bg_id: str) -> bool:
        if bg_id not in self.owned_bgs:
            return False
        self.active_bg_id = bg_id
        self.save()
        return True
