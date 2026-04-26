"""Tests for legal move generation and capture rules."""

import pytest
from jungle_game.engine.game import GameState
from jungle_game.engine.board import Board, WATER_SQUARES, BLUE_DEN, RED_DEN, BLUE_TRAPS, RED_TRAPS
from jungle_game.engine.pieces import Piece, PieceType, Player
from jungle_game.engine.rules import generate_legal_moves, is_capture_valid, check_win, check_win_with_reason
from conftest import make_game_with_pieces


class TestBasicMovement:
    def test_initial_legal_moves_count(self):
        game = GameState()
        moves = game.get_legal_moves()
        # Blue starts with 8 pieces; some can move, some blocked by own pieces
        assert len(moves) > 0

    def test_all_moves_are_orthogonal(self):
        game = GameState()
        moves = game.get_legal_moves()
        for (fc, fr), (tc, tr) in moves:
            # Either same column and row differs by 1, or vice versa
            assert (fc == tc and abs(fr - tr) == 1) or (fr == tr and abs(fc - tc) == 1) or \
                _is_river_jump(game, fc, fr, tc, tr)

    def test_cannot_move_out_of_bounds(self):
        """All legal moves must land in bounds."""
        game = GameState()
        moves = game.get_legal_moves()
        for _, (tc, tr) in moves:
            assert 0 <= tc <= 6
            assert 0 <= tr <= 8

    def test_cannot_capture_own_pieces(self):
        """No move should land on a square with own piece."""
        game = GameState()
        moves = game.get_legal_moves()
        for _, (tc, tr) in moves:
            target = game.piece_at(tc, tr)
            if target is not None:
                assert target.player != Player.BLUE  # Blue moves first

    def test_cannot_enter_own_den(self):
        """Pieces cannot enter their own den."""
        game = GameState()
        moves = game.get_legal_moves()
        for _, (tc, tr) in moves:
            if game.current_player == Player.BLUE:
                assert (tc, tr) != BLUE_DEN

    def test_must_move_on_turn(self):
        """If a player has pieces, they should have at least some moves."""
        game = GameState()
        assert len(game.get_legal_moves()) > 0


def _is_river_jump(game, fc, fr, tc, tr):
    """Helper to check if a move is a river jump (not a 1-step orthogonal move)."""
    return abs(fc - tc) > 1 or abs(fr - tr) > 1


class TestWaterRules:
    def test_only_rat_enters_water(self):
        """Only the rat can move into water squares."""
        game = GameState()
        moves = generate_legal_moves(game, Player.BLUE)
        for (fc, fr), (tc, tr) in moves:
            if game.board.is_water(tc, tr):
                piece = game.piece_at(fc, fr)
                assert piece is not None
                assert piece.piece_type == PieceType.RAT

    def test_rat_can_move_from_land_to_water(self):
        """Blue rat at (0,2) can move down to (1,2) which is land, or further..."""
        game = GameState()
        # Blue rat starts at (0,2). (0,3) is land. (1,2) is land.
        # To enter water, rat needs to be adjacent to water
        # Place a single rat adjacent to water
        pieces = [Piece(PieceType.RAT, Player.BLUE, 0, 3)]  # Adjacent to water at (1,3)
        game = make_game_with_pieces(pieces)
        moves = generate_legal_moves(game, Player.BLUE)
        # Check rat can move into water at (1,3)
        to_water = [((fc, fr), (tc, tr)) for (fc, fr), (tc, tr) in moves
                    if game.board.is_water(tc, tr)]
        # (0,3) is land, adjacent to (1,3) water - should be a legal move
        assert any(m[1] == (1, 3) for m in to_water)

    def test_non_rat_cannot_enter_water(self):
        """Dog, Cat, Wolf, etc. cannot enter water."""
        pieces = [Piece(PieceType.DOG, Player.BLUE, 0, 3)]
        game = make_game_with_pieces(pieces)
        moves = generate_legal_moves(game, Player.BLUE)
        water_moves = [m for m in moves if game.board.is_water(m[1][0], m[1][1])]
        assert len(water_moves) == 0

    def test_rat_in_water_can_move_in_water(self):
        """Rat already in water can move to adjacent water squares."""
        pieces = [Piece(PieceType.RAT, Player.BLUE, 1, 3)]  # In water
        game = make_game_with_pieces(pieces)
        moves = generate_legal_moves(game, Player.BLUE)
        # Should be able to move to other water squares
        assert len(moves) > 0

    def test_rat_can_exit_water_to_land(self):
        """Rat in water can move to adjacent land."""
        pieces = [Piece(PieceType.RAT, Player.BLUE, 1, 3)]  # In water
        game = make_game_with_pieces(pieces)
        moves = generate_legal_moves(game, Player.BLUE)
        land_moves = [m for m in moves if not game.board.is_water(m[1][0], m[1][1])]
        assert len(land_moves) > 0


class TestRatElephantSpecialRules:
    def test_rat_on_land_captures_elephant(self):
        """Rat on land can capture Elephant."""
        rat = Piece(PieceType.RAT, Player.BLUE, 2, 6)
        elephant = Piece(PieceType.ELEPHANT, Player.RED, 2, 7)
        game = make_game_with_pieces([rat, elephant])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((2, 6), (2, 7)) in moves

    def test_elephant_cannot_capture_rat(self):
        """Elephant can never capture Rat."""
        rat = Piece(PieceType.RAT, Player.RED, 2, 7)
        elephant = Piece(PieceType.ELEPHANT, Player.BLUE, 2, 6)
        game = make_game_with_pieces([rat, elephant])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((2, 6), (2, 7)) not in moves

    def test_rat_in_water_cannot_capture_elephant_on_land(self):
        """Rat in water cannot capture Elephant on adjacent land."""
        rat = Piece(PieceType.RAT, Player.BLUE, 1, 3)  # In water
        elephant = Piece(PieceType.ELEPHANT, Player.RED, 0, 3)  # Land, adjacent
        game = make_game_with_pieces([rat, elephant])
        moves = generate_legal_moves(game, Player.BLUE)
        # Rat in water should NOT be able to capture elephant on land
        assert ((1, 3), (0, 3)) not in moves

    def test_rat_in_water_captures_rat_in_water(self):
        """Rat in water can capture another Rat also in water."""
        rat1 = Piece(PieceType.RAT, Player.BLUE, 1, 3)  # In water
        rat2 = Piece(PieceType.RAT, Player.RED, 1, 4)  # In water, adjacent
        game = make_game_with_pieces([rat1, rat2])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((1, 3), (1, 4)) in moves

    def test_rat_on_land_cannot_capture_rat_in_water(self):
        """Rat on land cannot capture Rat in water."""
        rat1 = Piece(PieceType.RAT, Player.BLUE, 0, 3)  # Land, adjacent to water
        rat2 = Piece(PieceType.RAT, Player.RED, 1, 3)  # In water
        game = make_game_with_pieces([rat1, rat2])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((0, 3), (1, 3)) not in moves

    def test_land_piece_cannot_capture_rat_in_water(self):
        """A piece on land cannot capture a Rat in water."""
        cat = Piece(PieceType.CAT, Player.BLUE, 0, 3)  # Land
        rat = Piece(PieceType.RAT, Player.RED, 1, 3)  # Water
        game = make_game_with_pieces([cat, rat])
        moves = generate_legal_moves(game, Player.BLUE)
        # Cat can't enter water anyway, but let's verify
        assert ((0, 3), (1, 3)) not in moves


class TestRiverJumps:
    def test_lion_vertical_jump(self):
        """Lion can jump vertically across the river."""
        # Place lion above the left river area
        lion = Piece(PieceType.LION, Player.BLUE, 1, 2)  # Above water at (1,3)
        game = make_game_with_pieces([lion])
        moves = generate_legal_moves(game, Player.BLUE)
        # Should be able to jump to (1, 6) - landing below the water
        assert ((1, 2), (1, 6)) in moves

    def test_tiger_vertical_jump(self):
        """Tiger can jump vertically across the river."""
        tiger = Piece(PieceType.TIGER, Player.BLUE, 1, 2)
        game = make_game_with_pieces([tiger])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((1, 2), (1, 6)) in moves

    def test_lion_horizontal_jump(self):
        """Lion can jump horizontally across the river."""
        # Place lion to the left of right river area
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)  # Land between rivers
        game = make_game_with_pieces([lion])
        moves = generate_legal_moves(game, Player.BLUE)
        # Should be able to jump from (3,4) right over water to (6,4)
        assert ((3, 4), (6, 4)) in moves

    def test_tiger_cannot_jump_horizontally(self):
        """Tiger cannot jump horizontally across the river."""
        tiger = Piece(PieceType.TIGER, Player.BLUE, 3, 4)
        game = make_game_with_pieces([tiger])
        moves = generate_legal_moves(game, Player.BLUE)
        # Tiger should NOT be able to jump horizontally
        assert ((3, 4), (6, 4)) not in moves

    def test_jump_blocked_by_rat_in_water(self):
        """River jump is blocked if any Rat is in the intervening water."""
        lion = Piece(PieceType.LION, Player.BLUE, 1, 2)
        # Place a rat in the water path
        rat_in_water = Piece(PieceType.RAT, Player.RED, 1, 4)  # In water
        game = make_game_with_pieces([lion, rat_in_water])
        moves = generate_legal_moves(game, Player.BLUE)
        # Lion should NOT be able to jump because rat blocks
        assert ((1, 2), (1, 6)) not in moves

    def test_jump_blocked_by_own_rat_in_water(self):
        """River jump is blocked even by own Rat in the water."""
        lion = Piece(PieceType.LION, Player.BLUE, 1, 2)
        own_rat = Piece(PieceType.RAT, Player.BLUE, 1, 4)  # Own rat in water
        game = make_game_with_pieces([lion, own_rat])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((1, 2), (1, 6)) not in moves

    def test_jump_captures_at_landing(self):
        """Lion can capture at the landing square of a river jump."""
        lion = Piece(PieceType.LION, Player.BLUE, 1, 2)
        # Weak enemy piece at landing
        cat = Piece(PieceType.CAT, Player.RED, 1, 6)
        game = make_game_with_pieces([lion, cat])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((1, 2), (1, 6)) in moves


class TestTrapRules:
    def test_piece_in_opponent_trap_rank_zero(self):
        """Piece in opponent's trap has effective rank 0."""
        from jungle_game.engine.rules import _effective_rank
        dog = Piece(PieceType.DOG, Player.BLUE, 2, 8)  # In Red's trap
        board = Board()
        assert _effective_rank(dog, board) == 0

    def test_piece_not_in_trap_has_normal_rank(self):
        from jungle_game.engine.rules import _effective_rank
        dog = Piece(PieceType.DOG, Player.BLUE, 2, 4)  # Normal land
        board = Board()
        assert _effective_rank(dog, board) == 3

    def test_any_piece_captures_trapped_piece(self):
        """Any piece can capture an enemy piece in your trap."""
        # Blue rat next to Red cat in Blue's trap
        rat = Piece(PieceType.RAT, Player.BLUE, 2, 1)  # Adjacent to Blue trap (3,1)
        trapped_cat = Piece(PieceType.CAT, Player.RED, 3, 1)  # In Blue's trap
        game = make_game_with_pieces([rat, trapped_cat])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((2, 1), (3, 1)) in moves

    def test_own_trap_has_no_effect(self):
        """Own trap doesn't reduce your piece's rank."""
        from jungle_game.engine.rules import _effective_rank
        dog = Piece(PieceType.DOG, Player.BLUE, 2, 0)  # In Blue's own trap
        board = Board()
        assert _effective_rank(dog, board) == 3  # Full rank


class TestCaptureRules:
    def test_higher_rank_captures_lower(self):
        """Higher rank piece captures lower rank."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        cat = Piece(PieceType.CAT, Player.RED, 3, 5)
        game = make_game_with_pieces([lion, cat])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((3, 4), (3, 5)) in moves

    def test_same_rank_captures(self):
        """Same rank piece captures."""
        lion1 = Piece(PieceType.LION, Player.BLUE, 3, 4)
        lion2 = Piece(PieceType.LION, Player.RED, 3, 5)
        game = make_game_with_pieces([lion1, lion2])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((3, 4), (3, 5)) in moves

    def test_lower_rank_cannot_capture_higher(self):
        """Lower rank cannot capture higher rank (except Rat vs Elephant)."""
        cat = Piece(PieceType.CAT, Player.BLUE, 3, 4)
        lion = Piece(PieceType.LION, Player.RED, 3, 5)
        game = make_game_with_pieces([cat, lion])
        moves = generate_legal_moves(game, Player.BLUE)
        assert ((3, 4), (3, 5)) not in moves


class TestWinConditions:
    def test_enter_opponent_den_wins(self):
        """Moving a piece into the opponent's den wins."""
        # Place a piece adjacent to opponent's den
        lion = Piece(PieceType.LION, Player.BLUE, 3, 7)  # Adjacent to Red's den at (3,8)
        game = make_game_with_pieces([lion])
        game.make_move((3, 7), (3, 8))
        assert game.winner == Player.BLUE

    def test_capture_all_pieces_wins(self):
        """Capturing all opponent's pieces wins."""
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        rat = Piece(PieceType.RAT, Player.RED, 3, 5)
        game = make_game_with_pieces([lion, rat])
        game.make_move((3, 4), (3, 5))
        assert game.winner == Player.BLUE

    def test_no_winner_at_start(self):
        game = GameState()
        assert game.winner is None

    def test_stalemate_loss(self):
        """Player with no legal moves loses."""
        # Create a position where Blue has no legal moves
        # Blue rat surrounded with no moves
        elephant = Piece(PieceType.ELEPHANT, Player.RED, 0, 2)
        wolf = Piece(PieceType.WOLF, Player.RED, 1, 3)
        rat = Piece(PieceType.RAT, Player.BLUE, 0, 3)  # In water, but...
        # Actually let's create a cleaner scenario:
        # Single blue piece that's blocked
        rat = Piece(PieceType.RAT, Player.BLUE, 3, 4)
        # Surround it with red pieces it can't capture
        eleph1 = Piece(PieceType.ELEPHANT, Player.RED, 2, 4)
        eleph2 = Piece(PieceType.ELEPHANT, Player.RED, 4, 4)
        eleph3 = Piece(PieceType.ELEPHANT, Player.RED, 3, 3)
        eleph4 = Piece(PieceType.ELEPHANT, Player.RED, 3, 5)
        game = make_game_with_pieces([rat, eleph1, eleph2, eleph3, eleph4])
        # Blue rat at (3,4) surrounded by elephants - can't capture them
        # Actually, rat CAN capture elephant... Let me use different pieces
        # Surround with wolves (rank 4) - rat (rank 1) can't capture wolf
        wolf1 = Piece(PieceType.WOLF, Player.RED, 2, 4)
        wolf2 = Piece(PieceType.WOLF, Player.RED, 4, 4)
        wolf3 = Piece(PieceType.WOLF, Player.RED, 3, 3)
        wolf4 = Piece(PieceType.WOLF, Player.RED, 3, 5)
        game = make_game_with_pieces([rat, wolf1, wolf2, wolf3, wolf4])
        winner = check_win(game)
        assert winner == Player.RED  # Blue has no legal moves


class TestWinReason:
    """Tests for check_win_with_reason function."""

    def test_win_reason_no_winner_yet(self):
        lion = Piece(PieceType.LION, Player.BLUE, 0, 0)
        cat = Piece(PieceType.CAT, Player.RED, 6, 8)
        game = make_game_with_pieces([lion, cat])
        winner, reason = check_win_with_reason(game)
        assert winner is None
        assert reason == ""

    def test_win_reason_den_entry(self):
        lion = Piece(PieceType.LION, Player.BLUE, 3, 8)
        cat = Piece(PieceType.CAT, Player.RED, 6, 8)
        game = make_game_with_pieces([lion, cat])
        # Lion is ON Red's den at (3,8)
        winner, reason = check_win_with_reason(game)
        assert winner == Player.BLUE
        assert reason == "den_entry"

    def test_win_reason_stalemate(self):
        rat = Piece(PieceType.RAT, Player.BLUE, 3, 4)
        wolf1 = Piece(PieceType.WOLF, Player.RED, 2, 4)
        wolf2 = Piece(PieceType.WOLF, Player.RED, 4, 4)
        wolf3 = Piece(PieceType.WOLF, Player.RED, 3, 3)
        wolf4 = Piece(PieceType.WOLF, Player.RED, 3, 5)
        game = make_game_with_pieces([rat, wolf1, wolf2, wolf3, wolf4])
        winner, reason = check_win_with_reason(game)
        assert winner == Player.RED
        assert reason == "stalemate"

    def test_win_reason_elimination(self):
        lion = Piece(PieceType.LION, Player.BLUE, 3, 4)
        game = make_game_with_pieces([lion])  # Red has no pieces
        winner, reason = check_win_with_reason(game)
        assert winner == Player.BLUE
        assert reason == "elimination"


class TestPieceHashEquality:
    """Tests for Piece.__hash__ and __eq__ edge cases."""

    def test_hash_consistency(self):
        from jungle_game.engine.pieces import Piece, PieceType, Player
        p1 = Piece(PieceType.LION, Player.BLUE, 0, 0)
        p2 = Piece(PieceType.LION, Player.BLUE, 0, 0)
        assert hash(p1) == hash(p2)

    def test_hash_differs_for_different_pos(self):
        from jungle_game.engine.pieces import Piece, PieceType, Player
        p1 = Piece(PieceType.LION, Player.BLUE, 0, 0)
        p2 = Piece(PieceType.LION, Player.BLUE, 1, 0)
        assert hash(p1) != hash(p2)

    def test_eq_not_implemented_for_other_type(self):
        from jungle_game.engine.pieces import Piece, PieceType, Player
        p = Piece(PieceType.LION, Player.BLUE, 0, 0)
        assert p.__eq__("not a piece") is NotImplemented