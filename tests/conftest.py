"""Shared test fixtures and helpers for Jungle game tests."""

from jungle_game.engine.game import GameState
from jungle_game.engine.board import Board
from jungle_game.engine.pieces import Player


def make_game_with_pieces(pieces, current_player=Player.BLUE) -> GameState:
    """Create a GameState with custom piece placement for testing."""
    game = GameState.__new__(GameState)
    game.board = Board()
    game.pieces = pieces
    game.current_player = current_player
    game._move_history = []
    game._winner = None
    game._win_reason = ""
    game._rebuild_index()
    return game