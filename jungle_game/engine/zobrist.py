"""Zobrist hashing keys for Jungle (Dou Shou Qi).

Shared by :mod:`jungle_game.engine.game` (incremental hash maintained on
``make_move``/``undo_move``) and :mod:`jungle_game.engine.ai` (recompute-based
:func:`compute_zobrist_hash` fallback + the search's transposition table).

The random sequence uses a fixed seed and a fixed generation order so the key
values are stable across runs and identical to the Phase 1 baseline. The order
is: ``ZOBRIST_SIDE`` first, then ``ZOBRIST_PIECES`` iterating
``Player → PieceType → row → col``.
"""

from __future__ import annotations
import random

from jungle_game.engine.pieces import PieceType, Player

# Board dimensions (kept here to avoid importing board.py, which would pull in
# more dependencies; these are part of the board's fixed contract).
NCOLS = 7
NROWS = 9

_random = random.Random(42)
ZOBRIST_PIECES: dict[tuple[PieceType, Player, int, int], int] = {}
ZOBRIST_SIDE: int = _random.getrandbits(64)
for _player in Player:
    for _ptype in PieceType:
        for _row in range(NROWS):
            for _col in range(NCOLS):
                ZOBRIST_PIECES[(_ptype, _player, _col, _row)] = _random.getrandbits(64)


def piece_key(piece) -> int:
    """Zobrist key for a piece at its current position."""
    return ZOBRIST_PIECES[(piece.piece_type, piece.player, piece.col, piece.row)]


def initial_hash(pieces, current_player: Player) -> int:
    """Compute the full Zobrist hash for a set of pieces and the side to move."""
    h = 0
    for p in pieces:
        h ^= ZOBRIST_PIECES[(p.piece_type, p.player, p.col, p.row)]
    if current_player == Player.RED:
        h ^= ZOBRIST_SIDE
    return h