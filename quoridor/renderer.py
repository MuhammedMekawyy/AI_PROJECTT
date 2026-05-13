"""
quoridor/renderer.py
Dynamic renderer — all layout computed from actual screen size at draw time.
Supports true fullscreen: no hardcoded pixel constants used in drawing.
"""
from __future__ import annotations
import pygame
import math
from typing import List, Optional, Tuple
from quoridor.game import GameState, Wall, BOARD_SIZE, PLAYER_COLORS

# ── Fallback window size (only used for initial window creation) ──────────────
WINDOW_W = 1280
WINDOW_H = 800

# ── Color palette ─────────────────────────────────────────────────────────────
C_BG          = ( 8,   8,  14)
C_PANEL       = (13,  13,  22)
C_PANEL2      = (18,  18,  30)
C_BOARD_BG    = (16,  16,  26)
C_CELL        = (22,  22,  36)
C_CELL_ALT    = (26,  26,  42)
C_GRID        = (35,  35,  55)
C_ACCENT      = (108,  86, 255)
C_ACCENT2     = (255, 180,  50)
C_ACCENT3     = ( 50, 220, 150)
C_TEXT        = (255, 255, 255)   # pure white for max readability
C_TEXT2       = (200, 196, 230)   # light lavender — was too dim
C_TEXT3       = (160, 155, 200)   # medium lavender — was nearly invisible
C_BORDER      = ( 38,  36,  58)
C_BORDER2     = ( 52,  48,  80)
C_WALL        = (255, 185,  50)
C_WALL_BAD    = (220,  55,  75)
C_VALID       = (108,  86, 255)
C_WIN_OVERLAY = ( 8,   8,  14, 210)

PLAYER_COLORS_LIST = [
    (255, 100,  80),   # P1 coral-red
    ( 50, 210, 255),   # P2 electric-blue
    (230,  80, 200),   # P3 magenta
    ( 80, 230, 130),   # P4 mint
]

PLAYER_GLOW = [
    (255, 100,  80,  50),
    ( 50, 210, 255,  50),
    (230,  80, 200,  50),
    ( 80, 230, 130,  50),
]

# ── Font cache ────────────────────────────────────────────────────────────────
_fonts: dict = {}

def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.SysFont('consolas,couriernew,monospace', size, bold=bold)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size)
    return _fonts[key]

def _sfont(size: int, bold: bool = False) -> pygame.font.Font:
    """Serif-ish / UI font."""
    key = ('s', size, bold)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.SysFont('segoeui,tahoma,helvetica', size, bold=bold)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size)
    return _fonts[key]


# ── Layout helper — computed fresh each frame from screen size ─────────────────
class Layout:
    def __init__(self, sw: int, sh: int):
        self.sw = sw
        self.sh = sh

        # Panel width: 22% of screen, clamped
        self.panel_w = max(200, min(300, int(sw * 0.22)))
        self.panel_r = max(0, min(200, int(sw * 0.15)))  # right info bar

        # Board area
        board_area_w = sw - self.panel_w - self.panel_r
        pad = max(20, int(sh * 0.04))
        board_px = min(board_area_w - pad * 2, sh - pad * 2)
        board_px = (board_px // BOARD_SIZE) * BOARD_SIZE  # snap to cells

        self.board_px   = board_px
        self.board_x    = self.panel_w + (board_area_w - board_px) // 2
        self.board_y    = (sh - board_px) // 2

        self.cell       = board_px // BOARD_SIZE
        self.gap        = max(3, self.cell // 12)
        self.cell_inner = self.cell - self.gap
        self.wall_thick = max(4, self.cell // 7)

    def cell_to_px(self, row: int, col: int) -> Tuple[int, int]:
        x = self.board_x + col * self.cell + self.gap // 2
        y = self.board_y + row * self.cell + self.gap // 2
        return x, y

    def px_to_cell(self, mx: int, my: int) -> Optional[Tuple[int, int]]:
        bx = mx - self.board_x
        by = my - self.board_y
        if bx < 0 or by < 0 or bx >= self.board_px or by >= self.board_px:
            return None
        return by // self.cell, bx // self.cell

    def px_to_wall(self, mx: int, my: int, orientation: str) -> Optional[Wall]:
        cell = self.px_to_cell(mx, my)
        if cell is None:
            return None
        r, c = cell
        r = min(r, BOARD_SIZE - 2)
        c = min(c, BOARD_SIZE - 2)
        return Wall(r, c, orientation == 'H')


# ── Standalone helpers (for controller compatibility) ────────────────────────
# These use a module-level layout updated each frame
_cur_layout: Optional[Layout] = None

def _get_layout(screen: pygame.Surface) -> Layout:
    global _cur_layout
    sw, sh = screen.get_size()
    if _cur_layout is None or _cur_layout.sw != sw or _cur_layout.sh != sh:
        _cur_layout = Layout(sw, sh)
    return _cur_layout

def cell_to_px(row: int, col: int) -> Tuple[int, int]:
    if _cur_layout:
        return _cur_layout.cell_to_px(row, col)
    return (0, 0)

def px_to_cell(mx: int, my: int) -> Optional[Tuple[int, int]]:
    if _cur_layout:
        return _cur_layout.px_to_cell(mx, my)
    return None

def px_to_wall(mx: int, my: int) -> Optional[Wall]:
    return None

# Keep these for imports that reference them
CELL = 72
CELL_INNER = 68


# ── Drawing helpers ───────────────────────────────────────────────────────────
def _draw_rounded_rect_with_border(surf, rect, bg, border, radius=10, bw=1):
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, width=bw, border_radius=radius)

def _glow_circle(surf, color, center, radius, strength=60):
    for r in range(radius + strength, radius - 1, -3):
        alpha = max(0, int(strength * (1 - (r - radius) / strength) * 0.6))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color[:3], alpha), (r, r), r)
        surf.blit(s, (center[0] - r, center[1] - r), special_flags=pygame.BLEND_RGBA_ADD)


# ── Main Renderer ─────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._tick = 0
        self._wall_surf = None
        self._rebuild_surfaces()

    def _rebuild_surfaces(self):
        sw, sh = self.screen.get_size()
        self._wall_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)

    def draw(self, state: GameState, valid_moves, selected_cell,
             wall_preview, wall_preview_ok, action_mode, ui_state):
        sw, sh = self.screen.get_size()
        L = _get_layout(self.screen)

        if (self._wall_surf is None
                or self._wall_surf.get_width() != sw
                or self._wall_surf.get_height() != sh):
            self._rebuild_surfaces()

        self._tick += 1
        self.screen.fill(C_BG)

        # Subtle scanline atmosphere
        self._draw_atmosphere(sw, sh)

        self._draw_panel_left(L, state, ui_state)
        self._draw_panel_right(L, state, ui_state)
        self._draw_board(L, state, valid_moves, selected_cell,
                         wall_preview, wall_preview_ok, action_mode)

        if state.winner is not None:
            self._draw_winner(L, state, ui_state)

    # ── Atmosphere ────────────────────────────────────────────────────────────
    def _draw_atmosphere(self, sw, sh):
        # Corner glows
        for corner, color in [((0, 0), C_ACCENT), ((sw, sh), (50, 30, 120))]:
            s = pygame.Surface((400, 400), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, 8), (200, 200), 200)
            self.screen.blit(s, (corner[0] - 200, corner[1] - 200),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # Subtle horizontal lines
        for y in range(0, sh, 4):
            alpha = 4
            s = pygame.Surface((sw, 1), pygame.SRCALPHA)
            s.fill((255, 255, 255, alpha))
            self.screen.blit(s, (0, y))

    # ── Left Panel ────────────────────────────────────────────────────────────
    def _draw_panel_left(self, L: Layout, state: GameState, ui_state: dict):
        sw, sh = self.screen.get_size()
        pw = L.panel_w

        # Panel background
        panel = pygame.Rect(0, 0, pw, sh)
        pygame.draw.rect(self.screen, C_PANEL, panel)
        # Right border glow
        for i in range(4):
            alpha = 40 - i * 10
            s = pygame.Surface((2, sh), pygame.SRCALPHA)
            s.fill((*C_ACCENT, alpha))
            self.screen.blit(s, (pw - i, 0))

        y = 24
        # ── Logo ──
        logo_size = max(26, min(36, pw // 7))  # larger, more readable
        t1 = _font(logo_size, True).render("QUORIDOR", True, C_TEXT)
        self.screen.blit(t1, (pw // 2 - t1.get_width() // 2, y))
        y += t1.get_height() + 4

        sub = _sfont(max(12, logo_size // 2), True).render("STRATEGY BOARD GAME", True, C_ACCENT)
        self.screen.blit(sub, (pw // 2 - sub.get_width() // 2, y))
        y += sub.get_height() + 4

        # Thin accent line
        pygame.draw.line(self.screen, C_ACCENT, (16, y), (pw - 16, y), 1)
        y += 16

        # ── Players ──
        sec = _sfont(max(12, logo_size // 2), True).render("PLAYERS", True, C_TEXT2)
        self.screen.blit(sec, (16, y)); y += sec.get_height() + 8

        for pid in range(state.num_players):
            p = state.players[pid]
            is_active = (state.current_player == pid) and state.winner is None
            pcolor = PLAYER_COLORS_LIST[pid]
            box_h = max(44, int(sh * 0.075))
            box = pygame.Rect(10, y, pw - 20, box_h)

            # Glow for active player
            if is_active:
                glow = pygame.Surface((box.w + 20, box.h + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*pcolor, 18), glow.get_rect(), border_radius=12)
                self.screen.blit(glow, (box.x - 10, box.y - 10))

            bg = (24, 22, 42) if is_active else (16, 16, 28)
            brd = pcolor if is_active else C_BORDER
            _draw_rounded_rect_with_border(self.screen, box, bg, brd, radius=8,
                                           bw=2 if is_active else 1)

            # Player dot
            dot_r = max(8, box_h // 5)
            dot_cx = box.x + dot_r + 10
            dot_cy = box.y + box_h // 2
            pygame.draw.circle(self.screen, (*pcolor, 60), (dot_cx, dot_cy), dot_r + 4)
            pygame.draw.circle(self.screen, pcolor, (dot_cx, dot_cy), dot_r)
            if is_active:
                pygame.draw.circle(self.screen, (255, 255, 255), (dot_cx, dot_cy), dot_r, 2)
            num_lbl = _font(max(9, dot_r), True).render(str(pid + 1), True, (255, 255, 255))
            self.screen.blit(num_lbl, (dot_cx - num_lbl.get_width() // 2,
                                       dot_cy - num_lbl.get_height() // 2))

            # Name
            name = ui_state.get('player_names', {}).get(pid, f"Player {pid+1}")
            name_font_size = max(13, min(16, pw // 16))
            name_lbl = _sfont(name_font_size, True).render(name, True, C_TEXT)
            self.screen.blit(name_lbl, (dot_cx + dot_r + 8, box.y + 6))

            # Walls remaining
            w_lbl = _sfont(max(11, name_font_size - 1)).render(
                f"Walls: {p.walls_remaining}", True, C_TEXT2)
            self.screen.blit(w_lbl, (dot_cx + dot_r + 8, box.y + 6 + name_lbl.get_height() + 2))

            # Mini wall icons
            icon_x = box.right - 10
            for wi in range(p.walls_remaining):
                ix = icon_x - wi * 6
                if ix < dot_cx + dot_r + 8 + w_lbl.get_width() + 4:
                    break
                pygame.draw.rect(self.screen, C_WALL,
                                 (ix - 4, box.y + box_h // 2 - 8, 3, 16), border_radius=1)

            y += box_h + 8

        y += 4
        pygame.draw.line(self.screen, C_BORDER, (16, y), (pw - 16, y)); y += 12

        # ── Turn status ──
        if state.winner is None:
            pid = state.current_player
            name = ui_state.get('player_names', {}).get(pid, f"Player {pid+1}")
            pcolor = PLAYER_COLORS_LIST[pid]
            turn_size = max(13, min(16, pw // 16))
            t = _sfont(turn_size, True).render(f"Turn: {name}", True, pcolor)
        else:
            pid = state.winner
            name = ui_state.get('player_names', {}).get(pid, f"Player {pid+1}")
            t = _sfont(max(13, min(16, pw // 16)), True).render(f"★ {name} wins!", True, C_ACCENT2)
        self.screen.blit(t, (16, y)); y += t.get_height() + 4

        mv = _sfont(max(12, min(14, pw // 18))).render(f"Move #{state.move_count}", True, C_TEXT2)
        self.screen.blit(mv, (16, y)); y += mv.get_height() + 6

        # ── Mode indicator ──
        mode = ui_state.get('action_mode', 'move')
        mode_str = "▶  MOVE PAWN" if mode == 'move' else "▦  PLACE WALL"
        mode_col = C_ACCENT3 if mode == 'move' else C_ACCENT2
        mode_sz = max(12, min(15, pw // 18))
        mode_box = pygame.Rect(10, y, pw - 20, max(26, int(sh * 0.035)))
        pygame.draw.rect(self.screen, (*mode_col, 20), mode_box, border_radius=6)
        pygame.draw.rect(self.screen, (*mode_col, 80), mode_box, width=1, border_radius=6)
        ml = _sfont(mode_sz, True).render(mode_str, True, mode_col)
        self.screen.blit(ml, (mode_box.centerx - ml.get_width() // 2,
                               mode_box.centery - ml.get_height() // 2))
        y += mode_box.height + 6

        if mode == 'wall':
            wo = ui_state.get('wall_orientation', 'H')
            ol = _sfont(max(11, mode_sz - 1), True).render(
                f"{'━━' if wo=='H' else '┃'} {'Horizontal' if wo=='H' else 'Vertical'}  (R rotate)",
                True, C_TEXT2)
            self.screen.blit(ol, (16, y)); y += ol.get_height() + 4

        y += 4
        pygame.draw.line(self.screen, C_BORDER, (16, y), (pw - 16, y)); y += 10

        # ── Controls ──
        controls = [
            ("CONTROLS", None),
            ("Click", "Move pawn"),
            ("W", "Wall mode"),
            ("R", "Rotate wall"),
            ("Z / Y", "Undo / Redo"),
            ("S / L", "Save / Load"),
            ("F11", "Fullscreen"),
            ("F2", "New game"),
            ("ESC", "Menu"),
        ]
        ksz = max(11, min(13, pw // 20))
        for k, v in controls:
            if y > sh - 16: break
            if v is None:
                lbl = _sfont(ksz, True).render(k, True, C_TEXT2)
                self.screen.blit(lbl, (16, y)); y += lbl.get_height() + 4
            else:
                kl = _font(ksz, True).render(k, True, C_ACCENT)
                vl = _sfont(ksz, True).render(v, True, C_TEXT)
                self.screen.blit(kl, (16, y))
                self.screen.blit(vl, (16 + max(60, pw // 4), y))
                y += max(kl.get_height(), vl.get_height()) + 4

    # ── Right Panel ───────────────────────────────────────────────────────────
    def _draw_panel_right(self, L: Layout, state: GameState, ui_state: dict):
        sw, sh = self.screen.get_size()
        pw = L.panel_r
        if pw < 60:
            return
        rx = sw - pw

        panel = pygame.Rect(rx, 0, pw, sh)
        pygame.draw.rect(self.screen, C_PANEL, panel)
        for i in range(4):
            alpha = 40 - i * 10
            s = pygame.Surface((2, sh), pygame.SRCALPHA)
            s.fill((*C_ACCENT, alpha))
            self.screen.blit(s, (rx + i, 0))

        y = 24
        sz = max(8, min(11, pw // 12))
        label = _sfont(sz - 1).render("BOARD", True, C_TEXT3)
        self.screen.blit(label, (rx + pw // 2 - label.get_width() // 2, y)); y += label.get_height() + 6

        # Column letters vertical
        for i in range(BOARD_SIZE):
            lx, ly = L.cell_to_px(i, 0)
            lbl = _sfont(max(7, sz)).render(str(i + 1), True, C_TEXT3)
            self.screen.blit(lbl, (rx + pw // 2 - lbl.get_width() // 2,
                                   ly + L.cell_inner // 2 - lbl.get_height() // 2))

    # ── Board ─────────────────────────────────────────────────────────────────
    def _draw_board(self, L: Layout, state: GameState, valid_moves, selected_cell,
                    wall_preview, wall_preview_ok, action_mode):
        bx, by = L.board_x, L.board_y
        bp = L.board_px

        # Board shadow
        shadow = pygame.Rect(bx - 2 + 6, by - 2 + 6, bp + 4, bp + 4)
        pygame.draw.rect(self.screen, (4, 4, 8), shadow, border_radius=14)

        # Board bg
        board_rect = pygame.Rect(bx - 6, by - 6, bp + 12, bp + 12)
        _draw_rounded_rect_with_border(self.screen, board_rect, C_BOARD_BG, C_BORDER2,
                                       radius=12, bw=1)

        # Inner border glow
        for i in range(3):
            alpha = 20 - i * 6
            ir = pygame.Rect(bx - 4 + i, by - 4 + i, bp + 8 - i*2, bp + 8 - i*2)
            s = pygame.Surface((ir.w, ir.h), pygame.SRCALPHA)
            pygame.draw.rect(s, (*C_ACCENT, alpha), s.get_rect(), width=1, border_radius=10)
            self.screen.blit(s, ir.topleft)

        # Goal zones
        self._draw_goal_zones(L, state)

        # Cells
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x, y = L.cell_to_px(row, col)
                base = C_CELL_ALT if (row + col) % 2 == 0 else C_CELL
                if selected_cell == (row, col):
                    base = C_ACCENT
                rect = pygame.Rect(x, y, L.cell_inner, L.cell_inner)
                pygame.draw.rect(self.screen, base, rect, border_radius=3)

        # Valid move dots
        for (vr, vc) in valid_moves:
            x, y = L.cell_to_px(vr, vc)
            cx = x + L.cell_inner // 2
            cy = y + L.cell_inner // 2
            # Pulsing glow
            pulse = 0.7 + 0.3 * math.sin(self._tick * 0.08)
            r_dot = max(4, int(L.cell_inner * 0.22 * pulse))
            glow_s = pygame.Surface((r_dot * 6, r_dot * 6), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (*C_VALID, 30), (r_dot * 3, r_dot * 3), r_dot * 3)
            self.screen.blit(glow_s, (cx - r_dot * 3, cy - r_dot * 3),
                             special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(self.screen, C_VALID, (cx, cy), r_dot)

            rect = pygame.Rect(x, y, L.cell_inner, L.cell_inner)
            pygame.draw.rect(self.screen, (*C_VALID, 40), rect, width=2, border_radius=3)

        # Column labels (top)
        for col in range(BOARD_SIZE):
            x, _ = L.cell_to_px(0, col)
            lbl = _sfont(max(8, L.cell // 5)).render(chr(ord('A') + col), True, C_TEXT3)
            self.screen.blit(lbl, (x + L.cell_inner // 2 - lbl.get_width() // 2,
                                   by - lbl.get_height() - 4))

        # Placed walls
        for wall in state.walls:
            self._draw_wall(L, wall, C_WALL, alpha=255)

        # Wall preview
        if wall_preview:
            col = C_ACCENT3 if wall_preview_ok else C_WALL_BAD
            self._draw_wall(L, wall_preview, col, alpha=140)

        # Pawns
        for pid, player in enumerate(state.players):
            self._draw_pawn(L, player.row, player.col, pid,
                            selected=(selected_cell == player.pos))

    def _draw_goal_zones(self, L: Layout, state: GameState):
        for pid in range(min(2, state.num_players)):
            p = state.players[pid]
            col = PLAYER_COLORS_LIST[pid]
            goal_row = p.goal_row
            x, y = L.cell_to_px(goal_row, 0)
            s = pygame.Surface((L.board_px, L.cell_inner + L.gap), pygame.SRCALPHA)
            s.fill((*col, 18))
            self.screen.blit(s, (L.board_x, y - L.gap // 2))
            # Left marker stripe
            stripe = pygame.Surface((4, L.cell_inner + L.gap), pygame.SRCALPHA)
            stripe.fill((*col, 120))
            self.screen.blit(stripe, (L.board_x - 6, y - L.gap // 2))

    def _draw_wall(self, L: Layout, wall: Wall, color: tuple, alpha: int = 255):
        r, c = wall.row, wall.col
        if wall.horizontal:
            x1, y1 = L.cell_to_px(r, c)
            x2, y2 = L.cell_to_px(r, c + 1)
            wy = y1 + L.cell_inner + L.gap // 2
            wx1 = x1 - L.gap // 2
            wx2 = x2 + L.cell_inner + L.gap // 2
            rect = pygame.Rect(wx1, wy - L.wall_thick // 2, wx2 - wx1, L.wall_thick)
        else:
            x1, y1 = L.cell_to_px(r, c)
            x2, y2 = L.cell_to_px(r + 1, c)
            wx = x1 + L.cell_inner + L.gap // 2
            wy1 = y1 - L.gap // 2
            wy2 = y2 + L.cell_inner + L.gap // 2
            rect = pygame.Rect(wx - L.wall_thick // 2, wy1, L.wall_thick, wy2 - wy1)

        if alpha < 255:
            s = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
            inner = pygame.Rect(10, 10, rect.w, rect.h)
            # Glow
            glow_col = (*color[:3], alpha // 3)
            outer = pygame.Rect(4, 4, rect.w + 12, rect.h + 12)
            pygame.draw.rect(s, glow_col, outer, border_radius=4)
            pygame.draw.rect(s, (*color[:3], alpha), inner, border_radius=3)
            self.screen.blit(s, (rect.x - 10, rect.y - 10))
        else:
            # Glow pass
            gs = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*color[:3], 40), gs.get_rect(), border_radius=5)
            self.screen.blit(gs, (rect.x - 8, rect.y - 8),
                             special_flags=pygame.BLEND_RGBA_ADD)
            # Main wall with gradient-ish highlight
            pygame.draw.rect(self.screen, color, rect, border_radius=3)
            # Shine
            if rect.w > rect.h:  # horizontal
                shine = pygame.Rect(rect.x, rect.y, rect.w, rect.h // 2)
            else:
                shine = pygame.Rect(rect.x, rect.y, rect.w // 2, rect.h)
            s2 = pygame.Surface((shine.w, shine.h), pygame.SRCALPHA)
            s2.fill((255, 255, 255, 30))
            self.screen.blit(s2, shine.topleft)

    def _draw_pawn(self, L: Layout, row: int, col: int, pid: int, selected: bool):
        x, y = L.cell_to_px(row, col)
        cx = x + L.cell_inner // 2
        cy = y + L.cell_inner // 2
        r = max(8, int(L.cell_inner * 0.36))
        color = PLAYER_COLORS_LIST[pid]

        # Glow
        glow_r = r + 10
        gs = pygame.Surface((glow_r * 2 + 10, glow_r * 2 + 10), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*color, 35), (glow_r + 5, glow_r + 5), glow_r)
        self.screen.blit(gs, (cx - glow_r - 5, cy - glow_r - 5),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # Shadow
        pygame.draw.circle(self.screen, (4, 4, 8), (cx + 2, cy + 3), r)

        # Body
        pygame.draw.circle(self.screen, color, (cx, cy), r)

        # Inner gradient shine (top-left bright)
        shine_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for sr in range(r, 0, -2):
            alpha = int(80 * (1 - sr / r))
            pygame.draw.circle(shine_surf, (255, 255, 255, alpha),
                                (r // 2, r // 2), sr)
        self.screen.blit(shine_surf, (cx - r, cy - r),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # Selected ring
        if selected:
            pulse = 0.7 + 0.3 * math.sin(self._tick * 0.1)
            ring_r = int(r * (1.3 + 0.1 * pulse))
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), ring_r, 2)

        # Number label
        num = _font(max(8, r - 2), True).render(str(pid + 1), True, (255, 255, 255))
        self.screen.blit(num, (cx - num.get_width() // 2, cy - num.get_height() // 2))

    # ── Winner overlay ────────────────────────────────────────────────────────
    def _draw_winner(self, L: Layout, state: GameState, ui_state: dict):
        sw, sh = self.screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((6, 6, 12, 200))
        self.screen.blit(overlay, (0, 0))

        pid = state.winner
        color = PLAYER_COLORS_LIST[pid]
        name = ui_state.get('player_names', {}).get(pid, f"Player {pid + 1}")
        cx, cy = sw // 2, sh // 2

        # Glow circle
        for radius in [130, 100, 70]:
            gs = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            alpha = 25
            pygame.draw.circle(gs, (*color, alpha), (radius, radius), radius)
            self.screen.blit(gs, (cx - radius, cy - 80 - radius),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # Big pawn icon
        pygame.draw.circle(self.screen, (*color, 40), (cx, cy - 80), 60)
        pygame.draw.circle(self.screen, color, (cx, cy - 80), 50)
        num = _font(40, True).render(str(pid + 1), True, (255, 255, 255))
        self.screen.blit(num, (cx - num.get_width() // 2, cy - 80 - num.get_height() // 2))

        # Win text — with drop-shadow for contrast against glow background
        win_sz = max(36, min(64, sw // 15))
        win_text = f"PLAYER {pid+1} WINS"
        # Draw dark shadow first for contrast
        shadow_lbl = _font(win_sz, True).render(win_text, True, (0, 0, 0))
        for ox, oy in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
            self.screen.blit(shadow_lbl, (cx - shadow_lbl.get_width() // 2 + ox, cy + 10 + oy))
        win_lbl = _font(win_sz, True).render(win_text, True, (255, 255, 255))
        self.screen.blit(win_lbl, (cx - win_lbl.get_width() // 2, cy + 10))

        name_lbl = _sfont(max(18, win_sz // 2), True).render(f"({name})", True, (220, 216, 255))
        self.screen.blit(name_lbl, (cx - name_lbl.get_width() // 2, cy + 10 + win_lbl.get_height() + 6))

        move_lbl = _sfont(max(16, win_sz // 3), True).render(
            f"Completed in {state.move_count} moves", True, (200, 196, 230))
        self.screen.blit(move_lbl, (cx - move_lbl.get_width() // 2,
                                    cy + 10 + win_lbl.get_height() + name_lbl.get_height() + 14))

        hint = _sfont(max(14, win_sz // 4), True).render(
            "F2  new game    ESC  menu", True, (200, 196, 230))
        self.screen.blit(hint, (cx - hint.get_width() // 2, cy + 10 + win_lbl.get_height()
                                + name_lbl.get_height() + move_lbl.get_height() + 28))
