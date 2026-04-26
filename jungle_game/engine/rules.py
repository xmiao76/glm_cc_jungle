"""Legal move generation and capture validation for Jungle (Dou Shou Qi).

Rules summary:
- All pieces move one square orthogonally per turn
- Higher rank captures lower rank; same rank captures
- Rat (1) can capture Elephant (8) but only from land, not from water
- Elephant (8) cannot capture Rat (1) under any circumstance
- Rat in water can only be captured by another Rat also in water
- Rat in water cannot capture pieces on land (except another Rat in water)
- Lion and Tiger can jump across river (Lion: vertical+horizontal, Tiger: vertical only)
- Jump blocked if any Rat (either color) occupies intervening water squares
- Piece entering opponent's trap becomes rank 0
- Piece cannot enter its own den
- Win: enter opponent's den or capture all opponent's pieces
- Stalemate: player with no legal moves loses
"""

from jungle_game.engine.board import Board, COLS, ROWS, WATER_SQUARES
from jungle_game.engine.pieces import Piece, PieceType, Player


def is_capture_valid(
    attacker_type: PieceType,
    attacker_player: Player,
    attacker_col: int,
    attacker_row: int,
    defender: Piece,
    board: Board,
) -> bool:
    """Check if attacker can capture defender.

    Uses attacker_col/attacker_row as the attacker's ORIGINAL position
    (before the move) to correctly determine terrain context.
    """
    # Can't capture own pieces
    if attacker_player == defender.player:
        return False

    attacker_on_water = board.is_water(attacker_col, attacker_row)
    defender_on_water = board.is_water(defender.col, defender.row)
    attacker_on_land = not attacker_on_water
    defender_on_land = not defender_on_water

    # Rat in water cannot capture elephant on land
    if (attacker_type == PieceType.RAT and
            defender.piece_type == PieceType.ELEPHANT and
            attacker_on_water and defender_on_land):
        return False

    # Elephant cannot capture Rat under any circumstance
    if attacker_type == PieceType.ELEPHANT and defender.piece_type == PieceType.RAT:
        return False

    # Rat in water can only capture another Rat also in water
    if (attacker_type == PieceType.RAT and attacker_on_water):
        if defender.piece_type != PieceType.RAT or not defender_on_water:
            return False

    # Rat on land capturing Rat in water is not allowed (different terrain)
    if (attacker_type == PieceType.RAT and defender.piece_type == PieceType.RAT
            and attacker_on_land and defender_on_water):
        return False

    # Determine effective ranks (trap effects)
    defender_rank = _effective_rank(defender, board)
    # Attacker rank at destination (where the capture occurs)
    if board.is_opponent_trap(defender.col, defender.row, attacker_player):
        attacker_rank = 0
    else:
        attacker_rank = int(attacker_type)

    # Higher or equal rank captures
    if attacker_rank >= defender_rank:
        return True

    # Rat on land can capture Elephant (special circular capture)
    if (attacker_type == PieceType.RAT and
            defender.piece_type == PieceType.ELEPHANT and
            attacker_on_land):
        return True

    return False


def _effective_rank(piece: Piece, board: Board) -> int:
    """Get the effective rank of a piece, accounting for trap effects.

    A piece in the opponent's trap has rank 0.
    """
    if board.is_opponent_trap(piece.col, piece.row, piece.player):
        return 0
    return piece.rank


def _get_river_jump_landing(
    piece: Piece, dc: int, dr: int, board: Board
) -> tuple[int, int] | None:
    """Calculate landing position for a lion/tiger river jump.

    Returns the landing (col, row) if a valid jump exists, or None.
    dc, dr is the direction of movement (one of -1, 0, +1 for each).
    """
    if not piece.can_jump_river():
        return None

    # Horizontal jump: Lion only
    if dr == 0 and dc != 0:
        if not piece.can_jump_horizontally():
            return None
        # Check that we're jumping from land adjacent to water
        # The piece is at (col, row) moving in direction dc
        # Water must be in the next squares
        col, row = piece.col + dc, piece.row + dr
        if not board.in_bounds(col, row) or not board.is_water(col, row):
            return None

        # Scan through water squares in that direction
        intervening_rats = False
        while board.in_bounds(col, row) and board.is_water(col, row):
            # Check for rats in water (blocking the jump)
            # We'll check this in the calling function with game state
            col += dc
            row += dr

        if not board.in_bounds(col, row):
            return None

        # Must land on non-water square
        if board.is_water(col, row):
            return None

        return (col, row)

    # Vertical jump: Lion and Tiger
    if dc == 0 and dr != 0:
        col, row = piece.col + dc, piece.row + dr
        if not board.in_bounds(col, row) or not board.is_water(col, row):
            return None

        while board.in_bounds(col, row) and board.is_water(col, row):
            col += dc
            row += dr

        if not board.in_bounds(col, row):
            return None

        if board.is_water(col, row):
            return None

        return (col, row)

    return None


def _is_river_jump_blocked(
    piece: Piece, dc: int, dr: int, board: Board,
    pieces_by_pos: dict[tuple[int, int], Piece]
) -> bool:
    """Check if a river jump is blocked by a Rat in the intervening water squares."""
    col, row = piece.col + dc, piece.row + dr
    while board.in_bounds(col, row) and board.is_water(col, row):
        pos = (col, row)
        if pos in pieces_by_pos:
            blocker = pieces_by_pos[pos]
            if blocker.piece_type == PieceType.RAT:
                return True
        col += dc
        row += dr
    return False


def generate_legal_moves(
    game_state,  # GameState - avoid circular import by using duck typing
    player: Player,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Generate all legal moves for the given player.

    Returns list of (from_pos, to_pos) tuples.
    """
    board = game_state.board
    pieces_by_pos = game_state.pieces_by_pos
    moves = []

    for piece in game_state.get_player_pieces(player):
        from_pos = piece.pos

        # Try all 4 orthogonal directions for normal moves
        for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nc, nr = piece.col + dc, piece.row + dr

            if not board.in_bounds(nc, nr):
                continue

            # Cannot enter own den
            if board.is_own_den(nc, nr, piece.player):
                continue

            # Water entry: only Rat can enter water
            if board.is_water(nc, nr) and not piece.can_enter_water():
                # Lion/Tiger: attempt river jump instead
                if piece.can_jump_river():
                    jump_landing = _get_river_jump_landing(piece, dc, dr, board)
                    if jump_landing is not None:
                        jc, jr = jump_landing
                        # Check if jump is blocked by rat in water
                        if _is_river_jump_blocked(piece, dc, dr, board, pieces_by_pos):
                            continue
                        # Cannot jump into own den
                        if board.is_own_den(jc, jr, piece.player):
                            continue
                        # Check destination
                        target_piece = pieces_by_pos.get((jc, jr))
                        if target_piece is None:
                            moves.append((from_pos, (jc, jr)))
                        elif target_piece.player != piece.player:
                            # Validate capture: use piece's original position for terrain context
                            if is_capture_valid(piece.piece_type, piece.player,
                                                piece.col, piece.row,
                                                target_piece, board):
                                moves.append((from_pos, (jc, jr)))
                continue

            # Normal move to land/trap/den square
            target_piece = pieces_by_pos.get((nc, nr))
            if target_piece is None:
                # Empty square - can always move there
                # But if we're a Rat in water moving to land, that's fine
                # And if target is opponent's den, that's a win move
                moves.append((from_pos, (nc, nr)))
            elif target_piece.player != piece.player:
                # Attempt capture: use piece's original position for terrain context
                if is_capture_valid(piece.piece_type, piece.player,
                                    piece.col, piece.row,
                                    target_piece, board):
                    moves.append((from_pos, (nc, nr)))

    return moves


def check_win(game_state) -> Player | None:
    """Check if the game has been won.

    Returns the winning player, or None if no winner yet.
    """
    winner, _ = check_win_with_reason(game_state)
    return winner


def check_win_with_reason(game_state) -> tuple[Player | None, str]:
    """Check if the game has been won, returning (winner, reason).

    Reason is one of: "den_entry", "elimination", "stalemate", or "" if no winner.
    """
    board = game_state.board
    pieces_by_pos = game_state.pieces_by_pos

    # Check den entry: if any piece is on the opponent's den
    for pos, piece in pieces_by_pos.items():
        if board.is_opponent_den(piece.col, piece.row, piece.player):
            return piece.player, "den_entry"

    # Check elimination: if one player has no pieces
    blue_pieces = game_state.get_player_pieces(Player.BLUE)
    red_pieces = game_state.get_player_pieces(Player.RED)

    if len(blue_pieces) == 0:
        return Player.RED, "elimination"
    if len(red_pieces) == 0:
        return Player.BLUE, "elimination"

    # Check stalemate: if current player has no legal moves
    current = game_state.current_player
    legal_moves = generate_legal_moves(game_state, current)
    if len(legal_moves) == 0:
        # Current player loses
        if current == Player.BLUE:
            return Player.RED, "stalemate"
        return Player.BLUE, "stalemate"

    return None, ""