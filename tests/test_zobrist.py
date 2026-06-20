"""Property tests for the incremental Zobrist hash in GameState.

Guards the highest-risk Phase 2 change: the incremental hash maintained in
make_move/undo_move must always equal the from-scratch recompute, and undo must
restore the previous hash exactly. A single missed XOR (e.g. forgetting the
captured piece) would fail these tests.
"""

import random

from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Piece, PieceType, Player
from jungle_game.engine.ai import compute_zobrist_hash
from conftest import make_game_with_pieces


def _make(specs, current_player=Player.BLUE):
    pieces = [Piece(t, p, c, r) for (t, p, c, r) in specs]
    return make_game_with_pieces(pieces, current_player)


class TestIncrementalZobrist:
    def test_incremental_equals_recompute_random_positions(self):
        rnd = random.Random(4242)
        types = list(PieceType)
        for _ in range(200):
            specs = []
            used = set()
            for _ in range(rnd.randint(2, 12)):
                for _ in range(20):
                    c, r = rnd.randint(0, 6), rnd.randint(0, 8)
                    if (c, r) not in used:
                        used.add((c, r))
                        specs.append((rnd.choice(types),
                                      rnd.choice([Player.BLUE, Player.RED]),
                                      c, r))
                        break
            if not any(s[1] == Player.BLUE for s in specs):
                continue
            if not any(s[1] == Player.RED for s in specs):
                continue
            g = _make(specs, rnd.choice([Player.BLUE, Player.RED]))
            assert g.zobrist_hash == compute_zobrist_hash(g), \
                "incremental hash must equal recompute on constructed positions"

    def test_incremental_equals_recompute_during_random_play(self):
        """After every make_move in random play, incremental == recompute.

        Random play exercises captures, water entry, and river jumps.
        """
        rnd = random.Random(99)
        for game_idx in range(10):
            g = GameState(first_player=rnd.choice([Player.BLUE, Player.RED]))
            for _ in range(60):
                if g.is_over:
                    break
                moves = g.get_legal_moves()
                if not moves:
                    break
                before = g.zobrist_hash
                move = rnd.choice(moves)
                g.make_move(move[0], move[1])
                assert g.zobrist_hash == compute_zobrist_hash(g), \
                    f"hash diverged after move {move} (game {game_idx})"
                # Undo restores the pre-move hash exactly.
                assert g.undo_move() is True
                assert g.zobrist_hash == before, \
                    f"undo did not restore hash after move {move}"
                assert g.zobrist_hash == compute_zobrist_hash(g)
                # Redo the same move to keep the game progressing.
                g.make_move(move[0], move[1])

    def test_undo_restores_hash_after_captures_and_jumps(self):
        """Targeted: make every capture/jump move and verify undo restores hash."""
        g = GameState()
        for _ in range(80):
            if g.is_over:
                break
            moves = g.get_legal_moves()
            if not moves:
                break
            # Prefer forcing moves (captures and den-entries) to stress the hash.
            forcing = [m for m in moves if g.piece_at(m[1][0], m[1][1]) is not None]
            move = forcing[0] if forcing else moves[0]
            before = g.zobrist_hash
            g.make_move(move[0], move[1])
            assert g.zobrist_hash == compute_zobrist_hash(g)
            assert g.undo_move() is True
            assert g.zobrist_hash == before, "undo did not restore hash after forcing move"
            assert g.zobrist_hash == compute_zobrist_hash(g)
            g.make_move(move[0], move[1])

    def test_copy_preserves_hash(self):
        g = GameState()
        m = g.get_legal_moves()[0]
        g.make_move(m[0], m[1])
        c = g.copy()
        assert c.zobrist_hash == g.zobrist_hash, "copy must preserve the hash"
        assert c.zobrist_hash == compute_zobrist_hash(c)

    def test_conftest_helper_sets_hash(self):
        """make_game_with_pieces bypasses __init__ but calls _rebuild_index,
        which must set a valid (non-zero, recompute-consistent) hash."""
        g = _make([(PieceType.LION, Player.BLUE, 3, 4),
                   (PieceType.ELEPHANT, Player.RED, 0, 6)])
        assert g.zobrist_hash != 0
        assert g.zobrist_hash == compute_zobrist_hash(g)

    def test_side_to_move_affects_hash(self):
        """Same piece placement but different side to move must hash differently."""
        pieces = [Piece(PieceType.LION, Player.BLUE, 3, 4),
                  Piece(PieceType.ELEPHANT, Player.RED, 0, 6)]
        g_blue = make_game_with_pieces([p.copy() for p in pieces], Player.BLUE)
        g_red = make_game_with_pieces([p.copy() for p in pieces], Player.RED)
        assert g_blue.zobrist_hash != g_red.zobrist_hash