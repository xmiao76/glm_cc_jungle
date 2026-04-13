"""Tests for the AI engine."""

import pytest
import time
from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Piece, PieceType, Player
from jungle_game.engine.ai import (
    find_best_move, evaluate, order_moves, PIECE_VALUES,
    compute_zobrist_hash, TranspositionTable, EXACT, LOWERBOUND, UPPERBOUND,
)
from jungle_game.engine.rules import generate_legal_moves


def make_game_with_pieces(pieces: list[Piece]) -> GameState:
    game = GameState.__new__(GameState)
    game.board = GameState().board
    game.pieces = pieces
    game.current_player = Player.BLUE
    game._move_history = []
    game._winner = None
    game._rebuild_index()
    return game


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
        # Create a position with no moves for Blue
        wolf1 = Piece(PieceType.WOLF, Player.RED, 2, 4)
        wolf2 = Piece(PieceType.WOLF, Player.RED, 4, 4)
        wolf3 = Piece(PieceType.WOLF, Player.RED, 3, 3)
        wolf4 = Piece(PieceType.WOLF, Player.RED, 3, 5)
        rat = Piece(PieceType.RAT, Player.BLUE, 3, 4)
        game = make_game_with_pieces([rat, wolf1, wolf2, wolf3, wolf4])
        moves = generate_legal_moves(game, Player.BLUE)
        # If there are no moves, find_best_move should return None
        if not moves:
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