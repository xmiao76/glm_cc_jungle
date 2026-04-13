"""Board representation for Jungle (Dou Shou Qi).

Coordinate system: (col, row) where col 0-6, row 0-8.
Row 0 = Blue's home row (top), Row 8 = Red's home row (bottom).

Board layout:
  Col: 0   1   2   3   4   5   6
Row 0: L   .   .  [D] .   .   T     <- Blue
Row 1: .   D   .  [T] .   C   .
Row 2: R   .   P   .   W   .   E
Row 3: .  [W] [W] .  [W] [W] .
Row 4: .  [W] [W] .  [W] [W] .
Row 5: .  [W] [W] .  [W] [W] .
Row 6: E   .   W   .   P   .   R
Row 7: .   C   .  [T] .   D   .
Row 8: T   .   .  [D] .   .   L     <- Red

[D]=Den, [T]=Trap, [W]=Water/River
"""

from jungle_game.engine.pieces import Piece, PieceType, Player

# Board dimensions
COLS = 7
ROWS = 9

# Terrain types
LAND = 0
WATER = 1
TRAP = 2
DEN = 3

# Den positions
BLUE_DEN = (3, 0)
RED_DEN = (3, 8)

# Trap positions (3 per player, surrounding each den)
BLUE_TRAPS = {(2, 0), (4, 0), (3, 1)}
RED_TRAPS = {(2, 8), (4, 8), (3, 7)}

# Water squares (two 2x3 rectangles)
WATER_SQUARES = set()
for _c in (1, 2):
    for _r in (3, 4, 5):
        WATER_SQUARES.add((_c, _r))
for _c in (4, 5):
    for _r in (3, 4, 5):
        WATER_SQUARES.add((_c, _r))

# Starting positions: (col, row) -> (PieceType, Player)
STARTING_POSITIONS = {
    # Blue pieces (top, Player.BLUE)
    (0, 0): (PieceType.LION, Player.BLUE),
    (6, 0): (PieceType.TIGER, Player.BLUE),
    (1, 1): (PieceType.DOG, Player.BLUE),
    (5, 1): (PieceType.CAT, Player.BLUE),
    (0, 2): (PieceType.RAT, Player.BLUE),
    (2, 2): (PieceType.LEOPARD, Player.BLUE),
    (4, 2): (PieceType.WOLF, Player.BLUE),
    (6, 2): (PieceType.ELEPHANT, Player.BLUE),
    # Red pieces (bottom, Player.RED)
    (6, 8): (PieceType.LION, Player.RED),
    (0, 8): (PieceType.TIGER, Player.RED),
    (5, 7): (PieceType.DOG, Player.RED),
    (1, 7): (PieceType.CAT, Player.RED),
    (6, 6): (PieceType.RAT, Player.RED),
    (4, 6): (PieceType.LEOPARD, Player.RED),
    (2, 6): (PieceType.WOLF, Player.RED),
    (0, 6): (PieceType.ELEPHANT, Player.RED),
}


class Board:
    """Static board terrain map. Terrain never changes during a game."""

    _terrain: list[list[int]]

    def __init__(self):
        self._terrain = [[LAND] * COLS for _ in range(ROWS)]
        # Set water
        for c, r in WATER_SQUARES:
            self._terrain[r][c] = WATER
        # Set dens
        self._terrain[BLUE_DEN[1]][BLUE_DEN[0]] = DEN
        self._terrain[RED_DEN[1]][RED_DEN[0]] = DEN
        # Set traps
        for c, r in BLUE_TRAPS:
            self._terrain[r][c] = TRAP
        for c, r in RED_TRAPS:
            self._terrain[r][c] = TRAP

    def in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < COLS and 0 <= row < ROWS

    def terrain_at(self, col: int, row: int) -> int:
        """Return terrain type at the given position."""
        return self._terrain[row][col]

    def is_water(self, col: int, row: int) -> bool:
        return self._terrain[row][col] == WATER

    def is_trap(self, col: int, row: int) -> bool:
        return self._terrain[row][col] == TRAP

    def is_den(self, col: int, row: int) -> bool:
        return self._terrain[row][col] == DEN

    def is_own_den(self, col: int, row: int, player: Player) -> bool:
        """Check if position is the given player's own den."""
        if player == Player.BLUE:
            return (col, row) == BLUE_DEN
        return (col, row) == RED_DEN

    def is_opponent_den(self, col: int, row: int, player: Player) -> bool:
        """Check if position is the given player's opponent's den."""
        if player == Player.BLUE:
            return (col, row) == RED_DEN
        return (col, row) == BLUE_DEN

    def is_own_trap(self, col: int, row: int, player: Player) -> bool:
        """Check if position is a trap belonging to the given player."""
        if player == Player.BLUE:
            return (col, row) in BLUE_TRAPS
        return (col, row) in RED_TRAPS

    def is_opponent_trap(self, col: int, row: int, player: Player) -> bool:
        """Check if position is a trap belonging to the given player's opponent."""
        if player == Player.BLUE:
            return (col, row) in RED_TRAPS
        return (col, row) in BLUE_TRAPS

    @staticmethod
    def create_pieces() -> list[Piece]:
        """Create all pieces in their starting positions."""
        pieces = []
        for (col, row), (ptype, player) in STARTING_POSITIONS.items():
            pieces.append(Piece(ptype, player, col, row))
        return pieces