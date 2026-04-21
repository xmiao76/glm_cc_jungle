"""Piece types and piece representation for Jungle (Dou Shou Qi)."""

from enum import IntEnum
from dataclasses import dataclass


class Player(IntEnum):
    """Player identifier. Blue is top (row 0), Red is bottom (row 8)."""
    BLUE = 0
    RED = 1


class PieceType(IntEnum):
    """Animal piece types with their rank values."""
    RAT = 1
    CAT = 2
    DOG = 3
    WOLF = 4
    LEOPARD = 5
    TIGER = 6
    LION = 7
    ELEPHANT = 8


# Piece display names
PIECE_NAMES = {
    PieceType.RAT: "Rat",
    PieceType.CAT: "Cat",
    PieceType.DOG: "Dog",
    PieceType.WOLF: "Wolf",
    PieceType.LEOPARD: "Leopard",
    PieceType.TIGER: "Tiger",
    PieceType.LION: "Lion",
    PieceType.ELEPHANT: "Elephant",
}


@dataclass
class Piece:
    """A single piece on the board."""
    piece_type: PieceType
    player: Player
    col: int
    row: int

    @property
    def rank(self) -> int:
        """Base rank of this piece type."""
        return int(self.piece_type)

    @property
    def name(self) -> str:
        return PIECE_NAMES[self.piece_type]

    @property
    def pos(self) -> tuple[int, int]:
        return (self.col, self.row)

    @pos.setter
    def pos(self, value: tuple[int, int]):
        self.col, self.row = value

    def can_enter_water(self) -> bool:
        """Only the rat can enter water squares."""
        return self.piece_type == PieceType.RAT

    def can_jump_river(self) -> bool:
        """Lion and Tiger can jump across the river."""
        return self.piece_type in (PieceType.LION, PieceType.TIGER)

    def can_jump_horizontally(self) -> bool:
        """Only the Lion can jump horizontally across the river."""
        return self.piece_type == PieceType.LION

    def __hash__(self):
        return hash((self.piece_type, self.player, self.col, self.row))

    def __eq__(self, other):
        if not isinstance(other, Piece):
            return NotImplemented
        return (self.piece_type == other.piece_type and
                self.player == other.player and
                self.col == other.col and
                self.row == other.row)

    def copy(self) -> "Piece":
        return Piece(self.piece_type, self.player, self.col, self.row)