"""
quoridor/controller.py
Game controller: event handling, undo/redo stack, AI scheduling, action mode.
Uses dynamic layout from renderer so fullscreen works correctly.
"""
from __future__ import annotations
import pygame
import threading
from typing import Optional, List, Tuple, Dict
from quoridor.game import GameState, MoveAction, WallAction, Wall, BOARD_SIZE
from quoridor.ai import QuoridorAI, EASY, MEDIUM, HARD
from quoridor.renderer import (Renderer, WINDOW_W, WINDOW_H, Layout,
                                _sfont, _font,
                                C_ACCENT, C_BORDER, C_TEXT, C_TEXT2,
                                PLAYER_COLORS_LIST)
from quoridor.save_manager import save_game, load_game
from quoridor.dialogs import show_save_dialog, show_load_dialog, show_confirm


class GameController:
    """
    Runs the main game loop for one match.
    Returns 'menu' to go back to menu, or 'quit' to exit.
    """

    def __init__(self, screen: pygame.Surface, config: dict, toggle_fullscreen=None):
        self.screen = screen
        self.config  = config
        self._toggle_fullscreen = toggle_fullscreen
        self.renderer = Renderer(screen)

        num_players = config.get('num_players', 2)
        load_slot   = config.get('load_slot', None)

        if load_slot is not None:
            state = load_game(load_slot)
            if state is None:
                state = GameState(num_players)
        else:
            state = GameState(num_players)

        self.state: GameState = state
        self._history: List[GameState] = []
        self._redo:    List[GameState] = []

        # AI setup
        self.ai_agents: Dict[int, QuoridorAI] = {}
        mode = config.get('mode', 'hvh')
        if mode == 'hvc':
            diff = config.get('ai_difficulty', MEDIUM)
            ai_pid = config.get('ai_player', 1)
            self.ai_agents[ai_pid] = QuoridorAI(ai_pid, diff)

        self.action_mode: str = 'move'
        self.wall_orientation: str = 'H'
        self.selected_cell: Optional[Tuple[int,int]] = None
        self.valid_moves: List[Tuple[int,int]] = []
        self.wall_preview: Optional[Wall] = None
        self.wall_preview_ok: bool = False

        self._ai_thinking: bool = False
        self._ai_result: Optional  = None

        self.player_names = self._build_names(config, num_players)

        self.clock = pygame.time.Clock()
        self.running = True
        self.result = 'menu'

    def _build_names(self, config: dict, n: int) -> Dict[int, str]:
        names = {}
        for i in range(n):
            if i in self.ai_agents:
                diff = config.get('ai_difficulty', MEDIUM)
                names[i] = f"AI ({diff})"
            else:
                names[i] = f"Player {i+1}"
        return names

    def _layout(self) -> Layout:
        sw, sh = self.screen.get_size()
        return Layout(sw, sh)

    # ── Main loop ──────────────────────────────────────────────────────────────
    def run(self) -> str:
        while self.running:
            self._handle_events()
            self._tick_ai()
            self._draw()
            self.clock.tick(60)
        return self.result

    # ── Events ─────────────────────────────────────────────────────────────────
    def _handle_events(self):
        mx, my = pygame.mouse.get_pos()
        self._update_wall_preview(mx, my)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False; self.result = 'quit'; return

            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_key(self, key: int):
        if key == pygame.K_F11 and self._toggle_fullscreen:
            self.screen = self._toggle_fullscreen(self.screen)
            self.renderer.screen = self.screen
            self.renderer._rebuild_surfaces()
            return
        if key == pygame.K_ESCAPE:
            self.running = False; self.result = 'menu'
        elif key == pygame.K_F2:
            self.running = False; self.result = 'menu'
        elif key == pygame.K_w:
            self._toggle_mode()
        elif key == pygame.K_r:
            self._rotate_wall()
        elif key == pygame.K_z:
            self._undo()
        elif key == pygame.K_y:
            self._redo_action()
        elif key == pygame.K_s:
            self._save()
        elif key == pygame.K_l:
            self._load()

    def _handle_click(self, pos: Tuple[int,int]):
        if self.state.winner is not None:
            return
        if self._ai_thinking:
            return
        pid = self.state.current_player
        if pid in self.ai_agents:
            return

        if self.action_mode == 'move':
            self._handle_move_click(pos)
        else:
            self._handle_wall_click(pos)

    def _handle_move_click(self, pos):
        L = self._layout()
        cell = L.px_to_cell(*pos)
        if cell is None:
            self.selected_cell = None
            self.valid_moves = []
            return
        pid = self.state.current_player
        player = self.state.players[pid]
        if cell == player.pos:
            if self.selected_cell == cell:
                self.selected_cell = None
                self.valid_moves = []
            else:
                self.selected_cell = cell
                self.valid_moves = self.state.legal_pawn_moves(pid)
            return
        if cell in self.valid_moves:
            self._apply_action(MoveAction(pid, player.pos, cell))
            self.selected_cell = None
            self.valid_moves = []
            return
        vm = self.state.legal_pawn_moves(pid)
        if cell in vm:
            self._apply_action(MoveAction(pid, player.pos, cell))
            self.selected_cell = None
            self.valid_moves = []
        else:
            self.selected_cell = None
            self.valid_moves = []

    def _handle_wall_click(self, pos):
        if self.wall_preview and self.wall_preview_ok:
            pid = self.state.current_player
            self._apply_action(WallAction(pid, self.wall_preview))

    def _update_wall_preview(self, mx: int, my: int):
        if self.action_mode != 'wall' or self.state.winner is not None:
            self.wall_preview = None
            return
        pid = self.state.current_player
        if pid in self.ai_agents:
            self.wall_preview = None
            return

        L = self._layout()
        cell = L.px_to_cell(mx, my)
        if cell is None:
            self.wall_preview = None
            return

        r, c = cell
        horiz = (self.wall_orientation == 'H')
        r = min(r, BOARD_SIZE - 2)
        c = min(c, BOARD_SIZE - 2)
        wall = Wall(r, c, horiz)
        self.wall_preview = wall
        self.wall_preview_ok = self.state.can_place_wall(wall, pid)

    def _toggle_mode(self):
        self.action_mode = 'wall' if self.action_mode == 'move' else 'move'
        self.selected_cell = None
        self.valid_moves = []

    def _rotate_wall(self):
        self.wall_orientation = 'V' if self.wall_orientation == 'H' else 'H'

    # ── Action application ────────────────────────────────────────────────────
    def _apply_action(self, action):
        self._history.append(self.state._clone())
        self._redo.clear()
        self.state._apply_inplace(action)
        self.action_mode = 'move'

    def _undo(self):
        if not self._history:
            return
        self._redo.append(self.state._clone())
        self.state = self._history.pop()
        self.selected_cell = None
        self.valid_moves = []
        self.action_mode = 'move'

    def _redo_action(self):
        if not self._redo:
            return
        self._history.append(self.state._clone())
        self.state = self._redo.pop()
        self.selected_cell = None
        self.valid_moves = []

    # ── AI ────────────────────────────────────────────────────────────────────
    def _tick_ai(self):
        pid = self.state.current_player
        if (self.state.winner is None
                and pid in self.ai_agents
                and not self._ai_thinking
                and self._ai_result is None):
            self._ai_thinking = True
            ai = self.ai_agents[pid]
            state_copy = self.state._clone()

            def think():
                self._ai_result = ai.choose_action(state_copy)
                self._ai_thinking = False

            t = threading.Thread(target=think, daemon=True)
            t.start()

        if self._ai_result is not None and not self._ai_thinking:
            action = self._ai_result
            self._ai_result = None
            self._apply_action(action)

    # ── Save / Load ───────────────────────────────────────────────────────────
    def _save(self):
        slot = show_save_dialog(self.screen, self.state)
        if slot is not None:
            ok = save_game(self.state, slot, {'player_names': self.player_names})
            self._flash_message(f"Saved to slot {slot+1}!" if ok else "Save failed.")

    def _load(self):
        slot = show_load_dialog(self.screen)
        if slot is not None:
            new_state = load_game(slot)
            if new_state:
                if show_confirm(self.screen, "Load Game",
                                f"Load save from slot {slot+1}? Current game will be lost."):
                    self._history.clear()
                    self._redo.clear()
                    self.state = new_state
                    self._flash_message(f"Loaded slot {slot+1}.")
            else:
                self._flash_message(f"Slot {slot+1} is empty.")

    def _flash_message(self, msg: str):
        sw, sh = self.screen.get_size()
        for _ in range(90):
            self._draw()
            box_w, box_h = max(300, int(sw * 0.28)), 44
            surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            surf.fill((22, 20, 42, 225))
            pygame.draw.rect(surf, C_ACCENT, surf.get_rect(), width=1, border_radius=8)
            lbl = _sfont(14).render(msg, True, C_TEXT)
            surf.blit(lbl, (box_w // 2 - lbl.get_width() // 2,
                            box_h // 2 - lbl.get_height() // 2))
            self.screen.blit(surf, (sw // 2 - box_w // 2, sh - 70))
            pygame.display.flip()
            self.clock.tick(60)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        sw, sh = self.screen.get_size()
        ui_state = {
            'action_mode': self.action_mode,
            'wall_orientation': self.wall_orientation,
            'player_names': self.player_names,
        }
        vms = self.valid_moves if self.selected_cell else []
        self.renderer.draw(
            self.state, vms,
            self.selected_cell,
            self.wall_preview, self.wall_preview_ok,
            self.action_mode, ui_state
        )
        if self._ai_thinking:
            pid = self.state.current_player
            name = self.player_names.get(pid, f"Player {pid+1}")
            box_w = max(220, int(sw * 0.22))
            s = pygame.Surface((box_w, 38), pygame.SRCALPHA)
            s.fill((16, 14, 32, 215))
            pygame.draw.rect(s, C_ACCENT, s.get_rect(), width=1, border_radius=7)
            lbl = _sfont(13).render(f"{name} is thinking…", True, C_TEXT2)
            s.blit(lbl, (box_w // 2 - lbl.get_width() // 2, 19 - lbl.get_height() // 2))
            self.screen.blit(s, (sw // 2 - box_w // 2, 14))
        pygame.display.flip()
