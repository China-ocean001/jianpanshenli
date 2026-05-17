"""
Achievement system for Keyboard Forest.
18 achievements with optional side effects.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from forest import Forest

_LETTERS = list('abcdefghijklmnopqrstuvwxyz')
_DIGITS  = list('1234567890')


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    side_effect: str = ""   # 'ctrl_xp_boost' | 'rain_bonus' | ''
    unlocked: bool = False
    unlocked_at: str = ""   # 'YYYY-MM-DD HH:MM' when unlocked


ALL_ACHIEVEMENTS: List[Achievement] = [
    Achievement('sprout_first', '破土新生',   '任意一个按键从种子长成小芽'),
    Achievement('seedlings_5',  '林间幼苗',   '拥有5棵幼苗期及以上的按键树'),
    Achievement('tree_stage4',  '枝繁叶茂',   '任意一棵小树晋升成树期'),
    Achievement('tree_max',     '参天而立',   '养成第一棵满级参天大树'),
    Achievement('forest_10',    '森林初现',   '累计拥有10棵存活小树'),
    Achievement('space_max',    '空格灌溉王', '空格键小树达到参天大树'),
    Achievement('enter_100k',   '回车摆渡人', '回车键累计敲击破10万次'),
    Achievement('ctrl_5k_7d',   'Ctrl守护者', 'Ctrl键七天内使用5000次（永久1.5倍经验加成）',
                side_effect='ctrl_xp_boost'),
    Achievement('digits_alive', '数字林场主', '0-9十个数字键全部养成存活小树'),
    Achievement('letters_max',  '字母大师',   '26个字母键全都拥有一棵满级树'),
    Achievement('all_max',      '冷门护林员', '所有按键都有一棵满级树'),
    Achievement('dead_reborn',  '枯木逢春',   '将曾经枯死的按键重新养成至满级'),
    Achievement('no_sick_30d',  '不弃一树',   '连续30天无任何小树进入枯萎状态'),
    Achievement('rain_10_day',  '暴雨甘霖',   '单日触发暴雨10次（雨天全员经验加成增强）',
                side_effect='rain_bonus'),
    Achievement('rain_100k',    '林间听雨',   '暴雨中累计打字十万次'),
    Achievement('key_10k',      '万击树人',   '单个按键累计敲击破10000次'),
    Achievement('daily_50k',    '敲击狂人',   '单日全键盘总敲击突破50000次'),
    Achievement('all_named',    '按键收藏家', '全键盘所有按键都拥有专属命名'),
]


class AchievementSystem:
    def __init__(self, db):
        self.db = db
        self._achs: dict = {
            a.id: Achievement(a.id, a.name, a.description, a.side_effect)
            for a in ALL_ACHIEVEMENTS
        }
        self.new_unlocks: List[str] = []   # freshly unlocked names; drained by Forest

    def load(self):
        for ach_id, unlocked_at in self.db.load_achievements():
            if ach_id in self._achs:
                a = self._achs[ach_id]
                a.unlocked = True
                a.unlocked_at = unlocked_at

    def restore_side_effects(self, forest: 'Forest'):
        """Re-apply side effects for already-unlocked achievements on startup."""
        for a in self._achs.values():
            if a.unlocked and a.side_effect:
                self._apply_side_effect(a, forest)

    @property
    def achievements(self) -> List[Achievement]:
        return [self._achs[a.id] for a in ALL_ACHIEVEMENTS]

    def check_all(self, forest: 'Forest'):
        for a in list(self._achs.values()):
            if not a.unlocked and self._check_one(a.id, forest):
                self._unlock(a, forest)

    # ── Per-achievement conditions ─────────────────────────────────────────

    def _check_one(self, aid: str, forest: 'Forest') -> bool:
        trees = forest.trees
        climate = forest.climate

        if aid == 'sprout_first':
            return any(t.stage >= 2 for t in trees.values())

        if aid == 'seedlings_5':
            return sum(1 for t in trees.values() if t.stage >= 2) >= 5

        if aid == 'tree_stage4':
            return any(t.stage >= 4 for t in trees.values())

        if aid == 'tree_max':
            return any(t.stage == 5 for t in trees.values())

        if aid == 'forest_10':
            return sum(1 for t in trees.values() if t.stage > 0 and t.health > 0) >= 10

        if aid == 'space_max':
            t = trees.get('space')
            return t is not None and t.stage == 5

        if aid == 'enter_100k':
            t = trees.get('enter')
            return t is not None and t.total_presses >= 100_000

        if aid == 'ctrl_5k_7d':
            try:
                total = sum(
                    c for _, c in self.db.get_key_period_stats('ctrl', 7)
                ) + sum(
                    c for _, c in self.db.get_key_period_stats('ctrl_r', 7)
                )
                ct = trees.get('ctrl')
                cr = trees.get('ctrl_r')
                total += (ct.today_presses if ct else 0) + (cr.today_presses if cr else 0)
                return total >= 5_000
            except Exception:
                return False

        if aid == 'digits_alive':
            return all(
                trees.get(d) is not None and trees[d].stage > 0 and trees[d].health > 0
                for d in _DIGITS
            )

        if aid == 'letters_max':
            return all(
                trees.get(c) is not None and trees[c].stage == 5
                for c in _LETTERS
            )

        if aid == 'all_max':
            return all(t.stage == 5 for t in trees.values())

        if aid == 'dead_reborn':
            return any(t.was_dead and t.stage == 5 for t in trees.values())

        if aid == 'no_sick_30d':
            return forest.no_sick_streak >= 30

        if aid == 'rain_10_day':
            return climate.daily_rain_count >= 10

        if aid == 'rain_100k':
            return climate.rain_keypress_total >= 100_000

        if aid == 'key_10k':
            return any(t.total_presses >= 10_000 for t in trees.values())

        if aid == 'daily_50k':
            return sum(t.today_presses for t in trees.values()) >= 50_000

        if aid == 'all_named':
            return all(t.custom_name != "" for t in trees.values())

        return False

    # ── Unlock helpers ─────────────────────────────────────────────────────

    def _unlock(self, a: Achievement, forest: 'Forest'):
        a.unlocked = True
        a.unlocked_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db.save_achievement(a.id, a.unlocked_at)
        self.new_unlocks.append(a.name)
        self._apply_side_effect(a, forest)

    def _apply_side_effect(self, a: Achievement, forest: 'Forest'):
        if a.side_effect == 'ctrl_xp_boost':
            for key in ('ctrl', 'ctrl_r'):
                t = forest.trees.get(key)
                if t:
                    t.permanent_xp_boost = True
                    t.xp_multiplier = max(t.xp_multiplier, 1.5)
        elif a.side_effect == 'rain_bonus':
            forest.climate.rain_bonus_active = True
