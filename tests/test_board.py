"""Tests for the Board class."""

import pytest
from jungle_game.engine.board import (
    Board, COLS, ROWS, LAND, WATER, TRAP, DEN,
    BLUE_DEN, RED_DEN, BLUE_TRAPS, RED_TRAPS, WATER_SQUARES,
    STARTING_POSITIONS,
)
from jungle_game.engine.pieces import PieceType, Player


class TestBoardDimensions:
    def test_board_dimensions(self):
        assert COLS == 7
        assert ROWS == 9

    def test_in_bounds(self):
        board = Board()
        assert board.in_bounds(0, 0) is True
        assert board.in_bounds(6, 8) is True
        assert board.in_bounds(3, 4) is True
        assert board.in_bounds(-1, 0) is False
        assert board.in_bounds(7, 0) is False
        assert board.in_bounds(0, 9) is False
        assert board.in_bounds(0, -1) is False


class TestBoardTerrain:
    def test_den_positions(self):
        board = Board()
        assert board.terrain_at(*BLUE_DEN) == DEN
        assert board.terrain_at(*RED_DEN) == DEN

    def test_trap_positions(self):
        board = Board()
        for c, r in BLUE_TRAPS:
            assert board.terrain_at(c, r) == TRAP
        for c, r in RED_TRAPS:
            assert board.terrain_at(c, r) == TRAP

    def test_water_positions(self):
        board = Board()
        for c, r in WATER_SQUARES:
            assert board.terrain_at(c, r) == WATER

    def test_water_count(self):
        # Two 2x3 water areas = 12 water squares
        assert len(WATER_SQUARES) == 12

    def test_land_squares(self):
        board = Board()
        land_count = 0
        for r in range(ROWS):
            for c in range(COLS):
                if board.terrain_at(c, r) == LAND:
                    land_count += 1
        # Total squares: 63, minus 2 dens, 6 traps, 12 water = 43 land
        assert land_count == 43

    def test_is_water(self):
        board = Board()
        assert board.is_water(1, 3) is True
        assert board.is_water(2, 5) is True
        assert board.is_water(4, 4) is True
        assert board.is_water(5, 3) is True
        assert board.is_water(3, 4) is False  # Land column between rivers
        assert board.is_water(0, 0) is False

    def test_is_trap(self):
        board = Board()
        assert board.is_trap(2, 0) is True
        assert board.is_trap(4, 0) is True
        assert board.is_trap(3, 1) is True
        assert board.is_trap(2, 8) is True
        assert board.is_trap(4, 8) is True
        assert board.is_trap(3, 7) is True

    def test_is_den(self):
        board = Board()
        assert board.is_den(3, 0) is True
        assert board.is_den(3, 8) is True
        assert board.is_den(0, 0) is False

    def test_own_den(self):
        board = Board()
        assert board.is_own_den(3, 0, Player.BLUE) is True
        assert board.is_own_den(3, 8, Player.RED) is True
        assert board.is_own_den(3, 0, Player.RED) is False
        assert board.is_own_den(3, 8, Player.BLUE) is False

    def test_opponent_den(self):
        board = Board()
        assert board.is_opponent_den(3, 8, Player.BLUE) is True
        assert board.is_opponent_den(3, 0, Player.RED) is True
        assert board.is_opponent_den(3, 0, Player.BLUE) is False
        assert board.is_opponent_den(3, 8, Player.RED) is False

    def test_own_trap(self):
        board = Board()
        assert board.is_own_trap(2, 0, Player.BLUE) is True
        assert board.is_own_trap(2, 0, Player.RED) is False
        assert board.is_own_trap(2, 8, Player.RED) is True

    def test_opponent_trap(self):
        board = Board()
        assert board.is_opponent_trap(2, 8, Player.BLUE) is True
        assert board.is_opponent_trap(2, 0, Player.RED) is True
        assert board.is_opponent_trap(2, 0, Player.BLUE) is False


class TestStartingPositions:
    def test_starting_position_count(self):
        # 8 pieces per player = 16 total
        assert len(STARTING_POSITIONS) == 16

    def test_blue_starting_pieces(self):
        blue_count = sum(1 for _, (__, p) in STARTING_POSITIONS.items() if p == Player.BLUE)
        assert blue_count == 8

    def test_red_starting_pieces(self):
        red_count = sum(1 for _, (__, p) in STARTING_POSITIONS.items() if p == Player.RED)
        assert red_count == 8

    def test_create_pieces(self):
        board = Board()
        pieces = board.create_pieces()
        assert len(pieces) == 16

    def test_all_piece_types_present(self):
        board = Board()
        pieces = board.create_pieces()
        blue_types = {p.piece_type for p in pieces if p.player == Player.BLUE}
        red_types = {p.piece_type for p in pieces if p.player == Player.RED}
        assert blue_types == set(PieceType)
        assert red_types == set(PieceType)