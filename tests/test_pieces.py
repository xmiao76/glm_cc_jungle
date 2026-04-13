"""Tests for Piece types and Piece class."""

import pytest
from jungle_game.engine.pieces import Piece, PieceType, Player


class TestPieceType:
    def test_rank_values(self):
        assert PieceType.RAT == 1
        assert PieceType.CAT == 2
        assert PieceType.DOG == 3
        assert PieceType.WOLF == 4
        assert PieceType.LEOPARD == 5
        assert PieceType.TIGER == 6
        assert PieceType.LION == 7
        assert PieceType.ELEPHANT == 8

    def test_all_types_present(self):
        assert len(PieceType) == 8


class TestPiece:
    def test_piece_creation(self):
        p = Piece(PieceType.RAT, Player.BLUE, 0, 2)
        assert p.piece_type == PieceType.RAT
        assert p.player == Player.BLUE
        assert p.col == 0
        assert p.row == 2
        assert p.rank == 1

    def test_piece_pos(self):
        p = Piece(PieceType.ELEPHANT, Player.RED, 0, 6)
        assert p.pos == (0, 6)
        p.pos = (1, 6)
        assert p.col == 1
        assert p.row == 6

    def test_can_enter_water(self):
        rat = Piece(PieceType.RAT, Player.BLUE, 0, 2)
        assert rat.can_enter_water() is True
        cat = Piece(PieceType.CAT, Player.BLUE, 5, 1)
        assert cat.can_enter_water() is False
        elephant = Piece(PieceType.ELEPHANT, Player.RED, 0, 6)
        assert elephant.can_enter_water() is False

    def test_can_jump_river(self):
        lion = Piece(PieceType.LION, Player.BLUE, 0, 0)
        assert lion.can_jump_river() is True
        tiger = Piece(PieceType.TIGER, Player.BLUE, 6, 0)
        assert tiger.can_jump_river() is True
        cat = Piece(PieceType.CAT, Player.BLUE, 5, 1)
        assert cat.can_jump_river() is False

    def test_can_jump_horizontally(self):
        lion = Piece(PieceType.LION, Player.BLUE, 0, 0)
        assert lion.can_jump_horizontally() is True
        tiger = Piece(PieceType.TIGER, Player.BLUE, 6, 0)
        assert tiger.can_jump_horizontally() is False

    def test_piece_copy(self):
        p = Piece(PieceType.DOG, Player.BLUE, 1, 1)
        p2 = p.copy()
        assert p == p2
        assert p is not p2

    def test_piece_equality(self):
        p1 = Piece(PieceType.RAT, Player.BLUE, 0, 2)
        p2 = Piece(PieceType.RAT, Player.BLUE, 0, 2)
        assert p1 == p2

    def test_piece_inequality(self):
        p1 = Piece(PieceType.RAT, Player.BLUE, 0, 2)
        p2 = Piece(PieceType.RAT, Player.RED, 0, 2)
        assert p1 != p2

    def test_piece_name(self):
        p = Piece(PieceType.RAT, Player.BLUE, 0, 2)
        assert p.name == "Rat"

    def test_player_enum(self):
        assert Player.BLUE == 0
        assert Player.RED == 1