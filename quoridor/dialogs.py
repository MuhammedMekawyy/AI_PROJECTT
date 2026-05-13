"""
quoridor/dialogs.py
In-game modal dialogs: save slot picker, load slot picker, confirm dialog.
"""
from __future__ import annotations
import pygame
from typing import Optional
from quoridor.renderer import (WINDOW_W, WINDOW_H, C_BG, C_PANEL, C_BORDER,
                                C_TEXT, C_TEXT2, C_ACCENT, _font)
from quoridor.save_manager import all_slots, slot_info


def _draw_backdrop(screen: pygame.Surface):
    s = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
    s.fill((0, 0, 0, 180))
    screen.blit(s, (0, 0))


def _modal_box(screen: pygame.Surface, title: str, lines: list,
               buttons: list) -> Optional[int]:
    """
    Render a blocking modal dialog.
    buttons: list of (label, value) tuples.
    Returns chosen value or None if closed.
    """
    W, H = 420, 100 + len(lines)*22 + 60
    mx = WINDOW_W//2 - W//2
    my = WINDOW_H//2 - H//2
    box = pygame.Rect(mx, my, W, H)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                px, py = event.pos
                # Check buttons
                for i, (lbl, val) in enumerate(buttons):
                    bw = 120; bx = box.x + 20 + i*(bw+10)
                    by = box.y + H - 54
                    r = pygame.Rect(bx, by, bw, 38)
                    if r.collidepoint(px, py):
                        return val

        # Draw
        _draw_backdrop(screen)
        pygame.draw.rect(screen, C_PANEL, box, border_radius=10)
        pygame.draw.rect(screen, C_ACCENT, box, width=1, border_radius=10)

        t = _font(18, True).render(title, True, C_TEXT)
        screen.blit(t, (box.x + 20, box.y + 16))
        for i, line in enumerate(lines):
            l = _font(13).render(line, True, C_TEXT2)
            screen.blit(l, (box.x + 20, box.y + 48 + i*22))

        for i, (lbl, val) in enumerate(buttons):
            bw = 120; bx = box.x + 20 + i*(bw+10)
            by = box.y + H - 54
            r = pygame.Rect(bx, by, bw, 38)
            mp = pygame.mouse.get_pos()
            bg = (70, 60, 140) if r.collidepoint(mp) else (40, 38, 70)
            pygame.draw.rect(screen, bg, r, border_radius=7)
            pygame.draw.rect(screen, C_BORDER, r, width=1, border_radius=7)
            bl = _font(14).render(lbl, True, C_TEXT)
            screen.blit(bl, (r.centerx - bl.get_width()//2,
                              r.centery - bl.get_height()//2))

        pygame.display.flip()
        pygame.time.Clock().tick(60)


def show_save_dialog(screen: pygame.Surface, state) -> Optional[int]:
    """Show save-slot picker. Returns chosen slot index or None."""
    slots = all_slots()
    lines = []
    for i in range(3):
        info = slots[i]
        if info:
            lines.append(f"Slot {i+1}: Move #{info['move_count']}  ({info['saved_at'][:16]})")
        else:
            lines.append(f"Slot {i+1}: Empty")
    lines.append("")
    lines.append("Click a slot button to save.")
    buttons = [(f"Slot {i+1}", i) for i in range(3)] + [("Cancel", None)]
    return _modal_box(screen, "Save Game", lines, buttons)


def show_load_dialog(screen: pygame.Surface) -> Optional[int]:
    """Show load-slot picker. Returns chosen slot index or None."""
    slots = all_slots()
    lines = []
    has_any = False
    for i in range(3):
        info = slots[i]
        if info:
            lines.append(f"Slot {i+1}: Move #{info['move_count']}  ({info['saved_at'][:16]})")
            has_any = True
        else:
            lines.append(f"Slot {i+1}: Empty")
    if not has_any:
        lines.append("")
        lines.append("No saves found.")
    buttons = [(f"Slot {i+1}", i) for i in range(3)] + [("Cancel", None)]
    return _modal_box(screen, "Load Game", lines, buttons)


def show_confirm(screen: pygame.Surface, title: str, message: str) -> bool:
    result = _modal_box(screen, title, [message], [("Yes", True), ("No", False)])
    return result is True
