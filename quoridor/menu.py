"""
quoridor/menu.py
Main-menu — fully dynamic layout, scales to any window/fullscreen size.
"""
from __future__ import annotations
import pygame
import math
from typing import Optional
from quoridor.renderer import (WINDOW_W, WINDOW_H, C_BG, C_PANEL, C_BORDER, C_BORDER2,
                                C_TEXT, C_TEXT2, C_TEXT3, C_ACCENT, C_ACCENT2, C_ACCENT3,
                                C_WALL, PLAYER_COLORS_LIST, _font, _sfont,
                                _draw_rounded_rect_with_border)
from quoridor.save_manager import all_slots


class Button:
    def __init__(self, text: str, value=None, color=None, active_color=None, accent=None):
        self.rect = pygame.Rect(0, 0, 10, 10)   # set by layout
        self.text = text
        self.value = value
        self._color = color or (22, 20, 38)
        self._active_color = active_color or (50, 40, 110)
        self._accent = accent or C_ACCENT
        self.is_active = False
        self.hovered = False
        self._hover_t = 0.0

    def draw(self, surf: pygame.Surface):
        self._hover_t += (1.0 if self.hovered else -1.0) * 0.15
        self._hover_t = max(0.0, min(1.0, self._hover_t))
        t = self._hover_t

        if self.is_active:
            bg = tuple(int(a + (b - a) * t) for a, b in
                       zip(self._active_color, tuple(min(255, c + 20) for c in self._active_color)))
            border = self._accent
            bw = 2
        else:
            bg_base = self._color
            bg_hov = tuple(min(255, c + 12) for c in self._color)
            bg = tuple(int(a + (b - a) * t) for a, b in zip(bg_base, bg_hov))
            border = tuple(int(a + (b - a) * t) for a, b in zip(C_BORDER, C_BORDER2))
            bw = 1

        _draw_rounded_rect_with_border(surf, self.rect, bg, border, radius=8, bw=bw)

        # Glow for active
        if self.is_active:
            gs = pygame.Surface((self.rect.w + 16, self.rect.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*self._accent[:3], 30), gs.get_rect(), border_radius=12)
            surf.blit(gs, (self.rect.x - 8, self.rect.y - 8))
            _draw_rounded_rect_with_border(surf, self.rect, bg, border, radius=8, bw=bw)

        txt_col = (255, 255, 255) if self.is_active else (220, 216, 255)
        fsize = max(13, self.rect.h // 2)          # much larger, always visible
        lbl = _sfont(fsize, True).render(self.text, True, txt_col)
        surf.blit(lbl, (self.rect.centerx - lbl.get_width() // 2,
                        self.rect.centery - lbl.get_height() // 2))

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class MenuScreen:
    def __init__(self, screen: pygame.Surface, toggle_fullscreen=None):
        self.screen = screen
        self._toggle_fullscreen = toggle_fullscreen
        self.config = {
            'mode': 'hvc',
            'num_players': 2,
            'ai_difficulty': 'Medium',
            'ai_player': 1,
            'load_slot': None,
        }
        self._tick = 0
        self._build_buttons()

    def _build_buttons(self):
        self.mode_btns = [
            Button("Human vs Human", 'hvh'),
            Button("Human vs AI",    'hvc', accent=C_ACCENT),
        ]
        self.player_btns = [
            Button("2 Players", 2),
            Button("4 Players", 4),
        ]
        self.diff_btns = [
            Button("Easy",   'Easy',   accent=C_ACCENT3),
            Button("Medium", 'Medium', accent=C_ACCENT),
            Button("Hard",   'Hard',   accent=C_ACCENT2),
        ]
        self.start_btn = Button("▶  START GAME", color=(40, 30, 90),
                                active_color=(70, 55, 180), accent=C_ACCENT)
        self.start_btn.is_active = True

        self.slot_btns = []
        slots = all_slots()
        for i in range(3):
            info = slots[i]
            label = (f"Slot {i+1}  ·  Move #{info['move_count']}  ({info['saved_at'][:10]})"
                     if info else f"Slot {i+1}  ·  Empty")
            self.slot_btns.append(Button(label, i))

        self._sync_active()

    def _layout_buttons(self, sw: int, sh: int):
        """Distribute all sections evenly — nothing overlaps or gets cut off."""
        cx = sw // 2

        # Fixed element heights (scale with screen)
        title_block = max(70, min(120, int(sh * 0.15)))
        footer_h    = max(24, int(sh * 0.045))
        sec_h       = max(18, int(sh * 0.028))   # larger section header
        lbl_gap     = max(6,  int(sh * 0.009))
        bh          = max(36, min(52, int(sh * 0.065)))   # taller buttons
        sbh         = max(46, min(60, int(sh * 0.075)))   # taller start button
        sloth       = max(30, min(42, int(sh * 0.052)))
        slot_gap    = max(5,  int(sh * 0.008))
        n_slots     = len(self.slot_btns)

        section_h   = sec_h + lbl_gap + bh
        slots_block = sec_h + lbl_gap + n_slots * sloth + (n_slots - 1) * slot_gap
        content_h   = section_h * 3 + sbh + slots_block + footer_h
        avail       = sh - title_block - footer_h
        n_gaps      = 5
        gap         = max(6, (avail - content_h) // n_gaps)

        bw     = max(140, min(210, int(sw * 0.155)))
        btn_gap = max(8, int(sw * 0.01))
        btotal  = bw * 2 + btn_gap
        dbw    = max(85, min(125, int(sw * 0.09)))
        dtotal  = dbw * 3 + btn_gap * 2
        sbw    = max(180, min(260, int(sw * 0.20)))
        slotw  = max(260, min(460, int(sw * 0.35)))

        y = title_block + gap

        # GAME MODE
        self._y_mode_lbl = y;  y += sec_h + lbl_gap
        self._y_mode = y
        self.mode_btns[0].rect = pygame.Rect(cx - btotal // 2, y, bw, bh)
        self.mode_btns[1].rect = pygame.Rect(cx - btotal // 2 + bw + btn_gap, y, bw, bh)
        y += bh + gap

        # NUMBER OF PLAYERS
        self._y_pl_lbl = y;  y += sec_h + lbl_gap
        self._y_pl = y
        self.player_btns[0].rect = pygame.Rect(cx - btotal // 2, y, bw, bh)
        self.player_btns[1].rect = pygame.Rect(cx - btotal // 2 + bw + btn_gap, y, bw, bh)
        y += bh + gap

        # AI DIFFICULTY
        self._y_diff_lbl = y;  y += sec_h + lbl_gap
        self._y_diff = y
        for i, b in enumerate(self.diff_btns):
            b.rect = pygame.Rect(cx - dtotal // 2 + i * (dbw + btn_gap), y, dbw, bh)
        y += bh + gap

        # START
        self._y_start = y
        self.start_btn.rect = pygame.Rect(cx - sbw // 2, y, sbw, sbh)
        y += sbh + gap

        # LOAD SAVED GAME
        self._y_slot_lbl = y;  y += sec_h + lbl_gap
        self._y_slot = y
        for i, b in enumerate(self.slot_btns):
            b.rect = pygame.Rect(cx - slotw // 2, y + i * (sloth + slot_gap), slotw, sloth)

        self._title_block = title_block
        self._footer_h    = footer_h
        self._sec_h       = sec_h
        self._sw, self._sh = sw, sh

    def _sync_active(self):
        for b in self.mode_btns:   b.is_active = (b.value == self.config['mode'])
        for b in self.player_btns: b.is_active = (b.value == self.config['num_players'])
        for b in self.diff_btns:   b.is_active = (b.value == self.config['ai_difficulty'])

    def run(self) -> Optional[dict]:
        clock = pygame.time.Clock()
        while True:
            sw, sh = self.screen.get_size()
            self._layout_buttons(sw, sh)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_F11 and self._toggle_fullscreen:
                        self.screen = self._toggle_fullscreen(self.screen)

                for b in self.mode_btns:
                    if b.handle(event):
                        self.config['mode'] = b.value; self._sync_active()
                for b in self.player_btns:
                    if b.handle(event):
                        self.config['num_players'] = b.value; self._sync_active()
                for b in self.diff_btns:
                    if b.handle(event):
                        self.config['ai_difficulty'] = b.value; self._sync_active()
                if self.start_btn.handle(event):
                    self.config['load_slot'] = None
                    return self.config
                for b in self.slot_btns:
                    if b.handle(event):
                        slots = all_slots()
                        if slots[b.value]:
                            self.config['load_slot'] = b.value
                            return self.config
                self.start_btn.handle(event)

            self._draw()
            pygame.display.flip()
            clock.tick(60)

    def _draw(self):
        self._tick += 1
        sw, sh = self.screen.get_size()
        cx = sw // 2
        self.screen.fill(C_BG)

        # ── Atmosphere ──
        # Animated corner glows
        t = self._tick * 0.015
        for i, (ox, oy, col) in enumerate([
            (0, 0, C_ACCENT), (sw, 0, (80, 40, 160)),
            (0, sh, (40, 80, 160)), (sw, sh, (40, 140, 220))
        ]):
            pulse = 0.8 + 0.2 * math.sin(t + i * 1.5)
            r = int(300 * pulse)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, 10), (r, r), r)
            self.screen.blit(s, (ox - r, oy - r), special_flags=pygame.BLEND_RGBA_ADD)

        # Scanlines
        for y in range(0, sh, 4):
            s = pygame.Surface((sw, 1), pygame.SRCALPHA)
            s.fill((255, 255, 255, 4))
            self.screen.blit(s, (0, y))

        # ── Title ──
        title_sz = max(32, min(72, sw // 14))
        t1 = _font(title_sz, True).render("QUORIDOR", True, C_TEXT)
        ty = max(20, int(sh * 0.06))
        self.screen.blit(t1, (cx - t1.get_width() // 2, ty))

        # Accent underline
        uw = t1.get_width() + 20
        ul_y = ty + t1.get_height() + 2
        pygame.draw.rect(self.screen, C_ACCENT,
                         (cx - uw // 2, ul_y, uw, 3), border_radius=2)

        sub_sz = max(13, title_sz // 4)
        sub = _sfont(sub_sz, True).render("THE ART OF STRATEGIC OBSTRUCTION", True, (200, 196, 255))
        self.screen.blit(sub, (cx - sub.get_width() // 2, ul_y + 10))

        # ── Section headers & dividers ──
        sec_sz = max(13, min(16, sw // 80))
        sections = [
            ("GAME MODE",          self._y_mode_lbl),
            ("NUMBER OF PLAYERS",  self._y_pl_lbl),
            ("AI DIFFICULTY",      self._y_diff_lbl),
        ]
        lx = cx - max(180, int(sw * 0.17))
        rx = cx + max(180, int(sw * 0.17))
        for txt, sy in sections:
            lbl = _sfont(sec_sz, True).render(txt, True, (200, 196, 255))
            self.screen.blit(lbl, (lx, sy))
            pygame.draw.line(self.screen, (80, 76, 140),
                             (lx + lbl.get_width() + 8, sy + lbl.get_height() // 2),
                             (rx, sy + lbl.get_height() // 2))

        # ── Buttons ──
        for b in self.mode_btns: b.draw(self.screen)
        for b in self.player_btns: b.draw(self.screen)

        dim = (self.config['mode'] == 'hvh')
        for b in self.diff_btns:
            b.draw(self.screen)
            if dim:
                ds = pygame.Surface((b.rect.w, b.rect.h), pygame.SRCALPHA)
                ds.fill((8, 8, 14, 160))
                self.screen.blit(ds, b.rect.topleft)

        # Start button (animated glow)
        pulse = 0.6 + 0.4 * math.sin(self._tick * 0.05)
        sr = self.start_btn.rect
        gs = pygame.Surface((sr.w + 40, sr.h + 40), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*C_ACCENT, int(30 * pulse)), gs.get_rect(), border_radius=16)
        self.screen.blit(gs, (sr.x - 20, sr.y - 20))
        self.start_btn.draw(self.screen)

        # ── Load section ──
        load_sz = max(13, min(16, sw // 80))
        ll = _sfont(load_sz, True).render("LOAD SAVED GAME", True, (200, 196, 255))
        lx2 = cx - max(180, int(sw * 0.17))
        rx2 = cx + max(180, int(sw * 0.17))
        self.screen.blit(ll, (lx2, self._y_slot_lbl))
        pygame.draw.line(self.screen, (80, 76, 140),
                         (lx2 + ll.get_width() + 8, self._y_slot_lbl + ll.get_height() // 2),
                         (rx2, self._y_slot_lbl + ll.get_height() // 2))
        for b in self.slot_btns:
            b.draw(self.screen)

        # ── Footer ──
        foot_sz = max(12, min(15, sw // 90))
        keys = [("ESC", "quit"), ("F11", "fullscreen"), ("F2", "new game"), ("S/L", "save/load")]
        parts = []
        for k, v in keys:
            parts.append((k, v))
        foot_y = sh - foot_sz - 14
        px = cx
        sep = _sfont(foot_sz, True).render("  ·  ", True, (130, 126, 180))
        rendered = []
        for k, v in parts:
            kl = _font(foot_sz, True).render(k, True, C_ACCENT)
            vl = _sfont(foot_sz, True).render(f" {v}", True, (220, 216, 255))
            rendered.append((kl, vl))
        total_w = sum(kl.get_width() + vl.get_width() for kl, vl in rendered) + sep.get_width() * (len(rendered) - 1)
        fx = cx - total_w // 2
        for i, (kl, vl) in enumerate(rendered):
            self.screen.blit(kl, (fx, foot_y))
            fx += kl.get_width()
            self.screen.blit(vl, (fx, foot_y))
            fx += vl.get_width()
            if i < len(rendered) - 1:
                self.screen.blit(sep, (fx, foot_y))
                fx += sep.get_width()
