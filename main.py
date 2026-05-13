"""
main.py
Entry point for the Quoridor game.
Run: python main.py
Press F11 to toggle fullscreen at any time.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pygame
from quoridor.renderer import WINDOW_W, WINDOW_H
from quoridor.menu import MenuScreen
from quoridor.controller import GameController

_fullscreen = False

def toggle_fullscreen(current_screen: pygame.Surface) -> pygame.Surface:
    global _fullscreen
    _fullscreen = not _fullscreen
    if _fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
    return screen


def main():
    pygame.init()
    pygame.display.set_caption("QUORIDOR — Strategy Board Game")

    try:
        icon = pygame.Surface((32, 32))
        icon.fill((8, 8, 14))
        pygame.draw.circle(icon, (255, 100, 80), (10, 16), 7)
        pygame.draw.circle(icon, (50, 210, 255), (22, 16), 7)
        pygame.display.set_icon(icon)
    except Exception:
        pass

    # Start with a resizable window (user can press F11 for fullscreen)
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)

    result = 'menu'
    last_config = None

    while result != 'quit':
        if result == 'menu':
            menu = MenuScreen(screen, toggle_fullscreen)
            config = menu.run()
            screen = menu.screen
            if config is None:
                break
            last_config = config
            result = 'game'
        elif result == 'game':
            ctrl = GameController(screen, last_config, toggle_fullscreen)
            result = ctrl.run()
            screen = ctrl.screen

    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
