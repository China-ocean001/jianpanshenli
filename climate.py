"""
Global climate state machine.
Tracks typing rate to trigger Rain or Drought modes.
All XP multipliers here are applied globally to every key.
"""

from __future__ import annotations
import time
from collections import deque
from enum import Enum
from typing import Deque, Optional

from config import (
    RAIN_RATE_THRESHOLD, RAIN_SUSTAIN_S, RAIN_DURATION_S, RAIN_XP_MULT,
    DROUGHT_IDLE_S, DROUGHT_RECOVER_RATE, DROUGHT_RECOVER_WINDOW_S, DROUGHT_XP_MULT,
)

_RAIN_BONUS_XP_MULT = 3.0   # XP multiplier after 暴雨甘霖 is unlocked


class ClimateState(Enum):
    NORMAL  = "normal"
    RAIN    = "rain"
    DROUGHT = "drought"


class ClimateSystem:
    def __init__(self):
        self.state = ClimateState.NORMAL
        self.xp_multiplier = 1.0

        # Rain detection: sliding window of keypress timestamps
        self._press_times: Deque[float] = deque()   # monotonic timestamps
        self._rain_sustain_timer = 0.0               # seconds above threshold
        self._rain_remaining = 0.0                   # seconds of rain left

        # Drought detection
        self._last_press_time: Optional[float] = None
        self._drought_recover_presses: Deque[float] = deque()  # for recovery rate

        # Public read: current intensity (0–1) for particle density
        self.rain_intensity = 0.0    # 0..1
        self.drought_intensity = 0.0 # 0..1

        # Achievement tracking
        self.rain_keypress_total: int = 0   # cumulative presses while raining
        self.daily_rain_count: int = 0      # rain events today (for 暴雨甘霖)
        self.rain_bonus_active: bool = False  # set True when 暴雨甘霖 unlocked
        self._today_str: str = ""

    # ── Called on every keypress ──────────────────────────────────────────

    def record_press(self):
        now = time.monotonic()
        self._press_times.append(now)
        self._last_press_time = now

        if self.state == ClimateState.RAIN:
            self.rain_keypress_total += 1

        # Keep only last 60 s in the rain window
        cutoff = now - 60.0
        while self._press_times and self._press_times[0] < cutoff:
            self._press_times.popleft()

        # Drought recovery tracking
        self._drought_recover_presses.append(now)
        cutoff_d = now - DROUGHT_RECOVER_WINDOW_S
        while self._drought_recover_presses and self._drought_recover_presses[0] < cutoff_d:
            self._drought_recover_presses.popleft()

    # ── Main update (called every frame) ─────────────────────────────────

    def update(self, dt: float) -> Optional[str]:
        """
        dt: seconds since last frame.
        Returns a string event name if state changed, else None:
          'rain_start', 'rain_end', 'drought_start', 'drought_end'
        """
        # Midnight reset for daily rain count
        from datetime import date as _date
        today = _date.today().strftime("%Y-%m-%d")
        if today != self._today_str:
            self._today_str = today
            self.daily_rain_count = 0

        now = time.monotonic()
        event = None

        if self.state == ClimateState.NORMAL:
            event = self._check_rain_trigger(dt, now)
            if event is None:
                event = self._check_drought_trigger(now)

        elif self.state == ClimateState.RAIN:
            self._rain_remaining -= dt
            self.rain_intensity = min(1.0, self._rain_remaining / 30.0)
            if self._rain_remaining <= 0:
                self._transition_to(ClimateState.NORMAL)
                event = 'rain_end'

        elif self.state == ClimateState.DROUGHT:
            self.drought_intensity = min(1.0, self._drought_elapsed(now) / 600.0)
            event = self._check_drought_recovery(now)

        return event

    # ── State transitions ─────────────────────────────────────────────────

    def _check_rain_trigger(self, dt: float, now: float) -> Optional[str]:
        current_rate = self._rate_in_window(60.0, now)
        if current_rate >= RAIN_RATE_THRESHOLD:
            self._rain_sustain_timer += dt
            if self._rain_sustain_timer >= RAIN_SUSTAIN_S:
                self._transition_to(ClimateState.RAIN)
                self._rain_remaining = RAIN_DURATION_S
                self._rain_sustain_timer = 0.0
                self.daily_rain_count += 1
                return 'rain_start'
        else:
            self._rain_sustain_timer = max(0.0, self._rain_sustain_timer - dt * 2)
        return None

    def _check_drought_trigger(self, now: float) -> Optional[str]:
        if self._last_press_time is None:
            return None
        idle = now - self._last_press_time
        if idle >= DROUGHT_IDLE_S:
            self._transition_to(ClimateState.DROUGHT)
            self._drought_start = self._last_press_time + DROUGHT_IDLE_S
            return 'drought_start'
        return None

    def _check_drought_recovery(self, now: float) -> Optional[str]:
        window = DROUGHT_RECOVER_WINDOW_S
        count = len(self._drought_recover_presses)
        # prune
        cutoff = now - window
        while self._drought_recover_presses and self._drought_recover_presses[0] < cutoff:
            self._drought_recover_presses.popleft()
        rate = len(self._drought_recover_presses) / window
        if rate >= DROUGHT_RECOVER_RATE:
            self._transition_to(ClimateState.NORMAL)
            return 'drought_end'
        return None

    def _transition_to(self, new_state: ClimateState):
        self.state = new_state
        if new_state == ClimateState.NORMAL:
            self.xp_multiplier = 1.0
            self.rain_intensity = 0.0
            self.drought_intensity = 0.0
        elif new_state == ClimateState.RAIN:
            self.xp_multiplier = _RAIN_BONUS_XP_MULT if self.rain_bonus_active else RAIN_XP_MULT
            self.rain_intensity = 1.0
        elif new_state == ClimateState.DROUGHT:
            self.xp_multiplier = DROUGHT_XP_MULT
            self.drought_intensity = 0.1

    def _rate_in_window(self, window_s: float, now: float) -> float:
        cutoff = now - window_s
        count = sum(1 for t in self._press_times if t >= cutoff)
        return count / window_s

    def _drought_elapsed(self, now: float) -> float:
        start = getattr(self, '_drought_start', now)
        return now - start

    def _force_rain(self, duration_s: float):
        """Immediately trigger rain for the given duration (rain card)."""
        self._transition_to(ClimateState.RAIN)
        self._rain_remaining = duration_s
        self.daily_rain_count += 1

    def _end_drought(self):
        """Immediately end drought (drought card)."""
        if self.state == ClimateState.DROUGHT:
            self._transition_to(ClimateState.NORMAL)

    @property
    def state_label(self) -> str:
        return {
            ClimateState.NORMAL:  '晴天',
            ClimateState.RAIN:    '暴雨',
            ClimateState.DROUGHT: '干旱',
        }[self.state]
