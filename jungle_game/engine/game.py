"""Game state management for Jungle (Dou Shou Qi)."""

from __future__ import annotations
import copy
from jungle_game.engine.board import Board
from jungle_game.engine.pieces import Piece, PieceType, Player
from jungle_game.engine.rules import generate_legal_moves, check_win


class GameState:
    """Mutable game state. Supports make_move/undo_move and copying for AI search."""

    def __init__(self):
        self.board = Board()
        self.pieces: list[Piece] = self.board.create_pieces()
        self.current_player = Player.BLUE  # Blue moves first
        self._pieces_by_pos: dict[tuple[int, int], Piece] = {}
        self._move_history: list[tuple] = []  # Stack for undo
        self._winner: Player | None = None
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the position -> piece index."""
        self._pieces_by_pos = {}
        for p in self.pieces:
            self._pieces_by_pos[(p.col, p.row)] = p

    @property
    def pieces_by_pos(self) -> dict[tuple[int, int], Piece]:
        return self._pieces_by_pos

    def get_player_pieces(self, player: Player) -> list[Piece]:
        """Get all pieces belonging to a player."""
        return [p for p in self.pieces if p.player == player]

    def piece_at(self, col: int, row: int) -> Piece | None:
        """Get piece at the given position, or None if empty."""
        return self._pieces_by_pos.get((col, row))

    @property
    def winner(self) -> Player | None:
        return self._winner

    @property
    def is_over(self) -> bool:
        return self._winner is not None

    def make_move(self, from_pos: tuple[int, int], to_pos: tuple[int, int],
                  skip_validation: bool = False):
        """Execute a move. Returns the captured piece if any, or None.

        Args:
            skip_validation: If True, skip the legal-move check. Use in AI search
                where moves are already known to be legal. Defaults to False.

        Raises ValueError if the move is illegal.
        """
        if self._winner is not None:
            raise ValueError("Game is already over")

        piece = self._pieces_by_pos.get(from_pos)
        if piece is None:
            raise ValueError(f"No piece at {from_pos}")
        if piece.player != self.current_player:
            raise ValueError(f"Not {piece.player}'s turn")

        # Verify move is legal (skipped during AI search for performance)
        if not skip_validation:
            legal_moves = generate_legal_moves(self, self.current_player)
            if (from_pos, to_pos) not in legal_moves:
                raise ValueError(f"Illegal move: {from_pos} -> {to_pos}")

        captured = self._pieces_by_pos.get(to_pos)

        # Save state for undo
        self._move_history.append((from_pos, to_pos, piece.copy(), captured.copy() if captured else None))

        # Remove captured piece
        if captured is not None:
            self.pieces.remove(captured)
            del self._pieces_by_pos[to_pos]

        # Move piece
        del self._pieces_by_pos[from_pos]
        piece.col, piece.row = to_pos
        self._pieces_by_pos[to_pos] = piece

        # Switch player
        self.current_player = Player.RED if self.current_player == Player.BLUE else Player.BLUE

        # Check win
        self._winner = check_win(self)

        return captured

    def undo_move(self) -> bool:
        """Undo the last move. Returns True if successful, False if no moves to undo."""
        if not self._move_history:
            return False

        from_pos, to_pos, original_piece, captured_piece = self._move_history.pop()

        # Find the piece that was moved (it's now at to_pos)
        moved_piece = self._pieces_by_pos.get(to_pos)
        if moved_piece is None:
            return False

        # Remove from current position
        del self._pieces_by_pos[to_pos]

        # Restore piece to original position and state
        moved_piece.col = original_piece.col
        moved_piece.row = original_piece.row
        self._pieces_by_pos[from_pos] = moved_piece

        # Restore captured piece
        if captured_piece is not None:
            self.pieces.append(captured_piece)
            self._pieces_by_pos[to_pos] = captured_piece

        # Switch back to the previous player
        self.current_player = Player.RED if self.current_player == Player.BLUE else Player.BLUE

        # Clear winner (move was undone)
        self._winner = None

        return True

    def copy(self) -> "GameState":
        """Create a deep copy of the game state for AI search."""
        new_state = GameState.__new__(GameState)
        new_state.board = self.board  # Board is immutable, safe to share
        new_state.pieces = [p.copy() for p in self.pieces]
        new_state.current_player = self.current_player
        new_state._move_history = []  # Don't copy history for search states
        new_state._winner = self._winner
        new_state._rebuild_index()
        return new_state

    def get_legal_moves(self) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """Get legal moves for the current player."""
        return generate_legal_moves(self, self.current_player)