"""
tests/test_game.py - Unit tests using Python built-in unittest
Run: python tests/test_game.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from quoridor.game import GameState, Wall, MoveAction, WallAction, BOARD_SIZE, NUM_WALLS

MID = BOARD_SIZE // 2

class TestInitialState(unittest.TestCase):
    def setUp(self): self.g = GameState(2)
    def test_player0_start(self): self.assertEqual(self.g.players[0].pos, (0, MID))
    def test_player1_start(self): self.assertEqual(self.g.players[1].pos, (BOARD_SIZE-1, MID))
    def test_wall_counts(self): [self.assertEqual(p.walls_remaining, NUM_WALLS) for p in self.g.players]
    def test_no_walls(self): self.assertEqual(len(self.g.walls), 0)
    def test_current_player(self): self.assertEqual(self.g.current_player, 0)
    def test_no_winner(self): self.assertIsNone(self.g.winner)
    def test_4player(self):
        g4 = GameState(4)
        self.assertEqual(g4.players[2].pos, (MID, 0))
        self.assertEqual(g4.players[3].pos, (MID, BOARD_SIZE-1))

class TestMovement(unittest.TestCase):
    def setUp(self): self.g = GameState(2)
    def test_can_move_down(self): self.assertIn((1, MID), self.g.legal_pawn_moves(0))
    def test_cannot_move_up(self): self.assertNotIn((-1, MID), self.g.legal_pawn_moves(0))
    def test_apply_moves_pawn(self):
        new = self.g.apply(MoveAction(0, (0, MID), (1, MID)))
        self.assertEqual(new.players[0].pos, (1, MID))
    def test_turn_advances(self):
        new = self.g.apply(MoveAction(0, (0, MID), (1, MID)))
        self.assertEqual(new.current_player, 1)
    def test_immutable(self):
        self.g.apply(MoveAction(0, (0, MID), (1, MID)))
        self.assertEqual(self.g.players[0].pos, (0, MID))
    def test_winner_on_goal(self):
        g = GameState(2); g.players[0].row = BOARD_SIZE-2; g.players[1].col = MID+1
        new = g.apply(MoveAction(0, g.players[0].pos, (BOARD_SIZE-1, MID)))
        self.assertEqual(new.winner, 0)

class TestWalls(unittest.TestCase):
    def setUp(self): self.g = GameState(2)
    def test_place_wall(self):
        new = self.g.apply(WallAction(0, Wall(3,3,True)))
        self.assertIn(Wall(3,3,True), new.walls)
    def test_reduces_count(self):
        new = self.g.apply(WallAction(0, Wall(3,3,True)))
        self.assertEqual(new.players[0].walls_remaining, NUM_WALLS-1)
    def test_oob_rejected(self): self.assertFalse(self.g.can_place_wall(Wall(BOARD_SIZE-1,0,True)))
    def test_overlap_rejected(self):
        new = self.g.apply(WallAction(0, Wall(3,3,True)))
        self.assertFalse(new.can_place_wall(Wall(3,3,True)))
    def test_cross_rejected(self):
        new = self.g.apply(WallAction(0, Wall(3,3,True)))
        self.assertFalse(new.can_place_wall(Wall(3,3,False)))
    def test_blocks_passage(self):
        new = self.g.apply(WallAction(0, Wall(3,3,True)))
        self.assertTrue(new._passage_blocked((3,3),(4,3)))
        self.assertFalse(new._passage_blocked((3,2),(4,2)))
    def test_no_walls_left(self):
        g = GameState(2); g.players[0].walls_remaining = 0
        self.assertFalse(g.can_place_wall(Wall(2,2,True), 0))

class TestPathfinding(unittest.TestCase):
    def setUp(self): self.g = GameState(2)
    def test_has_path(self): self.assertTrue(self.g.has_path_to_goal(0))
    def test_shortest_initial(self): self.assertEqual(self.g.shortest_path(0), BOARD_SIZE-1)
    def test_shortest_after_move(self):
        new = self.g.apply(MoveAction(0, (0,MID), (1,MID)))
        self.assertEqual(new.shortest_path(0), BOARD_SIZE-2)

class TestJumping(unittest.TestCase):
    def test_straight_jump(self):
        g = GameState(2); g.players[0].row=4; g.players[0].col=4
        g.players[1].row=5; g.players[1].col=4
        self.assertIn((6,4), g.legal_pawn_moves(0))
    def test_diagonal_jump(self):
        g = GameState(2); g.players[0].row=4; g.players[0].col=4
        g.players[1].row=5; g.players[1].col=4
        g._add_wall(Wall(5,4,True))
        moves = g.legal_pawn_moves(0)
        self.assertNotIn((6,4), moves)
        self.assertTrue((5,3) in moves or (5,5) in moves)

class TestSerialization(unittest.TestCase):
    def test_roundtrip(self):
        g = GameState(2)
        g = g.apply(MoveAction(0,(0,MID),(1,MID)))
        g = g.apply(WallAction(1, Wall(3,3,True)))
        r = GameState.deserialize(g.serialize())
        self.assertEqual(r.players[0].pos, g.players[0].pos)
        self.assertEqual(len(r.walls), len(g.walls))
        self.assertTrue(r._passage_blocked((3,3),(4,3)))

class TestAI(unittest.TestCase):
    def _check(self, diff):
        from quoridor.ai import QuoridorAI
        g = GameState(2)
        ai = QuoridorAI(0, diff)
        action = ai.choose_action(g)
        self.assertIsNotNone(action)
        if isinstance(action, MoveAction):
            self.assertIn(action.to_pos, g.legal_pawn_moves(0))
        else:
            self.assertTrue(g.can_place_wall(action.wall, 0))
    def test_easy(self): self._check('Easy')
    def test_medium(self): self._check('Medium')
    def test_hard(self): self._check('Hard')

if __name__ == '__main__':
    unittest.main(verbosity=2)
