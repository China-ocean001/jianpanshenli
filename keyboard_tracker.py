"""
Global keyboard listener (pynput) + thread-safe event queue.
Runs as a daemon thread; the main pygame thread drains the queue each frame.

pynput does NOT require elevation on Windows for user-space key monitoring.
It will miss keystrokes from processes running as Administrator.
"""

from __future__ import annotations
import queue
import threading
from typing import List

from pynput import keyboard


# Left/right variants that should collapse to a single logical key name
_NORMALIZE = {
    'ctrl_l':  'ctrl',
    'ctrl_r':  'ctrl_r',
    'shift_l': 'shift',
    'shift_r': 'shift_r',
    'alt_l':   'alt',
    'alt_r':   'alt_r',
    'alt_gr':  'alt_r',
    'cmd':     'win',
    'cmd_l':   'win',
    'cmd_r':   'win_r',
    'caps_lock': 'caps_lock',
    'num_lock': 'num_lock',
    'scroll_lock': 'scroll_lock',
}

# Map pynput Key attribute names to display-friendly canonical names
_KEY_NAME_MAP = {
    'backspace': 'backspace',
    'tab':       'tab',
    'enter':     'enter',
    'space':     'space',
    'esc':       'esc',
    'delete':    'delete',
    'insert':    'insert',
    'home':      'home',
    'end':       'end',
    'page_up':   'page_up',
    'page_down': 'page_down',
    'up':        'up',
    'down':      'down',
    'left':      'left',
    'right':     'right',
    'f1':  'f1',  'f2':  'f2',  'f3':  'f3',  'f4':  'f4',
    'f5':  'f5',  'f6':  'f6',  'f7':  'f7',  'f8':  'f8',
    'f9':  'f9',  'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
    'print_screen': 'print_screen',
    'pause':        'pause',
    'menu':         'menu',
}


# Windows Virtual Key codes for numpad keys (differ from regular keys)
_NUMPAD_VK: dict = {
    96:  'np_0',      97:  'np_1',      98:  'np_2',      99:  'np_3',
    100: 'np_4',      101: 'np_5',      102: 'np_6',      103: 'np_7',
    104: 'np_8',      105: 'np_9',
    106: 'np_multiply', 107: 'np_add',  109: 'np_subtract',
    110: 'np_decimal',  111: 'np_divide',
    144: 'num_lock',
    # vk=13 (Enter) could be numpad Enter but indistinguishable → maps to 'enter'
}


def to_canonical_name(key) -> str:
    """Convert a pynput key event to a canonical string key name."""
    # Check VK code first to distinguish numpad from number row
    vk = getattr(key, 'vk', None)
    if vk is not None and vk in _NUMPAD_VK:
        return _NUMPAD_VK[vk]

    if hasattr(key, 'char') and key.char is not None:
        return key.char.lower()

    raw = str(key).replace('Key.', '').lower()
    raw = _NORMALIZE.get(raw, raw)
    return _KEY_NAME_MAP.get(raw, raw)


class KeyboardTracker:
    """
    Starts a background daemon thread that listens for global key presses
    and pushes canonical key names onto a thread-safe queue.
    OS key-repeat is filtered: only the first physical press is counted.
    """

    def __init__(self, maxsize: int = 2000):
        self._queue: queue.Queue[str] = queue.Queue(maxsize=maxsize)
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._held_keys: set = set()

    def start(self):
        with self._lock:
            if self._listener is not None:
                return
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()

    def stop(self):
        with self._lock:
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
        self._held_keys.clear()

    def drain(self) -> List[str]:
        """Drain all pending key events. Call once per frame from main thread."""
        result: List[str] = []
        try:
            while True:
                result.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return result

    def _on_press(self, key):
        """Called on the pynput thread; enqueue only the first press (not repeats)."""
        try:
            name = to_canonical_name(key)
            if name in self._held_keys:
                return  # OS key-repeat – ignore
            self._held_keys.add(name)
            self._queue.put_nowait(name)
        except (queue.Full, Exception):
            pass

    def _on_release(self, key):
        """Called on the pynput thread; remove key from held set."""
        try:
            name = to_canonical_name(key)
            self._held_keys.discard(name)
        except Exception:
            pass
