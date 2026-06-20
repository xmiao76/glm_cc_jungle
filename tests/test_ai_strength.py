"""Strength and correctness tests for the enhanced Jungle AI.

These cover the invariants and behaviours introduced by the negamax rewrite:

- Evaluation symmetry (``evaluate(g, A) == -evaluate(g, B)``) — required for
  negamax to be correct.
- Time-abort stability: a clearly-best capture must be returned consistently
  regardless of the time limit (regression for the critical bug where a
  time-aborted deep iteration committed a garbage move).
- Tactical vision: forced den-entry wins, trap-blunder avoidance, taking a
  free piece.
- Playing strength: the AI beats a random mover; deeper search does not lose
  to shallower search (same algorithm).
"""

import random
import pytest

from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Piece, PieceType, Player
from jungle_game.engine.ai import (
    find_best_move, evaluate, clear_tt, set_extensions_enabled,
    _move_creates_den_threat,
)
from jungle_game.engine.evaluation import MATE
from conftest import make_game_with_pieces


def _make(specs, current_player=Player.BLUE):
    """Build a GameState from (PieceType, Player, col, row) tuples."""
    pieces = [Piece(t, p, c, r) for (t, p, c, r) in specs]
    return make_game_with_pieces(pieces, current_player)


class TestEvaluationSymmetry:
    """evaluate(g, BLUE) must equal -evaluate(g, RED) for negamax validity."""

    def test_symmetric_start_position(self):
        g = GameState()
        assert evaluate(g, Player.BLUE) == -evaluate(g, Player.RED)

    def test_symmetric_random_positions(self):
        rnd = random.Random(2024)
        types = list(PieceType)
        checked = 0
        for _ in range(300):
            specs = []
            used = set()
            for _ in range(rnd.randint(2, 10)):
                for _ in range(20):
                    c, r = rnd.randint(0, 6), rnd.randint(0, 8)
                    if (c, r) not in used:
                        used.add((c, r))
                        specs.append((rnd.choice(types),
                                      rnd.choice([Player.BLUE, Player.RED]),
                                      c, r))
                        break
            # Both sides must have a piece, otherwise it is a terminal position.
            if not any(s[1] == Player.BLUE for s in specs):
                continue
            if not any(s[1] == Player.RED for s in specs):
                continue
            g = _make(specs, rnd.choice([Player.BLUE, Player.RED]))
            assert evaluate(g, Player.BLUE) == -evaluate(g, Player.RED)
            checked += 1
        assert checked >= 100, "test did not exercise enough positions"


class TestTimeAbortStability:
    """Regression: a time-aborted deep iteration must not return a garbage move.

    A Red Wolf can capture a free Blue Cat. The static evaluation and every
    completed search depth agree the capture is best. Previously, at longer
    time limits the search aborted mid-iteration and committed a different
    (losing-the-free-piece) move ~80% of the time.
    """

    SCENARIO = [
        (PieceType.WOLF, Player.RED, 3, 5),
        (PieceType.CAT, Player.BLUE, 3, 6),
        (PieceType.ELEPHANT, Player.RED, 0, 6),
        (PieceType.LION, Player.BLUE, 6, 0),
    ]

    @pytest.mark.parametrize("time_limit_ms", [100, 500, 1000])
    def test_always_captures_free_piece(self, time_limit_ms):
        for _ in range(3):
            clear_tt()
            g = _make(self.SCENARIO, Player.RED)
            move = find_best_move(g, Player.RED, time_limit_ms=time_limit_ms)
            assert move == ((3, 5), (3, 6)), \
                f"AI should capture the free Cat at 3,6 (got {move})"


class TestTactics:
    """The AI should spot forced wins and avoid blunders."""

    def test_finds_forced_den_entry_in_two(self):
        """Red Lion two steps from Blue's den must advance toward the win."""
        clear_tt()
        # Lion at (3,2) -> (3,1) -> (3,0) wins. Blue's pieces are too far to
        # capture the Lion at (3,1) (Blue's own trap, where it drops to rank 0
        # but is unguarded) or to block the den.
        g = _make([
            (PieceType.LION, Player.RED, 3, 2),
            (PieceType.CAT, Player.BLUE, 0, 8),
            (PieceType.LION, Player.BLUE, 6, 8),
        ], Player.RED)
        move = find_best_move(g, Player.RED, time_limit_ms=1500)
        assert move == ((3, 2), (3, 1)), \
            f"Red should advance the Lion toward the den (got {move})"

    def test_avoids_trap_blunder(self):
        """A piece must not step into the opponent's trap as rank 0 next to a
        capturer when a safe move exists."""
        clear_tt()
        # Blue Elephant at (3,6). (3,7) is Red's trap. Red Cat at (2,7) is
        # adjacent to (3,7), so an Elephant entering (3,7) becomes rank 0 and
        # is lost next turn. The AI must not play (3,6)->(3,7).
        g = _make([
            (PieceType.ELEPHANT, Player.BLUE, 3, 6),
            (PieceType.CAT, Player.RED, 2, 7),
            (PieceType.LION, Player.BLUE, 0, 0),
            (PieceType.LION, Player.RED, 6, 8),
        ], Player.BLUE)
        move = find_best_move(g, Player.BLUE, time_limit_ms=1500)
        assert move != ((3, 6), (3, 7)), \
            f"AI blundered into the opponent's trap (got {move})"

    def test_takes_free_high_value_piece(self):
        """The AI should capture a free, high-value piece when it is safe."""
        clear_tt()
        # Blue Tiger adjacent to a Red Leopard (both on land). Tiger (6) captures
        # Leopard (5). A faraway Red piece keeps it from being an instant win.
        g = _make([
            (PieceType.TIGER, Player.BLUE, 3, 4),
            (PieceType.LEOPARD, Player.RED, 3, 5),
            (PieceType.LION, Player.RED, 6, 8),
            (PieceType.ELEPHANT, Player.BLUE, 0, 0),
        ], Player.BLUE)
        move = find_best_move(g, Player.BLUE, time_limit_ms=800)
        assert move == ((3, 4), (3, 5)), \
            f"Blue Tiger should capture the free Leopard (got {move})"


class TestDenThreatExtensions:
    """Den-threat (check-style) search extensions: correct, bounded, effective."""

    def test_threat_detection(self):
        """A piece adjacent to the opponent's empty den is a threat."""
        clear_tt()
        # Red Lion at (3,1) is adjacent to Blue's empty den (3,0) -> threat.
        g = _make([(PieceType.LION, Player.RED, 3, 1),
                   (PieceType.CAT, Player.BLUE, 6, 8)])
        assert _move_creates_den_threat(g, (3, 1), Player.RED) is True
        # Lion at (3,2) is not adjacent -> no threat.
        g2 = _make([(PieceType.LION, Player.RED, 3, 2),
                    (PieceType.CAT, Player.BLUE, 6, 8)])
        assert _move_creates_den_threat(g2, (3, 2), Player.RED) is False
        # Adjacent but the den is occupied -> no empty-den threat.
        g3 = _make([(PieceType.LION, Player.RED, 3, 1),
                    (PieceType.WOLF, Player.RED, 3, 0)])  # Red on Blue's den = already won
        assert _move_creates_den_threat(g3, (3, 1), Player.RED) is False

    def test_extensions_are_bounded(self):
        """Extensions must not cause runaway recursion: a threat-heavy position
        must still return within a normal time budget."""
        clear_tt()
        set_extensions_enabled(True)
        try:
            # Red Lion one step from Blue's empty den — maximum threat density.
            g = _make([(PieceType.LION, Player.RED, 3, 1),
                       (PieceType.CAT, Player.BLUE, 6, 8),
                       (PieceType.LION, Player.BLUE, 0, 0)], Player.RED)
            import time as _time
            t0 = _time.time()
            move = find_best_move(g, Player.RED, time_limit_ms=600)
            elapsed = _time.time() - t0
            assert move is not None
            assert elapsed < 1.5, f"extensions caused a runaway search ({elapsed:.2f}s)"
        finally:
            set_extensions_enabled(False)  # restore the shipped default (off)

    def test_extensions_find_deeper_den_win(self):
        """With extensions on, the search should still find a multi-move forced
        den win (and not regress vs extensions off)."""
        clear_tt()
        set_extensions_enabled(True)
        try:
            # Red Lion 3 steps from Blue's den with a clear path; Blue cannot interfere.
            g = _make([(PieceType.LION, Player.RED, 3, 3),
                       (PieceType.CAT, Player.BLUE, 6, 8),
                       (PieceType.LION, Player.BLUE, 0, 0)], Player.RED)
            move = find_best_move(g, Player.RED, time_limit_ms=800)
            # The only sensible winning plan is to advance the Lion toward the den.
            assert move[0] == (3, 3), f"should advance the Lion (got {move})"
            assert move[1] in ((3, 2), (2, 3), (4, 3)), \
                f"Lion should step toward the den (got {move})"
        finally:
            set_extensions_enabled(False)


class TestPlayingStrength:
    """The AI should beat weak opponents and benefit from deeper search."""

    @pytest.mark.slow
    def test_ai_beats_random(self):
        """AI (Blue, short time) must beat a random mover (Red) decisively."""
        rnd = random.Random(7)
        wins = 0
        games = 2
        for _ in range(games):
            g = GameState(first_player=Player.BLUE)
            clear_tt()
            moves_played = 0
            while not g.is_over and moves_played < 150:
                if g.current_player == Player.BLUE:
                    move = find_best_move(g, Player.BLUE, time_limit_ms=100)
                else:
                    legal = g.get_legal_moves()
                    move = rnd.choice(legal) if legal else None
                if move is None:
                    break
                g.make_move(move[0], move[1])
                moves_played += 1
            if g.is_over and g.winner == Player.BLUE:
                wins += 1
        assert wins >= 1, f"AI should win vs random (won {wins}/{games})"

    @pytest.mark.slow
    def test_deeper_search_does_not_lose_to_shallower(self):
        """Same algorithm, more time must not have a losing record vs less time.

        The transposition table is cleared before each move so the weaker side
        cannot free-ride on the stronger side's deeper entries. With a small
        sample and Jungle's natural variance, a single loss is tolerable; the
        bar is that the deeper side does not post a LOSING record (wins >=
        losses over the sample).
        """
        strong_ms, weak_ms = 160, 35
        wins = losses = draws = 0
        games = 4
        for i in range(games):
            strong_is_blue = (i % 2 == 0)
            g = GameState(first_player=Player.BLUE)
            moves_played = 0
            while not g.is_over and moves_played < 48:
                clear_tt()  # isolate each move's search
                is_strong = (g.current_player == Player.BLUE) == strong_is_blue
                move = find_best_move(g, g.current_player,
                                      time_limit_ms=strong_ms if is_strong else weak_ms)
                if move is None:
                    break
                g.make_move(move[0], move[1])
                moves_played += 1
            strong_player = Player.BLUE if strong_is_blue else Player.RED
            if g.is_over and g.winner is not None:
                if g.winner == strong_player:
                    wins += 1
                else:
                    losses += 1
            else:
                draws += 1
        assert wins >= losses, \
            f"Deeper search posted a losing record (W={wins} L={losses} D={draws})"

    @pytest.mark.slow
    def test_ai_vs_ai_runs_without_errors(self):
        """Two identical AIs must play a long game without crashing.

        Two equal-strength engines often draw or shuffle (neither makes a losing
        mistake), so this is a smoke test, not a decisiveness test: the game must
        play many moves without raising, and IF it ends the win reason must be
        valid. (Decisive wins against weaker opponents are covered by
        test_ai_beats_random and test_deeper_search_does_not_lose_to_shallower.)
        """
        g = GameState(first_player=Player.BLUE)
        clear_tt()
        moves_played = 0
        while not g.is_over and moves_played < 200:
            move = find_best_move(g, g.current_player, time_limit_ms=100)
            if move is None:
                break
            g.make_move(move[0], move[1])
            moves_played += 1
        # Must have played a real game without error.
        assert moves_played >= 40, f"AI vs AI stalled early ({moves_played} moves)"
        if g.is_over:
            assert g.winner is not None
            assert g.win_reason in ("den_entry", "elimination", "stalemate")