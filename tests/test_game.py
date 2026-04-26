"""Tests for GameState management."""

import pytest
from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Piece, PieceType, Player
from conftest import make_game_with_pieces


class TestGameStateInit:
    def test_initial_state(self):
        game = GameState()
        assert game.current_player == Player.BLUE
        assert game.winner is None
        assert game.is_over is False

    def test_initial_piece_count(self):
        game = GameState()
        blue = game.get_player_pieces(Player.BLUE)
        red = game.get_player_pieces(Player.RED)
        assert len(blue) == 8
        assert len(red) == 8

    def test_piece_at_starting_positions(self):
        game = GameState()
        # Blue Lion at (0,0)
        piece = game.piece_at(0, 0)
        assert piece is not None
        assert piece.piece_type == PieceType.LION
        assert piece.player == Player.BLUE

        # Red Elephant at (0,6)
        piece = game.piece_at(0, 6)
        assert piece is not None
        assert piece.piece_type == PieceType.ELEPHANT
        assert piece.player == Player.RED

    def test_no_piece_at_empty_square(self):
        game = GameState()
        assert game.piece_at(3, 4) is None  # Land between rivers

    def test_custom_first_player(self):
        game = GameState(first_player=Player.RED)
        assert game.current_player == Player.RED

    def test_first_player_alternation(self):
        """When Red moves first, after Red's move it should be Blue's turn."""
        game = GameState(first_player=Player.RED)
        assert game.current_player == Player.RED
        moves = game.get_legal_moves()
        game.make_move(moves[0][0], moves[0][1])
        assert game.current_player == Player.BLUE


class TestMakeMove:
    def test_valid_move(self):
        game = GameState()
        # Blue's first move - pick any legal move
        moves = game.get_legal_moves()
        assert len(moves) > 0
        from_pos, to_pos = moves[0]
        captured = game.make_move(from_pos, to_pos)
        # Should switch to Red
        assert game.current_player == Player.RED
        assert game.winner is None

    def test_move_switches_player(self):
        game = GameState()
        moves = game.get_legal_moves()
        game.make_move(moves[0][0], moves[0][1])
        assert game.current_player == Player.RED

    def test_capture_removes_piece(self):
        # Set up a capture scenario
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        cat = Piece(PieceType.CAT, Player.RED, 3, 5)
        game = GameState.__new__(GameState)
        game.board = GameState().board
        game.pieces = [lion, cat]
        game.current_player = Player.BLUE
        game._move_history = []
        game._winner = None
        game._rebuild_index()

        captured = game.make_move((3, 4), (3, 5))
        assert captured is not None
        assert captured.piece_type == PieceType.CAT
        assert len(game.get_player_pieces(Player.RED)) == 0

    def test_move_piece_updates_position(self):
        game = GameState()
        # Find a piece that can move
        moves = game.get_legal_moves()
        from_pos, to_pos = moves[0]
        piece = game.piece_at(*from_pos)
        assert piece is not None

        game.make_move(from_pos, to_pos)
        assert piece.col == to_pos[0]
        assert piece.row == to_pos[1]

    def test_illegal_move_raises(self):
        game = GameState()
        with pytest.raises(ValueError):
            game.make_move((3, 4), (3, 5))  # No piece there

    def test_wrong_turn_raises(self):
        game = GameState()
        # Try to move a Red piece on Blue's turn
        with pytest.raises(ValueError):
            game.make_move((0, 8), (0, 7))

    def test_move_after_game_over_raises(self):
        # Create a game that ends immediately
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        game = GameState.__new__(GameState)
        game.board = GameState().board
        game.pieces = [lion]
        game.current_player = Player.BLUE
        game._move_history = []
        game._winner = None
        game._rebuild_index()

        game.make_move((3, 7), (3, 8))  # Enter den, win
        assert game.is_over
        with pytest.raises(ValueError):
            game.make_move((3, 8), (3, 7))


class TestUndoMove:
    def test_undo_simple_move(self):
        game = GameState()
        initial_player = game.current_player
        moves = game.get_legal_moves()
        from_pos, to_pos = moves[0]
        piece = game.piece_at(*from_pos)

        game.make_move(from_pos, to_pos)
        assert game.current_player != initial_player

        game.undo_move()
        assert game.current_player == initial_player
        assert piece.pos == from_pos

    def test_undo_capture(self):
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        cat = Piece(PieceType.CAT, Player.RED, 3, 5)
        game = GameState.__new__(GameState)
        game.board = GameState().board
        game.pieces = [lion, cat]
        game.current_player = Player.BLUE
        game._move_history = []
        game._winner = None
        game._rebuild_index()

        game.make_move((3, 4), (3, 5))
        assert len(game.get_player_pieces(Player.RED)) == 0

        game.undo_move()
        assert len(game.get_player_pieces(Player.RED)) == 1
        assert game.piece_at(3, 5) is not None
        assert game.piece_at(3, 5).piece_type == PieceType.CAT

    def test_undo_no_moves(self):
        game = GameState()
        assert game.undo_move() is False

    def test_multiple_undo(self):
        game = GameState()
        moves = game.get_legal_moves()
        initial_player = game.current_player

        # Make 3 consecutive moves
        game.make_move(moves[0][0], moves[0][1])
        moves2 = game.get_legal_moves()
        game.make_move(moves2[0][0], moves2[0][1])
        moves3 = game.get_legal_moves()
        game.make_move(moves3[0][0], moves3[0][1])

        # Undo all 3
        assert game.undo_move() is True
        assert game.undo_move() is True
        assert game.undo_move() is True
        assert game.current_player == initial_player


class TestGameCopy:
    def test_copy_preserves_state(self):
        game = GameState()
        copy = game.copy()
        assert copy.current_player == game.current_player
        assert len(copy.pieces) == len(game.pieces)

    def test_copy_independence(self):
        game = GameState()
        copy = game.copy()
        moves = copy.get_legal_moves()
        copy.make_move(moves[0][0], moves[0][1])
        # Original should not be affected
        assert game.current_player == Player.BLUE


class TestFullGame:
    def test_two_random_players_finish(self):
        """Two random movers should complete a game (or reach a position)."""
        import random
        random.seed(42)

        game = GameState()
        max_moves = 500
        moves_played = 0

        while not game.is_over and moves_played < max_moves:
            moves = game.get_legal_moves()
            if not moves:
                break
            move = random.choice(moves)
            game.make_move(move[0], move[1])
            moves_played += 1

        # Game should either be over or have been moving
        assert moves_played > 0

    def test_random_game_eventually_ends(self):
        """Random games should eventually end (den entry or elimination)."""
        import random
        for seed in range(5):
            random.seed(seed)
            game = GameState()
            max_moves = 1000
            moves_played = 0

            while not game.is_over and moves_played < max_moves:
                moves = game.get_legal_moves()
                if not moves:
                    break
                move = random.choice(moves)
                game.make_move(move[0], move[1])
                moves_played += 1

            assert game.is_over, f"Game with seed {seed} did not end after {moves_played} moves"

    def test_deny_entry_to_own_den(self):
        """A piece cannot move into its own den."""
        game = GameState()
        # Blue piece near Blue's den at (3,0)
        # Place a piece at (3,1) which is a Blue trap, adjacent to Blue's den
        # The den (3,0) should not be in legal moves
        lion = Piece(PieceType.LION, Player.BLUE, 3, 1)
        game2 = GameState.__new__(GameState)
        game2.board = GameState().board
        game2.pieces = [lion]
        game2.current_player = Player.BLUE
        game2._move_history = []
        game2._winner = None
        game2._rebuild_index()

        moves = game2.get_legal_moves()
        # (3,1) -> (3,0) is Blue's own den, should NOT be legal
        assert ((3, 1), (3, 0)) not in moves

    def test_den_entry_wins_game(self):
        """Moving into opponent's den immediately wins."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        game = GameState.__new__(GameState)
        game.board = GameState().board
        game.pieces = [lion]
        game.current_player = Player.BLUE
        game._move_history = []
        game._winner = None
        game._rebuild_index()

        game.make_move((3, 7), (3, 8))
        assert game.is_over
        assert game.winner == Player.BLUE

    def test_undo_winning_move_clears_winner(self):
        """Undoing a winning move should clear the winner."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        game = make_game_with_pieces([lion])
        game.make_move((3, 7), (3, 8))
        assert game.is_over
        assert game.winner == Player.BLUE
        game.undo_move()
        assert not game.is_over
        assert game.winner is None

    def test_win_reason_den_entry(self):
        """Win by den entry should have correct reason."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        game = make_game_with_pieces([lion])
        game.make_move((3, 7), (3, 8))
        assert game.win_reason == "den_entry"

    def test_win_reason_elimination(self):
        """Win by elimination should have correct reason."""
        lion = Piece(PieceType.LION, Player.BLUE, 0, 7)
        cat = Piece(PieceType.CAT, Player.RED, 0, 8)
        game = make_game_with_pieces([lion, cat])
        game.make_move((0, 7), (0, 8))
        assert game.winner == Player.BLUE
        assert game.win_reason == "elimination"

    def test_copy_preserves_win_reason(self):
        """Copy should preserve win reason."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)
        game = make_game_with_pieces([lion])
        game.make_move((3, 7), (3, 8))
        copy = game.copy()
        assert copy.win_reason == "den_entry"
        assert copy.winner == Player.BLUE