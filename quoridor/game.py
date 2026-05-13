"""
quoridor/game.py
Core game logic: board state, rule enforcement, pathfinding, move generation.
"""
from __future__ import annotations
import copy
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BOARD_SIZE = 9          # 9x9 cell grid
NUM_WALLS   = 10        # walls per player (2-player)

# Directions (row_delta, col_delta)
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# Player colours (for rendering hints)
PLAYER_COLORS = [(220, 100, 60), (60, 190, 220), (220, 60, 150), (60, 220, 100)]

# ---------------------------------------------------------------------------
# Wall representation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Wall:
    """
    A wall segment.
    row, col : top-left anchor cell (0-based)
    horizontal : True = horizontal wall (blocks vertical movement between
                 row,col and row+1,col  AND  row,col+1 and row+1,col+1)
                 False = vertical wall (blocks horizontal movement)
    """
    row: int
    col: int
    horizontal: bool   # True = H-wall, False = V-wall

    def cells_blocked(self) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
        """Return list of (cell_a, cell_b) pairs that this wall separates."""
        r, c = self.row, self.col
        if self.horizontal:
            # blocks passage between (r,c)↔(r+1,c) and (r,c+1)↔(r+1,c+1)
            return [((r, c), (r+1, c)), ((r, c+1), (r+1, c+1))]
        else:
            # blocks passage between (r,c)↔(r,c+1) and (r+1,c)↔(r+1,c+1)
            return [((r, c), (r, c+1)), ((r+1, c), (r+1, c+1))]

    def occupied_slots(self) -> List[Tuple[int,int,bool]]:
        """The two 1-cell slots this wall occupies (for overlap detection)."""
        r, c = self.row, self.col
        return [(r, c, self.horizontal), (r, c+1 if self.horizontal else r+1, self.horizontal)]

# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
@dataclass
class Player:
    player_id: int          # 0-based
    row: int
    col: int
    walls_remaining: int = NUM_WALLS
    goal_row: Optional[int] = None   # None means "any row" (set by GameState)

    @property
    def pos(self) -> Tuple[int,int]:
        return (self.row, self.col)

# ---------------------------------------------------------------------------
# Move types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MoveAction:
    player_id: int
    from_pos: Tuple[int,int]
    to_pos: Tuple[int,int]

@dataclass(frozen=True)
class WallAction:
    player_id: int
    wall: Wall

Action = MoveAction | WallAction

# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------
class GameState:
    """
    Full game state.  Supports 2 or 4 players.
    """

    def __init__(self, num_players: int = 2):
        assert num_players in (2, 4), "Only 2 or 4 players supported"
        self.num_players = num_players
        self.walls: Set[Wall] = set()
        self._wall_slots: Set[Tuple[int,int,bool]] = set()  # fast overlap check
        self._blocked: Set[frozenset] = set()               # blocked cell pairs
        self.current_player: int = 0
        self.winner: Optional[int] = None
        self.move_count: int = 0
        self.players: List[Player] = self._init_players(num_players)

    # ------------------------------------------------------------------
    def _init_players(self, n: int) -> List[Player]:
        s = BOARD_SIZE - 1
        m = BOARD_SIZE // 2
        walls_each = NUM_WALLS if n == 2 else 5
        if n == 2:
            p0 = Player(0, 0, m, walls_each, goal_row=s)
            p1 = Player(1, s, m, walls_each, goal_row=0)
            return [p0, p1]
        else:
            p0 = Player(0, 0, m, walls_each, goal_row=s)
            p1 = Player(1, s, m, walls_each, goal_row=0)
            p2 = Player(2, m, 0, walls_each, goal_row=None)   # goal: any col=s
            p3 = Player(3, m, s, walls_each, goal_row=None)   # goal: any col=0
            p2.goal_col = s
            p3.goal_col = 0
            return [p0, p1, p2, p3]

    # ------------------------------------------------------------------
    # Adjacency / path helpers
    # ------------------------------------------------------------------
    def _passage_blocked(self, a: Tuple[int,int], b: Tuple[int,int]) -> bool:
        return frozenset((a, b)) in self._blocked

    def neighbors(self, pos: Tuple[int,int]) -> List[Tuple[int,int]]:
        """Reachable orthogonal neighbors ignoring other pawns."""
        r, c = pos
        result = []
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                if not self._passage_blocked((r, c), (nr, nc)):
                    result.append((nr, nc))
        return result

    def _pawn_at(self, pos: Tuple[int,int]) -> Optional[int]:
        for p in self.players:
            if p.pos == pos and p.player_id != self.current_player:
                return p.player_id
        return None

    def legal_pawn_moves(self, player_id: Optional[int] = None) -> List[Tuple[int,int]]:
        """Return list of legal destination cells for given player (default current)."""
        if player_id is None:
            player_id = self.current_player
        player = self.players[player_id]
        r, c = player.pos
        moves = []
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
                continue
            if self._passage_blocked((r, c), (nr, nc)):
                continue
            occ = self._pawn_at((nr, nc))
            if occ is None:
                moves.append((nr, nc))
            else:
                # Jumping logic
                jr, jc = nr + dr, nc + dc
                if (0 <= jr < BOARD_SIZE and 0 <= jc < BOARD_SIZE
                        and not self._passage_blocked((nr, nc), (jr, jc))
                        and self._pawn_at((jr, jc)) is None):
                    moves.append((jr, jc))
                else:
                    # Diagonal jumps when straight jump blocked
                    for ddr, ddc in DIRECTIONS:
                        if (ddr, ddc) == (dr, dc) or (ddr, ddc) == (-dr, -dc):
                            continue
                        sr, sc = nr + ddr, nc + ddc
                        if (0 <= sr < BOARD_SIZE and 0 <= sc < BOARD_SIZE
                                and not self._passage_blocked((nr, nc), (sr, sc))
                                and self._pawn_at((sr, sc)) is None):
                            moves.append((sr, sc))
        return list(set(moves))

    # ------------------------------------------------------------------
    # BFS path check
    # ------------------------------------------------------------------
    def has_path_to_goal(self, player_id: int) -> bool:
        player = self.players[player_id]
        start = player.pos
        visited = {start}
        q = deque([start])
        while q:
            pos = q.popleft()
            if self._at_goal(pos, player_id):
                return True
            for nb in self.neighbors(pos):
                if nb not in visited:
                    visited.add(nb)
                    q.append(nb)
        return False

    def _at_goal(self, pos: Tuple[int,int], player_id: int) -> bool:
        player = self.players[player_id]
        if player_id < 2:
            return pos[0] == player.goal_row
        else:
            goal_col = getattr(player, 'goal_col', None)
            return pos[1] == goal_col

    def shortest_path(self, player_id: int) -> int:
        """BFS distance to goal (used by AI heuristic). Returns large number if no path."""
        player = self.players[player_id]
        start = player.pos
        visited = {start}
        q = deque([(start, 0)])
        while q:
            pos, dist = q.popleft()
            if self._at_goal(pos, player_id):
                return dist
            for nb in self.neighbors(pos):
                if nb not in visited:
                    visited.add(nb)
                    q.append((nb, dist + 1))
        return 9999

    # ------------------------------------------------------------------
    # Wall placement
    # ------------------------------------------------------------------
    def _wall_overlaps(self, wall: Wall) -> bool:
        for slot in wall.occupied_slots():
            if slot in self._wall_slots:
                return True
        # Check crossing: H-wall crosses V-wall at same anchor
        cross = Wall(wall.row, wall.col, not wall.horizontal)
        if cross in self.walls:
            return True
        return False

    def _wall_in_bounds(self, wall: Wall) -> bool:
        r, c = wall.row, wall.col
        max_rc = BOARD_SIZE - 2   # 0-indexed, max anchor = 7 for 9-cell board
        return 0 <= r <= max_rc and 0 <= c <= max_rc

    def legal_walls(self, player_id: Optional[int] = None) -> List[Wall]:
        """Generate all legal wall placements for player. Expensive — use for AI."""
        if player_id is None:
            player_id = self.current_player
        if self.players[player_id].walls_remaining == 0:
            return []
        result = []
        for r in range(BOARD_SIZE - 1):
            for c in range(BOARD_SIZE - 1):
                for horiz in (True, False):
                    w = Wall(r, c, horiz)
                    if self.can_place_wall(w, player_id):
                        result.append(w)
        return result

    def can_place_wall(self, wall: Wall, player_id: Optional[int] = None) -> bool:
        if player_id is None:
            player_id = self.current_player
        if self.players[player_id].walls_remaining <= 0:
            return False
        if not self._wall_in_bounds(wall):
            return False
        if self._wall_overlaps(wall):
            return False
        # Temporarily place and check path for all players
        self._add_wall(wall)
        ok = all(self.has_path_to_goal(pid) for pid in range(self.num_players))
        self._remove_wall(wall)
        return ok

    def _add_wall(self, wall: Wall):
        self.walls.add(wall)
        for slot in wall.occupied_slots():
            self._wall_slots.add(slot)
        for pair in wall.cells_blocked():
            self._blocked.add(frozenset(pair))

    def _remove_wall(self, wall: Wall):
        self.walls.discard(wall)
        for slot in wall.occupied_slots():
            self._wall_slots.discard(slot)
        for pair in wall.cells_blocked():
            self._blocked.discard(frozenset(pair))

    # ------------------------------------------------------------------
    # Apply / undo actions
    # ------------------------------------------------------------------
    def apply(self, action: Action) -> 'GameState':
        """Return a new GameState with the action applied."""
        new = self._clone()
        new._apply_inplace(action)
        return new

    def _apply_inplace(self, action: Action):
        if isinstance(action, MoveAction):
            p = self.players[action.player_id]
            p.row, p.col = action.to_pos
        elif isinstance(action, WallAction):
            p = self.players[action.player_id]
            p.walls_remaining -= 1
            self._add_wall(action.wall)
        self._check_winner()
        self.current_player = (self.current_player + 1) % self.num_players
        self.move_count += 1

    def _check_winner(self):
        for pid in range(self.num_players):
            if self._at_goal(self.players[pid].pos, pid):
                self.winner = pid
                return

    def _clone(self) -> 'GameState':
        new = GameState.__new__(GameState)
        new.num_players = self.num_players
        new.walls = set(self.walls)
        new._wall_slots = set(self._wall_slots)
        new._blocked = set(self._blocked)
        new.current_player = self.current_player
        new.winner = self.winner
        new.move_count = self.move_count
        new.players = [copy.copy(p) for p in self.players]
        return new

    # ------------------------------------------------------------------
    def serialize(self) -> dict:
        """Serialize to dict for save/load."""
        return {
            'num_players': self.num_players,
            'current_player': self.current_player,
            'winner': self.winner,
            'move_count': self.move_count,
            'players': [
                {'player_id': p.player_id, 'row': p.row, 'col': p.col,
                 'walls_remaining': p.walls_remaining,
                 'goal_row': p.goal_row,
                 'goal_col': getattr(p, 'goal_col', None)}
                for p in self.players
            ],
            'walls': [
                {'row': w.row, 'col': w.col, 'horizontal': w.horizontal}
                for w in self.walls
            ]
        }

    @classmethod
    def deserialize(cls, data: dict) -> 'GameState':
        g = cls(data['num_players'])
        g.current_player = data['current_player']
        g.winner = data['winner']
        g.move_count = data['move_count']
        for i, pd in enumerate(data['players']):
            p = g.players[i]
            p.row = pd['row']; p.col = pd['col']
            p.walls_remaining = pd['walls_remaining']
            p.goal_row = pd['goal_row']
            if pd.get('goal_col') is not None:
                p.goal_col = pd['goal_col']
        # Rebuild walls
        for wd in data['walls']:
            w = Wall(wd['row'], wd['col'], wd['horizontal'])
            g._add_wall(w)
        return g
