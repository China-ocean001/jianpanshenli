"""
KeyTree: per-key tree state and growth/decay logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config import (
    STAGE_XP_THRESHOLDS, GRADUATION_XP,
    BASE_XP_PER_PRESS,
    HEALTH_DECAY_START_H,
    HEALTH_DECAY_PER_H,
    HEALTH_SICK_THRESHOLD,
)

STAGE_NAMES = ['未种植', '种子', '小芽', '幼苗', '成树', '参天大树']
MAX_STAGE = 5


@dataclass
class KeyTree:
    key_name: str
    stage: int = 0
    experience: float = 0.0
    health: float = 1.0
    total_presses: int = 0
    last_used: Optional[datetime] = None
    custom_name: str = ""
    xp_multiplier: float = 1.0      # set by Forest based on 7-day frequency
    today_presses: int = 0          # reset at midnight by Forest
    trees_grown: int = 0            # how many times this key has been fully grown
    was_dead: bool = False          # ever died? (survives reset, used for 枯木逢春)
    permanent_xp_boost: bool = False  # permanent 1.5× from Ctrl守护者 achievement
    skin_id: str = ''               # active skin palette id ('' = default green)
    # Transient animation state (not persisted)
    flash_timer: float = field(default=0.0, repr=False)
    level_up_timer: float = field(default=0.0, repr=False)
    just_graduated: bool = field(default=False, repr=False)

    # ── Growth ─────────────────────────────────────────────────────────────

    def add_press(self, climate_mult: float) -> bool:
        """Record one keypress. Returns True if tree just levelled up."""
        if self.stage == 0:
            # First press on unplanted key → plant seed
            self.stage = 1
            self.experience = 0.0
            self.health = 1.0

        if self.health <= 0.0:
            # Dead tree still shows dead visual; ignore presses until reset
            return False

        total_mult = BASE_XP_PER_PRESS * self.xp_multiplier * climate_mult
        self.experience += total_mult
        self.total_presses += 1
        self.today_presses += 1
        self.last_used = datetime.now()

        # Restore health slightly on use (reward coming back to idle keys)
        self.health = min(1.0, self.health + 0.005)

        return self._check_level_up()

    def _check_level_up(self) -> bool:
        if self.stage == MAX_STAGE:
            # Graduation: return to unplanted, user must press again to start new tree
            if self.experience >= GRADUATION_XP:
                self.trees_grown += 1
                self.stage = 0
                self.experience = 0.0
                self.health = 1.0
                self.last_used = None
                self.level_up_timer = 2.0
                self.just_graduated = True
                return True
            return False
        threshold = STAGE_XP_THRESHOLDS[self.stage - 1]
        if self.experience >= threshold:
            self.experience -= threshold
            self.stage += 1
            self.level_up_timer = 2.0
            return True
        return False

    # ── Health / decay ─────────────────────────────────────────────────────

    def update_health(self, now: datetime) -> bool:
        """Decay health based on idle time. Returns True if tree just died."""
        if self.stage == 0 or self.health <= 0.0:
            return False
        if self.last_used is None:
            return False

        idle_hours = (now - self.last_used).total_seconds() / 3600.0
        if idle_hours <= HEALTH_DECAY_START_H:
            return False

        decay_hours = idle_hours - HEALTH_DECAY_START_H
        new_health = 1.0 - decay_hours * HEALTH_DECAY_PER_H
        self.health = max(0.0, new_health)

        if self.health <= 0.0:
            return True  # tree died
        return False

    def drain_experience(self, amount: float) -> bool:
        """Subtract experience. If it hits 0 while tree was alive, tree dies.
        Returns True if the tree just died."""
        if self.stage == 0 or self.health <= 0.0 or self.experience <= 0.0:
            return False
        self.experience = max(0.0, self.experience - amount)
        if self.experience <= 0.0:
            self.health = 0.0
            self.was_dead = True
            return True
        return False

    def reset(self):
        """Called after death: wipe growth progress, go back to unplanted.
        Preserves trees_grown, was_dead, permanent_xp_boost, and custom_name."""
        self.stage = 0
        self.experience = 0.0
        self.health = 1.0
        self.total_presses = 0
        self.today_presses = 0
        self.last_used = None
        self.xp_multiplier = 1.5 if self.permanent_xp_boost else 1.0

    # ── Computed properties ────────────────────────────────────────────────

    @property
    def stage_name(self) -> str:
        return STAGE_NAMES[self.stage]

    @property
    def is_sick(self) -> bool:
        return 0.0 < self.health < HEALTH_SICK_THRESHOLD

    @property
    def is_dead(self) -> bool:
        return self.stage > 0 and self.health <= 0.0

    @property
    def xp_for_next_stage(self) -> Optional[float]:
        if self.stage == 0:
            return None
        if self.stage == MAX_STAGE:
            return GRADUATION_XP   # show progress toward next graduation
        return STAGE_XP_THRESHOLDS[self.stage - 1]

    @property
    def display_name(self) -> str:
        return self.custom_name if self.custom_name else self.key_name.upper()

    def health_color_fraction(self) -> float:
        """0.0 = dead/critical, 1.0 = full health."""
        return max(0.0, min(1.0, self.health))
