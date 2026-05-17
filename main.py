"""
键盘森林 – Entry point.
"""

import sys
import pygame

from config import WINDOW_W, WINDOW_H, WINDOW_TITLE, TARGET_FPS, DB_PATH, SAVE_INTERVAL_S
from database import Database
from forest import Forest
from keyboard_tracker import KeyboardTracker
from renderer.weather_particles import WeatherParticles
from renderer.forest_view import ForestView
from renderer.detail_view import DetailView
from renderer.stats_view import StatsView
from renderer.grove_view import GroveView
from renderer.achievement_view import AchievementView
from renderer.shop_view import ShopView
from renderer.hud import HUD
from renderer.clear_dialog import ClearDataDialog
from shop import ShopSystem


def _load_fonts():
    candidates = ["Microsoft YaHei", "SimHei", "Consolas", "Arial"]
    font_med = font_sm = None
    for name in candidates:
        try:
            if font_med is None:
                font_med = pygame.font.SysFont(name, 17)
            if font_sm is None:
                font_sm = pygame.font.SysFont(name, 13)
            if font_med and font_sm:
                break
        except Exception:
            continue
    font_med = font_med or pygame.font.Font(None, 20)
    font_sm  = font_sm  or pygame.font.Font(None, 15)
    return font_med, font_sm


def _try_create_shortcut():
    """Create desktop shortcut on first run; silently ignore failures."""
    try:
        from create_shortcut import create_desktop_shortcut
        create_desktop_shortcut()
    except Exception:
        pass


def main():
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()

    font_med, font_sm = _load_fonts()

    db      = Database(DB_PATH)
    forest  = Forest(db)
    tracker = KeyboardTracker()
    tracker.start()

    shop         = ShopSystem(db)
    weather      = WeatherParticles()
    forest_view  = ForestView(forest, font_sm, shop)
    detail_view  = DetailView(forest, font_med, font_sm, shop)
    stats_view   = StatsView(forest, db, font_med, font_sm)
    grove_view   = GroveView(forest, font_med, font_sm)
    ach_view     = AchievementView(forest, font_med, font_sm)
    shop_view    = ShopView(forest, shop, font_med, font_sm)
    hud          = HUD(forest, shop, font_med, font_sm)
    clear_dialog = ClearDataDialog(font_med, font_sm)

    active_view = 'forest'   # 'forest' | 'stats' | 'grove' | 'achievement' | 'shop'
    save_timer  = 0.0
    running     = True

    _try_create_shortcut()

    while running:
        dt = min(clock.tick(TARGET_FPS) / 1000.0, 0.1)

        # ── Events ────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Clear dialog takes priority over all other input when active
            elif clear_dialog.active:
                action = clear_dialog.handle_event(event)
                if action == 'clear':
                    db.clear_all_data()
                    forest.reload_after_clear()
                    shop.load()
                    forest._notify("所有数据已清除，重新开始！")
                # any action (clear or cancel) closes the dialog; no other handlers called
                continue

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if active_view != 'forest':
                        active_view = 'forest'
                    elif detail_view.is_open:
                        detail_view.close()
                    else:
                        running = False
                elif active_view == 'forest':
                    detail_view.handle_event(event)

            elif event.type == pygame.MOUSEMOTION:
                if active_view == 'forest':
                    forest_view.handle_mouse_move(event.pos)
                elif active_view == 'stats':
                    stats_view.handle_event(event)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                tab = hud.hit_test_tab(event.pos)
                if tab:
                    active_view = tab
                elif active_view == 'forest':
                    if not detail_view.handle_event(event):
                        key_name = forest_view.key_at(event.pos)
                        if key_name:
                            detail_view.toggle(key_name)
                elif active_view == 'stats':
                    stats_view.handle_event(event)
                elif active_view == 'grove':
                    grove_view.handle_event(event)
                elif active_view == 'shop':
                    shop_view.handle_event(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Scroll events (buttons 4/5) reach non-left-click branch
                if active_view == 'stats':
                    stats_view.handle_event(event)
                elif active_view == 'grove':
                    grove_view.handle_event(event)
                elif active_view == 'achievement':
                    ach_view.handle_event(event)

            elif event.type in (pygame.MOUSEBUTTONUP,):
                if active_view == 'forest':
                    detail_view.handle_event(event)

            else:
                if active_view == 'forest':
                    detail_view.handle_event(event)
                elif active_view == 'stats':
                    stats_view.handle_event(event)

        # Open clear dialog if stats view requested it
        if stats_view.requested_clear:
            stats_view.requested_clear = False
            clear_dialog.open()

        # ── Keyboard presses (pynput global) ──────────────────────────────
        if clear_dialog.active or detail_view._editing_name:
            tracker.drain()   # drain without processing
        else:
            for key_name in tracker.drain():
                forest.process_keypress(key_name)
                if active_view == 'forest':
                    forest_view.flash_key(key_name)

        # ── Logic update ──────────────────────────────────────────────────
        forest.tick(dt)
        if active_view == 'forest':
            forest_view.update(dt)
            detail_view.update(dt)
        elif active_view == 'stats':
            stats_view.update(dt)
        elif active_view == 'grove':
            grove_view.update(dt)
        elif active_view == 'achievement':
            ach_view.update(dt)
        elif active_view == 'shop':
            shop_view.update(dt)
        hud.update(dt)

        # ── Auto-save ─────────────────────────────────────────────────────
        save_timer += dt
        if save_timer >= SAVE_INTERVAL_S:
            db.save_all_trees(forest.trees)
            save_timer = 0.0

        # ── Render ────────────────────────────────────────────────────────
        if active_view == 'forest':
            weather.update_and_draw(screen, dt, forest.climate.state,
                                    max(forest.climate.rain_intensity,
                                        forest.climate.drought_intensity),
                                    theme=shop.get_theme())
            forest_view.draw(screen)
            detail_view.draw(screen)
        elif active_view == 'stats':
            stats_view.draw(screen)
        elif active_view == 'grove':
            grove_view.draw(screen)
        elif active_view == 'achievement':
            ach_view.draw(screen)
        elif active_view == 'shop':
            shop_view.draw(screen)

        hud.draw(screen, active_view)
        clear_dialog.draw(screen)    # overlays everything
        pygame.display.flip()

    # ── Shutdown ──────────────────────────────────────────────────────────
    tracker.stop()
    db.save_all_trees(forest.trees)
    forest.events.save_state(db)
    db.close()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
