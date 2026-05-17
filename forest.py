"""
Forest: manages all key trees, orchestrates climate, decay, and achievements.
"""

from __future__ import annotations
from collections import deque
from datetime import datetime, date
import time
from typing import Dict, List

from config import (
    ALL_KEYS,
    HIGH_FREQ_TOP20_MULT, HIGH_FREQ_TOP40_MULT,
    FREQ_RECALC_INTERVAL_S, HEALTH_CHECK_INTERVAL_S,
    HEALTH_SICK_THRESHOLD,
)
from key_tree import KeyTree
from climate import ClimateSystem, ClimateState
from database import Database
from achievements import AchievementSystem
from events import EventSystem

_ACH_CHECK_INTERVAL_S = 5.0


class Forest:
    def __init__(self, db: Database):
        self.db = db
        self.climate = ClimateSystem()
        self.trees: Dict[str, KeyTree] = db.load_all_trees()

        # Internal timers
        self._freq_timer = 0.0
        self._health_timer = 0.0
        self._ach_timer = 0.0
        self._today = date.today()

        # Sick-streak tracking
        self._sick_today: bool = False
        self.no_sick_streak: int = int(db.get_app_stat('no_sick_streak', '0'))

        # Recent events for HUD notifications (max 5)
        self.notifications: List[str] = []

        # Rolling 1-hour per-key press counter
        self._hour_queue: deque = deque()   # (monotonic_time, key_name)

        # Achievement system
        self.achievements = AchievementSystem(db)
        self.achievements.load()
        self.achievements.restore_side_effects(self)

        # Natural event system
        self.events = EventSystem()
        self.events.restore_state(db, self.trees)

        # Pre-compute freq multipliers from DB history
        self._recalculate_freq_multipliers()

    # ── Per-keypress ──────────────────────────────────────────────────────

    def process_keypress(self, key_name: str):
        self.climate.record_press()
        self._hour_queue.append((time.monotonic(), key_name))
        tree = self.trees.get(key_name)
        if tree is None:
            return
        event_mult = self.events.xp_mult(key_name, tree)
        levelled = tree.add_press(self.climate.xp_multiplier * event_mult)
        if tree.just_graduated:
            tree.just_graduated = False
            self._notify(f"{tree.display_name} 第{tree.trees_grown}棵参天大树长成！新苗已种下")
        elif levelled:
            self._notify(f"{tree.display_name} 升阶 → {tree.stage_name}!")
        self.events.on_keypress(key_name)
        # Check press-sensitive achievements immediately
        self.achievements.check_all(self)

    # ── Per-frame tick ────────────────────────────────────────────────────

    def tick(self, dt: float):
        # Midnight reset
        today = date.today()
        if today != self._today:
            # Update no-sick streak before resetting flag
            if self._sick_today:
                self.no_sick_streak = 0
            else:
                self.no_sick_streak += 1
            self.db.set_app_stat('no_sick_streak', str(self.no_sick_streak))
            self._sick_today = False
            for t in self.trees.values():
                t.today_presses = 0
            self._today = today

        # Climate state machine
        climate_event = self.climate.update(dt)
        if climate_event == 'rain_start':
            rain_mult = self.climate.xp_multiplier
            self._notify(f"开始暴雨！全局经验 ×{rain_mult:.0f}")
        elif climate_event == 'rain_end':
            self._notify("暴雨结束，阳光普照")
        elif climate_event == 'drought_start':
            self._notify("干旱来袭！经验大幅降低")
        elif climate_event == 'drought_end':
            self._notify("干旱解除，森林恢复生机")

        # Frequency-tier recalculation
        self._freq_timer += dt
        if self._freq_timer >= FREQ_RECALC_INTERVAL_S:
            self._recalculate_freq_multipliers()
            self._freq_timer = 0.0

        # Health decay check
        self._health_timer += dt
        if self._health_timer >= HEALTH_CHECK_INTERVAL_S:
            self._run_health_checks()
            self._health_timer = 0.0

        # Periodic achievement check
        self._ach_timer += dt
        if self._ach_timer >= _ACH_CHECK_INTERVAL_S:
            self.achievements.check_all(self)
            self._ach_timer = 0.0

        # Drain achievement unlocks into HUD notifications
        for ach_name in self.achievements.new_unlocks:
            self._notify(f"🏆 成就解锁: {ach_name}!")
        self.achievements.new_unlocks.clear()

        # Natural events tick + drain notifications
        self.events.tick(dt, self.trees)
        for msg in self.events.new_notifications:
            self._notify(msg)
        self.events.new_notifications.clear()

        # Update flash/level-up timers on trees
        for t in self.trees.values():
            if t.flash_timer > 0:
                t.flash_timer -= dt
            if t.level_up_timer > 0:
                t.level_up_timer -= dt

    # ── Stats for HUD ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        counts = {'healthy': 0, 'sick': 0, 'dead': 0, 'unplanted': 0}
        today_total = 0
        for t in self.trees.values():
            today_total += t.today_presses
            if t.stage == 0:
                counts['unplanted'] += 1
            elif t.is_dead:
                counts['dead'] += 1
            elif t.is_sick:
                counts['sick'] += 1
            else:
                counts['healthy'] += 1
        counts['today_total'] = today_total
        return counts

    # ── Internal helpers ──────────────────────────────────────────────────

    def _recalculate_freq_multipliers(self):
        weekly = self.db.load_weekly_counts()
        for key_name, tree in self.trees.items():
            weekly[key_name] = weekly.get(key_name, 0) + tree.today_presses

        if not weekly:
            return

        sorted_keys = sorted(weekly, key=lambda k: weekly[k], reverse=True)
        n = len(sorted_keys)
        top20 = max(1, int(n * 0.10))
        top40 = max(2, int(n * 0.20))

        for i, key_name in enumerate(sorted_keys):
            tree = self.trees.get(key_name)
            if tree is None:
                continue
            if tree.permanent_xp_boost:
                tree.xp_multiplier = max(1.5, tree.xp_multiplier)
                continue
            if i < top20:
                tree.xp_multiplier = HIGH_FREQ_TOP20_MULT
            elif i < top40:
                tree.xp_multiplier = HIGH_FREQ_TOP40_MULT
            else:
                tree.xp_multiplier = 1.0

    def _run_health_checks(self):
        now = datetime.now()
        for tree in self.trees.values():
            was_sick_before = tree.is_sick
            died = tree.update_health(now)
            if died:
                tree.was_dead = True
                self._notify(f"{tree.display_name} 树木枯死，重置为荒地")
                tree.reset()
            elif not was_sick_before and tree.is_sick:
                self._sick_today = True

    def _notify(self, msg: str):
        self.notifications.append(msg)
        if len(self.notifications) > 5:
            self.notifications.pop(0)

    def get_hour_presses(self) -> Dict[str, int]:
        """Return per-key press counts for the rolling last 60 minutes."""
        now = time.monotonic()
        cutoff = now - 3600.0
        while self._hour_queue and self._hour_queue[0][0] < cutoff:
            self._hour_queue.popleft()
        counts: Dict[str, int] = {}
        for _, k in self._hour_queue:
            counts[k] = counts.get(k, 0) + 1
        return counts

    def reload_after_clear(self):
        """Called after db.clear_all_data(): reset all in-memory state to fresh."""
        self.trees = self.db.load_all_trees()
        self.notifications.clear()
        self._sick_today = False
        self.no_sick_streak = 0
        self._freq_timer = 0.0
        self._health_timer = 0.0
        self._ach_timer = 0.0
        self._hour_queue.clear()
        # Reset climate counters (keep state machine running)
        self.climate.rain_keypress_total = 0
        self.climate.daily_rain_count = 0
        self.climate.rain_bonus_active = False
        # Reset achievement system
        for a in self.achievements._achs.values():
            a.unlocked = False
            a.unlocked_at = ""
        self.achievements.new_unlocks.clear()
        # Reset event system
        self.events.reset()
