"""
Natural event system: four random events that spice up tree cultivation.
Events are transient (not persisted to DB); they restart fresh each session.
"""

from __future__ import annotations
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Set

# ── Key groups ────────────────────────────────────────────────────────────────
LETTER_KEYS: Set[str] = set('abcdefghijklmnopqrstuvwxyz')

MODIFIER_KEYS: Set[str] = {
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
    'ctrl', 'ctrl_r', 'shift', 'shift_r', 'alt', 'alt_r',
    'win', 'win_r', 'tab', 'caps_lock', 'backspace', 'enter', 'esc', 'menu',
}

# ── Event metadata ────────────────────────────────────────────────────────────
EVENT_META: Dict[str, dict] = {
    'breeze': {
        'name':     '清风拂林',
        'icon':     '🌿',
        'desc':     '健康树木经验 ×1.3，亚健康树木缓慢恢复血量',
        'duration': 3600,
        'color':    (75, 185, 105),
    },
    'pest': {
        'name':     '虫灾侵袭',
        'icon':     '🐛',
        'desc':     '部分按键受虫害：健康受损、经验减少，快多敲击这些键驱虫！',
        'duration': 3600,   # max 1 hour; ends early when all pests cleared
        'color':    (200, 118, 42),
    },
    'morning': {
        'name':     '晨光普照',
        'icon':     '🌅',
        'desc':     '5-9时专属：全部字母键经验 ×2.5，早起打字效率大增',
        'duration': 1800,
        'color':    (248, 192, 72),
    },
    'starnight': {
        'name':     '星夜滋养',
        'icon':     '🌙',
        'desc':     '深夜专属：功能键/组合键经验 ×2.5，熬夜码字专属福利',
        'duration': 2700,
        'color':    (100, 112, 215),
    },
}

# Maximum times each event can fire per natural day
_DAILY_CAPS: Dict[str, int] = {
    'breeze':    2,
    'pest':      1,
    'morning':   1,
    'starnight': 1,
}

# Pest parameters
_PEST_KEYS_COUNT = 6    # how many keys get infested
_PEST_HITS_NEEDED = 50  # presses to clear each affected key

# How often to roll for a new event (seconds)
_CHECK_INTERVAL = 300.0


class EventSystem:
    def __init__(self):
        self.active_event: Optional[str] = None
        self._end_time:    float = 0.0         # monotonic

        # Stagger the first check so it doesn't always fire at startup
        self._check_timer: float = random.uniform(60, _CHECK_INTERVAL)

        self._today_str:    str = ''
        self._daily_counts: Dict[str, int] = {k: 0 for k in EVENT_META}

        # Pest state: key_name → hits remaining before cleared
        self._pest_hits: Dict[str, int] = {}

        # Pest XP drain: 5 XP/minute from each infested key
        self._pest_drain_timer: float = 0.0

        # Cumulative probability penalty for pest event (cleared daily)
        self._pest_prob_penalty: float = 0.0

        # Notifications to drain into forest.notifications on next tick
        self.new_notifications: List[str] = []

    # ── Public read-only API ──────────────────────────────────────────────────

    def xp_mult(self, key_name: str, tree) -> float:
        """Per-key event XP multiplier (1.0 = no change)."""
        ev = self.active_event
        if ev == 'breeze':
            return 1.3 if (tree.stage > 0 and tree.health > 0.5) else 1.0
        if ev == 'pest':
            return 0.55 if key_name in self._pest_hits else 1.0
        if ev == 'morning':
            return 2.5 if key_name in LETTER_KEYS else 1.0
        if ev == 'starnight':
            return 2.5 if key_name in MODIFIER_KEYS else 1.0
        return 1.0

    def pest_affected_keys(self) -> Set[str]:
        if self.active_event == 'pest':
            return set(self._pest_hits.keys())
        return set()

    def remaining_seconds(self) -> float:
        if self.active_event is None:
            return 0.0
        return max(0.0, self._end_time - time.monotonic())

    def event_label(self) -> str:
        if not self.active_event:
            return ''
        meta = EVENT_META[self.active_event]
        rem = int(self.remaining_seconds())
        if self.active_event == 'pest':
            n = len(self._pest_hits)
            return f"{meta['icon']} {meta['name']}  {n}键受害  {rem // 60}:{rem % 60:02d}"
        return f"{meta['icon']} {meta['name']}  {rem // 60}:{rem % 60:02d}"

    def event_color(self) -> tuple:
        if self.active_event:
            return EVENT_META[self.active_event]['color']
        return (80, 110, 70)

    def get_pest_info(self, key_name: str) -> Optional[dict]:
        """Returns pest status for a specific key, or None if not infested."""
        if self.active_event != 'pest' or key_name not in self._pest_hits:
            return None
        return {
            'hits_remaining': self._pest_hits[key_name],
            'hits_total':     _PEST_HITS_NEEDED,
            'time_remaining': self.remaining_seconds(),
            'next_drain_in':  max(0.0, 60.0 - self._pest_drain_timer),
        }

    # ── Called from Forest ────────────────────────────────────────────────────

    def on_keypress(self, key_name: str):
        """Handles pest-driving mechanic on each relevant keypress."""
        if self.active_event != 'pest':
            return
        if key_name not in self._pest_hits:
            return
        self._pest_hits[key_name] -= 1
        if self._pest_hits[key_name] <= 0:
            del self._pest_hits[key_name]
            self.new_notifications.append(
                f"🌱 {key_name.upper()} 的虫害已驱除！"
            )
        if not self._pest_hits:
            self.active_event = None
            self._pest_drain_timer = 0.0
            self.new_notifications.append("🎉 虫灾已被完全驱除！森林恢复生机")

    def tick(self, dt: float, trees: dict):
        """Called every frame from Forest.tick()."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Midnight reset of daily counters
        if today_str != self._today_str:
            self._today_str = today_str
            self._daily_counts = {k: 0 for k in EVENT_META}
            self._pest_prob_penalty = 0.0

        # Expire active event (pest expires when all cleared or timeout)
        if self.active_event and time.monotonic() >= self._end_time:
            self._expire_event(trees)

        # Pest XP drain: 5 XP per minute from each infested key
        if self.active_event == 'pest' and self._pest_hits:
            self._pest_drain_timer += dt
            if self._pest_drain_timer >= 60.0:
                self._pest_drain_timer -= 60.0
                for k in list(self._pest_hits.keys()):
                    tree = trees.get(k)
                    if tree is not None:
                        if tree.drain_experience(5):
                            self.new_notifications.append(
                                f"💀 {tree.display_name} 经验耗尽，已枯死！"
                            )

        # Breeze: slowly heal sick trees
        if self.active_event == 'breeze':
            for tree in trees.values():
                if tree.stage > 0 and 0.0 < tree.health < 0.5:
                    tree.health = min(0.5, tree.health + 0.00015 * dt * 60)

        # Try triggering a new event
        if self.active_event is None:
            self._check_timer += dt
            if self._check_timer >= _CHECK_INTERVAL:
                self._check_timer = 0.0
                self._try_trigger(now, trees)

    def reset(self):
        """Called on data clear."""
        self.active_event = None
        self._pest_hits.clear()
        self._pest_drain_timer = 0.0
        self._pest_prob_penalty = 0.0
        self._check_timer = random.uniform(60, _CHECK_INTERVAL)
        self._daily_counts = {k: 0 for k in EVENT_META}
        self.new_notifications.clear()

    # ── Persistence (save / restore across sessions) ──────────────────────────

    def save_state(self, db) -> None:
        """Persist active event and daily counts to app_stats."""
        db.set_app_stat('event_active', self.active_event or '')
        # Store real wall-clock deadline so we can reconstruct after restart
        wall_end = (time.time() + self.remaining_seconds()) if self.active_event else 0.0
        db.set_app_stat('event_end_wall', str(wall_end))
        db.set_app_stat('event_pest_hits',    json.dumps(self._pest_hits))
        db.set_app_stat('event_pest_penalty', str(self._pest_prob_penalty))
        today_str = datetime.now().strftime("%Y-%m-%d")
        db.set_app_stat('event_today_str',    today_str)
        db.set_app_stat('event_daily_counts', json.dumps(self._daily_counts))

    def restore_state(self, db, trees: dict) -> None:
        """Restore event state on startup; apply missed-expiry penalties for pest."""
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Always restore daily counts if they're from today
        saved_today = db.get_app_stat('event_today_str', '')
        if saved_today == today_str:
            try:
                saved_counts = json.loads(db.get_app_stat('event_daily_counts', '{}'))
                for k in self._daily_counts:
                    if k in saved_counts:
                        self._daily_counts[k] = int(saved_counts[k])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            try:
                self._pest_prob_penalty = float(db.get_app_stat('event_pest_penalty', '0'))
            except ValueError:
                pass
        self._today_str = today_str

        # Restore active event
        active = db.get_app_stat('event_active', '')
        if not active or active not in EVENT_META:
            return

        try:
            wall_end = float(db.get_app_stat('event_end_wall', '0'))
        except ValueError:
            return

        remaining = wall_end - time.time()

        if remaining > 0:
            # Event is still running — resume it
            self.active_event = active
            self._end_time = time.monotonic() + remaining
            if active == 'pest':
                try:
                    raw = db.get_app_stat('event_pest_hits', '{}')
                    self._pest_hits = {k: int(v) for k, v in json.loads(raw).items()}
                except (json.JSONDecodeError, TypeError, ValueError):
                    self._pest_hits = {}
                if not self._pest_hits:
                    # Pest was actually cleared; don't resume
                    self.active_event = None
                else:
                    self.new_notifications.append(
                        f"🐛 虫灾继续！还剩 {int(remaining//60)}分{int(remaining%60)}秒"
                    )
            else:
                meta = EVENT_META[active]
                self.new_notifications.append(
                    f"{meta['icon']} {meta['name']} 继续！还剩 {int(remaining//60)}分{int(remaining%60)}秒"
                )
        else:
            # Event expired while the app was closed
            if active == 'pest':
                try:
                    raw = db.get_app_stat('event_pest_hits', '{}')
                    pest_hits = {k: int(v) for k, v in json.loads(raw).items()}
                except (json.JSONDecodeError, TypeError, ValueError):
                    pest_hits = {}
                if pest_hits:
                    for k in pest_hits:
                        tree = trees.get(k)
                        if tree is not None:
                            penalty = random.randint(50, 1000)
                            tree.experience = max(0, tree.experience - penalty)
                    self._pest_prob_penalty = min(0.12, self._pest_prob_penalty + 0.03)
                    self.new_notifications.append(
                        f"⚠ 虫灾在关机期间结束，{len(pest_hits)}株树木未驱虫，遭受经验惩罚"
                    )

    # ── Internal trigger logic ────────────────────────────────────────────────

    def _try_trigger(self, now: datetime, trees: dict):
        h, m = now.hour, now.minute
        candidates: List[str] = []

        # Morning sunlight: 5am–9am
        if 5 <= h < 9 and self._daily_counts['morning'] < _DAILY_CAPS['morning']:
            if random.random() < 0.45:
                candidates.append('morning')

        # Starnight: 23:30–03:00
        in_night = (h == 23 and m >= 30) or (0 <= h < 3)
        if in_night and self._daily_counts['starnight'] < _DAILY_CAPS['starnight']:
            if random.random() < 0.55:
                candidates.append('starnight')

        # Gentle breeze: any time
        if self._daily_counts['breeze'] < _DAILY_CAPS['breeze']:
            if random.random() < 0.25:
                candidates.append('breeze')

        # Pest: any time, only if there are enough healthy trees to infest
        alive = [k for k, t in trees.items()
                 if t.stage > 0 and t.health > 0.3 and not t.is_dead]
        pest_prob = max(0.04, 0.18 - self._pest_prob_penalty)
        if len(alive) >= 3 and self._daily_counts['pest'] < _DAILY_CAPS['pest']:
            if random.random() < pest_prob:
                candidates.append('pest')

        if not candidates:
            return

        # Time-specific events get priority; otherwise random pick
        time_specific = [e for e in candidates if e in ('morning', 'starnight')]
        chosen = random.choice(time_specific) if time_specific else random.choice(candidates)
        self._start_event(chosen, trees)

    def _start_event(self, event_id: str, trees: dict):
        meta = EVENT_META[event_id]
        self.active_event = event_id
        self._end_time    = time.monotonic() + meta['duration']
        self._daily_counts[event_id] += 1

        if event_id == 'pest':
            alive = [k for k, t in trees.items()
                     if t.stage > 0 and t.health > 0.3 and not t.is_dead]
            n      = min(_PEST_KEYS_COUNT, len(alive))
            chosen = random.sample(alive, n)
            self._pest_hits = {k: _PEST_HITS_NEEDED for k in chosen}
            # Apply immediate health damage
            for k in chosen:
                trees[k].health = max(0.02, trees[k].health - random.uniform(0.12, 0.22))
            key_list  = '、'.join(k.upper() for k in chosen[:4])
            more_hint = f' 等{len(chosen)}键' if len(chosen) > 4 else ''
            self.new_notifications.append(
                f"🐛 虫灾侵袭！{key_list}{more_hint} 受害，快敲击这些键驱虫！"
            )
        else:
            self.new_notifications.append(
                f"{meta['icon']} {meta['name']}！{meta['desc']}"
            )

    def _expire_event(self, trees: dict):
        if self.active_event == 'pest' and self._pest_hits:
            n = len(self._pest_hits)
            # Penalty XP deduction: 50–1000 per surviving infested key
            for k in list(self._pest_hits.keys()):
                tree = trees.get(k)
                if tree is not None:
                    penalty = random.randint(50, 1000)
                    tree.experience = max(0, tree.experience - penalty)
            self._pest_prob_penalty = min(0.12, self._pest_prob_penalty + 0.03)
            self.new_notifications.append(
                f"⚠ 虫灾结束，{n}株树木未能驱虫，遭受额外经验惩罚"
            )
        elif self.active_event:
            meta = EVENT_META[self.active_event]
            self.new_notifications.append(
                f"{meta['icon']} {meta['name']} 结束"
            )
        self.active_event = None
        self._pest_hits.clear()
        self._pest_drain_timer = 0.0
