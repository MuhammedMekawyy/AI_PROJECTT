"""
quoridor/ai.py
AI engine: Easy (random), Medium (greedy BFS), Hard (Minimax + Alpha-Beta).
"""
from __future__ import annotations
import random
import math
from typing import Optional, List, Tuple
from quoridor.game import GameState, MoveAction, WallAction, Wall, Action, BOARD_SIZE


# ---------------------------------------------------------------------------
# Difficulty constants
# ---------------------------------------------------------------------------
EASY   = "Easy"
MEDIUM = "Medium"
HARD   = "Hard"


# ---------------------------------------------------------------------------
# Heuristic
# ---------------------------------------------------------------------------
def _heuristic(state: GameState, ai_id: int) -> float:
    """
    Score from ai_id's perspective.
    Positive = good for AI.
    """
    opp_id = 1 - ai_id   # works for 2-player
    my_dist  = state.shortest_path(ai_id)
    opp_dist = state.shortest_path(opp_id)
    if my_dist == 0:
        return 10000.0
    if opp_dist == 0:
        return -10000.0
    # Prefer shorter own path, longer opponent path
    score = (opp_dist - my_dist) * 10
    # Bonus for being ahead (smaller row distance to goal)
    ai_player  = state.players[ai_id]
    opp_player = state.players[opp_id]
    score += (state.shortest_path(opp_id) - state.shortest_path(ai_id))
    # Small penalty for wasting walls
    score += ai_player.walls_remaining * 0.5
    return score


# ---------------------------------------------------------------------------
# Move ordering (put pawn moves first, then strategic walls)
# ---------------------------------------------------------------------------
def _ordered_actions(state: GameState, player_id: int, wall_limit: int = 10) -> List[Action]:
    """Return actions ordered for better alpha-beta pruning."""
    actions: List[Action] = []
    # Pawn moves (sorted by distance to goal — greedily forward first)
    player = state.players[player_id]
    moves = state.legal_pawn_moves(player_id)
    # sort: prefer moves that reduce BFS distance
    def move_score(pos):
        tmp = state._clone()
        tmp.players[player_id].row, tmp.players[player_id].col = pos
        return state.shortest_path(player_id) - tmp.shortest_path(player_id)
    moves.sort(key=move_score, reverse=True)
    for m in moves:
        actions.append(MoveAction(player_id, player.pos, m))

    # Wall placements (limited for speed)
    if player.walls_remaining > 0:
        walls = state.legal_walls(player_id)
        # Prioritise walls that increase opponent's BFS distance most
        opp_id = 1 - player_id
        def wall_score(w: Wall):
            tmp = state._clone()
            tmp._add_wall(w)
            return tmp.shortest_path(opp_id)
        walls.sort(key=wall_score, reverse=True)
        for w in walls[:wall_limit]:
            actions.append(WallAction(player_id, w))
    return actions


# ---------------------------------------------------------------------------
# Minimax with Alpha-Beta
# ---------------------------------------------------------------------------
def _minimax(state: GameState, depth: int, alpha: float, beta: float,
             maximising: bool, ai_id: int) -> float:
    if state.winner is not None:
        return 10000.0 if state.winner == ai_id else -10000.0
    if depth == 0:
        return _heuristic(state, ai_id)

    current = state.current_player
    actions = _ordered_actions(state, current, wall_limit=6 if depth > 1 else 10)
    if not actions:
        return _heuristic(state, ai_id)

    if maximising:
        value = -math.inf
        for action in actions:
            child = state.apply(action)
            value = max(value, _minimax(child, depth - 1, alpha, beta, False, ai_id))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = math.inf
        for action in actions:
            child = state.apply(action)
            value = min(value, _minimax(child, depth - 1, alpha, beta, True, ai_id))
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class QuoridorAI:
    def __init__(self, player_id: int, difficulty: str = MEDIUM):
        self.player_id = player_id
        self.difficulty = difficulty

    def choose_action(self, state: GameState) -> Action:
        if self.difficulty == EASY:
            return self._easy(state)
        elif self.difficulty == MEDIUM:
            return self._medium(state)
        else:
            return self._hard(state)

    # ------------------------------------------------------------------
    def _easy(self, state: GameState) -> Action:
        """Random legal move, slight bias toward forward pawn movement."""
        player = state.players[self.player_id]
        moves = state.legal_pawn_moves(self.player_id)
        # 80% of the time just move pawn forward
        if moves and random.random() < 0.80:
            # pick move that moves toward goal if possible
            goal_row = player.goal_row
            if goal_row is not None:
                direction = 1 if goal_row > player.row else -1
                forward = [(r, c) for r, c in moves
                           if (r - player.row) * direction > 0]
                if forward:
                    return MoveAction(self.player_id, player.pos, random.choice(forward))
            return MoveAction(self.player_id, player.pos, random.choice(moves))
        # Otherwise random wall or move
        walls = state.legal_walls(self.player_id)
        all_actions: List[Action] = (
            [MoveAction(self.player_id, player.pos, m) for m in moves] +
            [WallAction(self.player_id, w) for w in walls]
        )
        return random.choice(all_actions) if all_actions else MoveAction(
            self.player_id, player.pos, moves[0])

    # ------------------------------------------------------------------
    def _medium(self, state: GameState) -> Action:
        """
        Greedy 1-ply: always picks action maximising heuristic.
        Fast and decent.
        """
        player = state.players[self.player_id]
        best_score = -math.inf
        best_action: Optional[Action] = None

        # Pawn moves
        for pos in state.legal_pawn_moves(self.player_id):
            child = state.apply(MoveAction(self.player_id, player.pos, pos))
            score = _heuristic(child, self.player_id)
            if score > best_score:
                best_score = score
                best_action = MoveAction(self.player_id, player.pos, pos)

        # Only consider walls if we have many and are behind
        opp_id = 1 - self.player_id
        my_dist  = state.shortest_path(self.player_id)
        opp_dist = state.shortest_path(opp_id)
        if player.walls_remaining >= 3 and opp_dist < my_dist + 3:
            walls = state.legal_walls(self.player_id)
            # Only top 15 by opponent distance increase
            walls.sort(key=lambda w: _wall_impact(state, w, opp_id), reverse=True)
            for w in walls[:15]:
                child = state.apply(WallAction(self.player_id, w))
                score = _heuristic(child, self.player_id)
                if score > best_score:
                    best_score = score
                    best_action = WallAction(self.player_id, w)

        if best_action is None:
            moves = state.legal_pawn_moves(self.player_id)
            best_action = MoveAction(self.player_id, player.pos,
                                     moves[0] if moves else player.pos)
        return best_action

    # ------------------------------------------------------------------
    def _hard(self, state: GameState) -> Action:
        """
        Minimax depth 3 with Alpha-Beta pruning.
        Chooses best action at root.
        """
        player = state.players[self.player_id]
        depth = 3
        best_score = -math.inf
        best_action: Optional[Action] = None
        alpha = -math.inf
        beta  =  math.inf

        for action in _ordered_actions(state, self.player_id, wall_limit=8):
            child = state.apply(action)
            score = _minimax(child, depth - 1, alpha, beta, False, self.player_id)
            if score > best_score:
                best_score = score
                best_action = action
            alpha = max(alpha, best_score)

        if best_action is None:
            moves = state.legal_pawn_moves(self.player_id)
            best_action = MoveAction(self.player_id, player.pos,
                                     moves[0] if moves else player.pos)
        return best_action


def _wall_impact(state: GameState, wall: Wall, opp_id: int) -> int:
    """How much does this wall increase opponent's path?"""
    before = state.shortest_path(opp_id)
    state._add_wall(wall)
    after = state.shortest_path(opp_id)
    state._remove_wall(wall)
    return after - before
