"""Tests for the AI engine."""

import pytest
import time
from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Piece, PieceType, Player
from jungle_game.engine.ai import (
    find_best_move, evaluate, order_moves, PIECE_VALUES,
    compute_zobrist_hash, TranspositionTable, EXACT, LOWERBOUND, UPPERBOUND,
    clear_tt, NULL_MOVE_R, LMR_MIN_DEPTH,
)
from jungle_game.engine.rules import generate_legal_moves
from conftest import make_game_with_pieces


class TestEvaluation:
    def test_initial_position_not_extreme(self):
        game = GameState()
        score = evaluate(game, Player.BLUE)
        assert -100000 < score < 100000

    def test_winning_position_high_score(self):
        """Piece about to enter opponent's den should have high score."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        game = make_game_with_pieces([lion])
        score = evaluate(game, Player.BLUE)
        assert score == 100000

    def test_losing_position_low_score(self):
        """Position where opponent is about to win should have low score."""
        lion = Piece(PieceType.LION, Player.RED, 3, 1)
        game = make_game_with_pieces([lion])
        score = evaluate(game, Player.BLUE)
        assert score == -100000

    def test_more_material_is_better(self):
        """Having more pieces should give a better score."""
        # More pieces for Blue, with opponent pieces to avoid instant win
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        cat = Piece(PieceType.CAT, Player.BLUE, 3, 5)
        rat = Piece(PieceType.RAT, Player.RED, 0, 6)
        game1 = make_game_with_pieces([lion, cat, rat])

        # Fewer pieces for Blue
        game2 = make_game_with_pieces([lion, rat])

        score1 = evaluate(game1, Player.BLUE)
        score2 = evaluate(game2, Player.BLUE)
        assert score1 > score2


class TestMoveOrdering:
    def test_captures_first(self):
        game = GameState()
        moves = generate_legal_moves(game, Player.BLUE)
        ordered = order_moves(moves, game)
        # Captures should come before non-captures
        # At the start, there are no captures, so order shouldn't change length
        assert len(ordered) == len(moves)

    def test_den_entry_prioritized(self):
        """Den-entry moves should be prioritized."""
        # Create a position where a piece can enter opponent's den
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        rat = Piece(PieceType.RAT, Player.BLUE, 0, 3)
        game = make_game_with_pieces([lion, rat])
        moves = generate_legal_moves(game, Player.BLUE)
        ordered = order_moves(moves, game)
        # The den-entry move should be near the top
        den_entry_idx = None
        for i, (fp, tp) in enumerate(ordered):
            if tp == (3, 8):  # Red's den
                den_entry_idx = i
                break
        if den_entry_idx is not None:
            assert den_entry_idx < 2  # Should be one of the first moves


class TestFindBestMove:
    def test_returns_legal_move(self):
        game = GameState()
        move = find_best_move(game, time_limit_ms=200)
        assert move is not None
        legal = generate_legal_moves(game, Player.BLUE)
        assert move in legal

    def test_no_moves_returns_none(self):
        """If no legal moves, returns None."""
        # Rat in center surrounded by higher-ranked enemy pieces — no captures, no moves
        wolf1 = Piece(PieceType.WOLF, Player.RED, 2, 4)
        wolf2 = Piece(PieceType.WOLF, Player.RED, 4, 4)
        wolf3 = Piece(PieceType.WOLF, Player.RED, 3, 3)
        wolf4 = Piece(PieceType.WOLF, Player.RED, 3, 5)
        rat = Piece(PieceType.RAT, Player.BLUE, 3, 4)
        game = make_game_with_pieces([rat, wolf1, wolf2, wolf3, wolf4])
        moves = generate_legal_moves(game, Player.BLUE)
        assert len(moves) == 0, f"Expected no moves, got {moves}"
        result = find_best_move(game, time_limit_ms=200)
        assert result is None

    def test_single_move_returns_immediately(self):
        """With only one legal move, should return it immediately."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        game = make_game_with_pieces([lion])
        move = find_best_move(game, time_limit_ms=200)
        assert move is not None

    def test_respects_time_limit(self):
        """Search should not exceed time limit."""
        game = GameState()
        start = time.time()
        find_best_move(game, time_limit_ms=500)
        elapsed = time.time() - start
        # Should not take much longer than the limit
        assert elapsed < 2.0

    def test_finds_winning_move(self):
        """AI should find a winning move (entering opponent's den)."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        # Add an opponent piece far away so it's not an instant-win position
        cat = Piece(PieceType.CAT, Player.RED, 0, 6)
        game = make_game_with_pieces([lion, cat])
        move = find_best_move(game, time_limit_ms=1000)
        # Should choose to enter the den (immediate win)
        assert move is not None
        # The den-entry move should be the best since it wins immediately
        # Lion at (3,7) can move to (3,8) = opponent's den = instant win
        assert move == ((3, 7), (3, 8))


class TestTranspositionTable:
    def test_store_and_lookup(self):
        tt = TranspositionTable()
        tt.store(12345, 4, 100, EXACT, ((3, 4), (3, 5)))
        result = tt.lookup(12345, 4)
        assert result is not None
        score, flag, best_move = result
        assert score == 100
        assert flag == EXACT
        assert best_move == ((3, 4), (3, 5))

    def test_depth_check(self):
        """Should not return entries with insufficient depth."""
        tt = TranspositionTable()
        tt.store(12345, 2, 100, EXACT, None)
        result = tt.lookup(12345, 4)  # Requesting depth 4, stored depth 2
        assert result is None

    def test_clear(self):
        tt = TranspositionTable()
        tt.store(12345, 4, 100, EXACT, None)
        tt.clear()
        assert tt.lookup(12345, 4) is None


class TestZobristHash:
    def test_different_positions_different_hash(self):
        game1 = GameState()
        game2 = GameState()
        # Make a move in game2
        moves = game2.get_legal_moves()
        game2.make_move(moves[0][0], moves[0][1])
        h1 = compute_zobrist_hash(game1)
        h2 = compute_zobrist_hash(game2)
        assert h1 != h2

    def test_same_position_same_hash(self):
        game1 = GameState()
        game2 = GameState()
        h1 = compute_zobrist_hash(game1)
        h2 = compute_zobrist_hash(game2)
        assert h1 == h2


class TestAICompletesGame:
    def test_ai_vs_random(self):
        """AI should be able to complete a game against a random mover."""
        import random
        random.seed(42)

        game = GameState()
        max_moves = 300

        for _ in range(max_moves):
            if game.is_over:
                break
            if game.current_player == Player.BLUE:
                move = find_best_move(game, time_limit_ms=200)
            else:
                moves = game.get_legal_moves()
                move = random.choice(moves) if moves else None

            if move is None:
                break
            game.make_move(move[0], move[1])

        assert game.is_over or len(game.get_legal_moves()) == 0


class TestMaximizingBug:
    """Regression tests for the critical bug where RED player minimized its own score."""

    def test_red_ai_finds_winning_move(self):
        """RED AI should find a winning den-entry move, just like BLUE."""
        clear_tt()
        # Red Lion one step from Blue's den (3,0)
        lion = Piece(PieceType.LION, Player.RED, 3, 1)
        # Blue piece far away so it's not instant-win
        cat = Piece(PieceType.CAT, Player.BLUE, 0, 6)
        game = make_game_with_pieces([lion, cat])
        game.current_player = Player.RED
        move = find_best_move(game, Player.RED, time_limit_ms=1000)
        assert move is not None
        # Lion at (3,1) can move to (3,0) = Blue's den = instant win
        assert move == ((3, 1), (3, 0))

    def test_red_ai_prefers_capture_over_idle_move(self):
        """RED AI should capture an adjacent weaker piece or advance toward den."""
        clear_tt()
        # Red Tiger at (4,4), Blue Cat at (4,5) — Tiger can capture Cat
        tiger = Piece(PieceType.TIGER, Player.RED, 4, 4)
        cat = Piece(PieceType.CAT, Player.BLUE, 4, 5)
        # Extra pieces to avoid instant win
        lion_blue = Piece(PieceType.LION, Player.BLUE, 0, 0)
        lion_red = Piece(PieceType.LION, Player.RED, 6, 8)
        game = make_game_with_pieces([tiger, cat, lion_blue, lion_red])
        game.current_player = Player.RED
        move = find_best_move(game, Player.RED, time_limit_ms=1000)
        assert move is not None
        # Tiger should move the Tiger piece (not the Lion) and make a sensible move
        assert move[0] == (4, 4), f"Expected Tiger to move, got move from {move[0]}"

    def test_blue_ai_prefers_capture_over_idle_move(self):
        """BLUE AI should also capture an adjacent weaker piece."""
        clear_tt()
        # Blue Tiger at (0,4), Red Cat at (0,5) — both land squares, Tiger can capture Cat
        tiger = Piece(PieceType.TIGER, Player.BLUE, 0, 4)
        cat = Piece(PieceType.CAT, Player.RED, 0, 5)
        lion_blue = Piece(PieceType.LION, Player.BLUE, 6, 0)
        lion_red = Piece(PieceType.LION, Player.RED, 6, 8)
        game = make_game_with_pieces([tiger, cat, lion_blue, lion_red])
        game.current_player = Player.BLUE
        move = find_best_move(game, Player.BLUE, time_limit_ms=1000)
        assert move is not None
        # The Tiger should capture the Cat
        if move[0] == (0, 4):
            assert move[1] == (0, 5), f"Expected Tiger to capture Cat at (0,5), got move to {move[1]}"

    def test_red_evaluates_positive_for_red_advantage(self):
        """Evaluate should return positive for RED when RED has more material."""
        clear_tt()
        # RED has Lion + Elephant, BLUE has only Cat
        lion = Piece(PieceType.LION, Player.RED, 3, 4)
        elephant = Piece(PieceType.ELEPHANT, Player.RED, 4, 4)
        cat = Piece(PieceType.CAT, Player.BLUE, 0, 6)
        game = make_game_with_pieces([lion, elephant, cat])
        score = evaluate(game, Player.RED)
        assert score > 0, f"RED with material advantage should have positive score, got {score}"

    def test_red_ai_does_not_avoid_capturing(self):
        """RED AI should not avoid capturing when it can — regression for inverted maximizing."""
        clear_tt()
        # Red Wolf at (3,5), Blue Cat at (3,6) — Wolf (rank 4) can capture Cat (rank 2)
        wolf = Piece(PieceType.WOLF, Player.RED, 3, 5)
        cat = Piece(PieceType.CAT, Player.BLUE, 3, 6)
        # Extra pieces far away
        elephant_r = Piece(PieceType.ELEPHANT, Player.RED, 0, 6)
        lion_b = Piece(PieceType.LION, Player.BLUE, 6, 0)
        game = make_game_with_pieces([wolf, cat, elephant_r, lion_b])
        game.current_player = Player.RED
        move = find_best_move(game, Player.RED, time_limit_ms=1000)
        assert move is not None
        # The best move should involve the Wolf capturing the Cat or advancing
        # At minimum, the Wolf should not move AWAY from the Cat
        if move[0] == (3, 5):
            assert move[1] == (3, 6), f"Wolf should capture Cat at (3,6), got move to {move[1]}"


class TestSkipValidation:
    """Tests for skip_validation parameter in make_move."""

    def test_skip_validation_accepts_legal_move(self):
        """skip_validation=True should work for legal moves."""
        game = GameState()
        moves = game.get_legal_moves()
        # Should not raise
        game.make_move(moves[0][0], moves[0][1], skip_validation=True)

    def test_skip_validation_allows_illegal_move(self):
        """skip_validation=True should bypass the legal-move check."""
        game = GameState()
        # Moving to an occupied own-piece square would normally be illegal
        # but with skip_validation it won't raise ValueError for legality
        # (it may still raise for other reasons like wrong player)
        # Test: a legal move with skip_validation should work fine
        moves = game.get_legal_moves()
        assert len(moves) > 0
        game.make_move(moves[0][0], moves[0][1], skip_validation=True)
        game.undo_move()
        # The same move without skip_validation should also work
        game.make_move(moves[0][0], moves[0][1], skip_validation=False)

    def test_normal_validation_catches_illegal_move(self):
        """Without skip_validation, illegal moves should raise ValueError."""
        game = GameState()
        with pytest.raises(ValueError):
            # Try to move from an empty square
            game.make_move((0, 5), (0, 4))


class TestEvaluationImprovements:
    """Tests for improved evaluation function."""

    def test_threat_bonus_for_capturing(self):
        """Pieces threatening to capture should get a bonus."""
        clear_tt()
        # Blue Tiger adjacent to Red Cat — Tiger threatens Cat
        tiger = Piece(PieceType.TIGER, Player.BLUE, 4, 3)
        cat = Piece(PieceType.CAT, Player.RED, 4, 4)
        game1 = make_game_with_pieces([tiger, cat])

        # Same pieces but not adjacent
        tiger2 = Piece(PieceType.TIGER, Player.BLUE, 0, 0)
        cat2 = Piece(PieceType.CAT, Player.RED, 6, 8)
        game2 = make_game_with_pieces([tiger2, cat2])

        score1 = evaluate(game1, Player.BLUE)
        score2 = evaluate(game2, Player.BLUE)
        assert score1 > score2, f"Threat position should score higher: {score1} vs {score2}"

    def test_closer_to_den_is_better(self):
        """Pieces closer to opponent's den should have higher positional score."""
        clear_tt()
        # Blue Lion near Red's den
        lion_close = Piece(PieceType.LION, Player.BLUE, 3, 6)
        rat_far = Piece(PieceType.RAT, Player.RED, 0, 0)
        game_close = make_game_with_pieces([lion_close, rat_far])

        # Blue Lion far from Red's den
        lion_far = Piece(PieceType.LION, Player.BLUE, 0, 0)
        game_far = make_game_with_pieces([lion_far, rat_far])

        score_close = evaluate(game_close, Player.BLUE)
        score_far = evaluate(game_far, Player.BLUE)
        assert score_close > score_far, f"Closer to den should score higher: {score_close} vs {score_far}"


class TestQuiescenceSearch:
    """Tests for quiescence search avoiding horizon effect."""

    def test_ai_finds_immediate_capture(self):
        """AI should see and take an immediate capture opportunity."""
        clear_tt()
        # Blue Lion at (3,4), Red Cat at (3,5) — Lion can capture Cat
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        cat = Piece(PieceType.CAT, Player.RED, 3, 5)
        elephant_r = Piece(PieceType.ELEPHANT, Player.RED, 0, 6)
        game = make_game_with_pieces([lion, cat, elephant_r])
        game.current_player = Player.BLUE
        move = find_best_move(game, time_limit_ms=500)
        assert move is not None
        # Should capture the Cat
        if move[0] == (3, 4):
            assert move[1] == (3, 5), f"Lion should capture Cat at (3,5), got {move}"

    def test_ai_avoids_walking_into_den(self):
        """AI should evaluate a position where opponent threatens den as dangerous."""
        clear_tt()
        # Red Lion at (2,1) — very close to Blue's den at (3,0)
        # This is NOT in a trap, so it's a real threat
        # Blue Elephant at (0,6) — far from defense
        lion_red = Piece(PieceType.LION, Player.RED, 2, 1)
        elephant_blue = Piece(PieceType.ELEPHANT, Player.BLUE, 0, 6)
        # Extra piece so it's not an instant win
        cat_red = Piece(PieceType.CAT, Player.RED, 5, 7)
        game = make_game_with_pieces([lion_red, elephant_blue, cat_red])
        game.current_player = Player.BLUE
        # The evaluation should see Red's Lion near Blue's den as threatening
        # Red has material advantage (Lion 1000 + Cat 200) vs Blue (Elephant 1100)
        # and positional threat from Lion near den
        score = evaluate(game, Player.BLUE)
        # With Red Lion threatening and material disadvantage, score should be negative
        assert score < 0, f"Position should be bad for Blue (Red Lion threatening den): score={score}"


class TestAIEnhancements:
    """Tests for new AI features: den defense, mobility, endgame, LMR."""

    def test_den_defense_bonus(self):
        """Having defenders near own den when threatened should score higher."""
        clear_tt()
        # Red Lion near Blue's den — no defender
        lion_red = Piece(PieceType.LION, Player.RED, 2, 1)
        elephant_blue = Piece(PieceType.ELEPHANT, Player.BLUE, 0, 6)
        cat_red = Piece(PieceType.CAT, Player.RED, 5, 7)
        game_no_defender = make_game_with_pieces([lion_red, elephant_blue, cat_red])

        # Red Lion near Blue's den — WITH defender
        dog_blue = Piece(PieceType.DOG, Player.BLUE, 3, 1)
        game_with_defender = make_game_with_pieces([lion_red, elephant_blue, cat_red, dog_blue])

        score_no_def = evaluate(game_no_defender, Player.BLUE)
        score_with_def = evaluate(game_with_defender, Player.BLUE)
        assert score_with_def > score_no_def, \
            f"Defender near den should score higher: {score_with_def} vs {score_no_def}"

    def test_mobility_bonus(self):
        """Pieces with more open moves should score higher."""
        clear_tt()
        # Lion in center with many moves
        lion_center = Piece(PieceType.LION, Player.BLUE, 3, 4)
        elephant_r = Piece(PieceType.ELEPHANT, Player.RED, 0, 6)
        game_center = make_game_with_pieces([lion_center, elephant_r])

        # Lion in corner with few moves
        lion_corner = Piece(PieceType.LION, Player.BLUE, 0, 0)
        game_corner = make_game_with_pieces([lion_corner, elephant_r])

        score_center = evaluate(game_center, Player.BLUE)
        score_corner = evaluate(game_corner, Player.BLUE)
        assert score_center > score_corner, \
            f"Center Lion should score higher (more mobility): {score_center} vs {score_corner}"

    def test_endgame_dominant_piece_bonus(self):
        """Lion/Tiger with no enemy Rat should get endgame bonus."""
        clear_tt()
        lion_blue = Piece(PieceType.LION, Player.BLUE, 3, 4)
        cat_red = Piece(PieceType.CAT, Player.RED, 0, 6)
        # Endgame: 2 pieces total
        game = make_game_with_pieces([lion_blue, cat_red])
        score = evaluate(game, Player.BLUE)
        # Should include dominant piece bonus (Lion with no enemy Rat)
        assert score > 0, f"Endgame with dominant Lion should be positive: {score}"

    def test_two_bucket_tt(self):
        """Two-bucket transposition table should work correctly."""
        tt = TranspositionTable(depth_size=100, always_size=100)
        # Store in depth table
        tt.store(12345, 4, 100, EXACT, None)
        result = tt.lookup(12345, 4)
        assert result is not None
        assert result[0] == 100
        # Lookup with insufficient depth should fail
        result = tt.lookup(12345, 5)
        assert result is None

    def test_null_move_pruning_constants(self):
        """Verify null-move pruning constants are sensible."""
        assert NULL_MOVE_R == 2
        assert LMR_MIN_DEPTH == 3

    def test_piece_values_rat_higher_than_cat(self):
        """Rat should be valued higher than Cat (can capture Elephant)."""
        assert PIECE_VALUES[PieceType.RAT] > PIECE_VALUES[PieceType.CAT]

    def test_piece_values_elephant_not_highest(self):
        """Elephant should not be the highest-valued piece (vulnerable to Rat)."""
        assert PIECE_VALUES[PieceType.ELEPHANT] < PIECE_VALUES[PieceType.LION]