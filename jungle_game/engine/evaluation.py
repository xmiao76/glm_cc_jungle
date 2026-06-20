"""Evaluation function for Jungle (Dou Shou Qi).

The evaluation is *symmetric*: for any position ``g`` and the two players
``A``/``B``, ``evaluate(g, A) == -evaluate(g, B)``. This invariant is required
by the negamax search in :mod:`jungle_game.engine.ai` and is enforced by a
regression test. Every scoring term that rewards one side has a mirrored term
that penalises the other side by the exact same amount, and the piece-square
tables are built mirror-symmetric by construction.

Scoring components:
- Material (piece values tuned for Jungle's circular capture rules)
- Piece-square tables (PSTs): per-piece positional value encoding den-attack
  advancement, central control, and piece-specific preferences (Rat near water,
  Lion/Tiger on river-jump lanes). Precomputed for an O(1) per-piece lookup.
- Symmetric den-defense (defenders near a threatened own den are rewarded)
- Trap handling (own piece in opponent's trap becomes rank 0 = vulnerable)
- Adjacent capture threats (MVV-LVA style)
- Mobility for both sides
- Endgame knowledge (Rat<->Elephant, dominant Lion/Tiger, immediate empty-den
  adjacency)

Weights are configurable via :class:`EvalConfig` (see ``set_eval_config``),
which the self-play tuning/elo-match harness uses for A/B testing.
"""

from __future__ import annotations
from dataclasses import dataclass

from jungle_game.engine.pieces import PieceType, Player
from jungle_game.engine.rules import is_capture_valid
from jungle_game.engine.game import GameState
from jungle_game.engine.board import WATER_SQUARES

# Win score returned for a terminal (won/lost) position. Kept stable at 100000
# so existing tests and the search's mate scoring stay consistent.
MATE = 100_000

# Piece material values (tuned for Jungle).
PIECE_VALUES = {
    PieceType.RAT: 400,
    PieceType.CAT: 150,
    PieceType.DOG: 400,
    PieceType.WOLF: 450,
    PieceType.LEOPARD: 600,
    PieceType.TIGER: 900,
    PieceType.LION: 1000,
    PieceType.ELEPHANT: 950,
}

# The den each player attacks (opponent's den).
DEN_POSITIONS = {
    Player.BLUE: (3, 8),  # Blue attacks Red's den at (3,8)
    Player.RED: (3, 0),   # Red attacks Blue's den at (3,0)
}

# Per-piece multiplier for den-attack advancement. Jumpers (Lion/Tiger) and the
# Rat (can swim and kill the Elephant) advance more valuably than the weak Cat.
ADVANCE_MULTIPLIER = {
    PieceType.RAT: 1.2,
    PieceType.CAT: 0.8,
    PieceType.DOG: 0.9,
    PieceType.WOLF: 1.0,
    PieceType.LEOPARD: 1.0,
    PieceType.TIGER: 1.3,
    PieceType.LION: 1.4,
    PieceType.ELEPHANT: 1.0,
}

# Orthogonal directions (pieces move one square orthogonally).
DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))

# Distance thresholds (Manhattan) for den proximity bonuses.
NEAR_DEN_DIST = 2       # "close" to a den
DEFENDER_DIST = 2       # considered a defender if within this of own den
ENDGAME_PIECE_COUNT = 6  # total pieces at or below which endgame terms apply


@dataclass(frozen=True)
class EvalConfig:
    """Tunable evaluation weights. ``DEFAULT_CONFIG`` reproduces the shipped
    baseline; the tuning/elo-match harness swaps in candidates via
    :func:`set_eval_config` (which rebuilds the piece-square tables)."""
    # Advancement / den-proximity (baked into the PST).
    advance_weight: int = 20
    near_den_bonus: int = 120
    one_step_bonus: int = 400
    # Piece-specific positional bonuses (baked into the PST).
    center_weight: int = 6
    rat_water_bonus: int = 30
    jump_lane_bonus: int = 25
    # Other terms (read live from the active config).
    defender_bonus: int = 50
    home_crowd_penalty: int = 15
    trap_penalty_divisor: int = 2
    threat_divisor: int = 4
    mobility_weight: int = 4
    empty_den_adjacency_bonus: int = 800
    endgame_mult: float = 1.5
    rat_vs_elephant_bonus: int = 200
    dominant_jumper_bonus: int = 300
    # The piece-square tables (central control + Rat-near-water + jump-lane
    # bonuses) are OFF by default: self-play measurement (scripts/elo_match.py)
    # found the PST extras net-harmful at the tested time control vs the plain
    # advancement formula. The shipped engine uses the formula; PSTs are opt-in
    # via EvalConfig(use_pst=True) for experimentation.
    use_pst: bool = False


DEFAULT_CONFIG = EvalConfig()

# Active configuration and the PSTs built from it. Swapped via set_eval_config.
_active_config: EvalConfig = DEFAULT_CONFIG
_pst_base: dict[PieceType, list[list[int]]] = {}


def _opponent(player: Player) -> Player:
    return Player.RED if player == Player.BLUE else Player.BLUE


# --- Piece-square tables ---------------------------------------------------

def _near_water(col: int, row: int) -> bool:
    """True if (col, row) is orthogonally adjacent to a water square.

    Water sits in the middle rows (3-5) and side columns (1,2,4,5); adjacency to
    it is mirror-symmetric under row -> 8-row and col -> 6-col, so the resulting
    Rat bonus preserves evaluation symmetry.
    """
    for dc, dr in DIRECTIONS:
        if (col + dc, row + dr) in WATER_SQUARES:
            return True
    return False


def _build_pst(piece_type: PieceType, config: EvalConfig) -> list[list[int]]:
    """Build a 9x7 PST for ``piece_type`` in the "attacking row 8" frame.

    ``table[row][col]`` is the positional value for a piece of this type at
    ``(col, row)`` assuming the side attacks the den at row 8 (Blue's frame). A
    Red piece at ``(c, r)`` reads ``table[8 - r][c]`` (vertical mirror), which
    yields the symmetric value for attacking the den at row 0. Every component
    (advancement, center, water/jump-lane) is mirror-symmetric, so the table is
    valid for both sides without per-side variants.
    """
    table = [[0] * 7 for _ in range(9)]
    mult = ADVANCE_MULTIPLIER[piece_type]
    for r in range(9):
        for c in range(7):
            rows_to_den = 8 - r          # rows from the target den (row 8)
            col_off = abs(c - 3)
            d_atk = rows_to_den + col_off
            v = 0
            # Den-attack advancement (replaces the old per-piece formula).
            v += (16 - d_atk) * config.advance_weight * mult
            if d_atk <= NEAR_DEN_DIST:
                v += (3 - d_atk) * config.near_den_bonus
            if d_atk <= 1:
                v += config.one_step_bonus
            # Central control (max at the board centre (3, 4), mirror-symmetric).
            center_dist = abs(c - 3) + abs(r - 4)
            v += (6 - center_dist) * config.center_weight
            # Piece-specific positional preferences.
            if piece_type == PieceType.RAT and _near_water(c, r):
                v += config.rat_water_bonus
            if piece_type in (PieceType.LION, PieceType.TIGER) and c in (1, 2, 4, 5):
                v += config.jump_lane_bonus
            table[r][c] = v
    return table


def _build_all_psts(config: EvalConfig) -> dict[PieceType, list[list[int]]]:
    return {pt: _build_pst(pt, config) for pt in PieceType}


def set_eval_config(config: EvalConfig) -> None:
    """Set the active eval config and rebuild the piece-square tables."""
    global _active_config, _pst_base
    _active_config = config
    _pst_base = _build_all_psts(config)


def reset_eval_config() -> None:
    """Restore the shipped default eval config (used by tests/fixtures)."""
    set_eval_config(DEFAULT_CONFIG)


# Build the default PSTs at import time.
_pst_base = _build_all_psts(DEFAULT_CONFIG)


def _pst_value(piece) -> int:
    """Symmetric PST lookup for a piece (vertical mirror for Red)."""
    er = piece.row if piece.player == Player.BLUE else 8 - piece.row
    return _pst_base[piece.piece_type][er][piece.col]


def _piece_positional(piece, board, pieces_by_pos) -> int:
    """Advancement (PST or inlined formula) + home-crowd + trap + adjacent threats.

    Depends only on the piece and the board state (not on the eval perspective),
    so it is symmetric: the same value is added for a own piece and subtracted
    for an opponent piece, preserving ``evaluate(g, A) == -evaluate(g, B)``.

    The formula is inlined (rather than calling a helper) to avoid a per-piece
    function-call in the search's hottest path; ``DEN_POSITIONS[player]`` is the
    den that player attacks, so advancement is measured toward that den.
    """
    cfg = _active_config
    if cfg.use_pst:
        score = _pst_value(piece)
    else:
        target_den = DEN_POSITIONS[piece.player]
        d_atk = abs(piece.col - target_den[0]) + abs(piece.row - target_den[1])
        score = (16 - d_atk) * cfg.advance_weight * ADVANCE_MULTIPLIER[piece.piece_type]
        if d_atk <= NEAR_DEN_DIST:
            score += (3 - d_atk) * cfg.near_den_bonus
        if d_atk <= 1:
            score += cfg.one_step_bonus

    # Small penalty for idling on top of our own den area (home crowd).
    own_den = DEN_POSITIONS[_opponent(piece.player)]
    d_def = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
    if d_def <= DEFENDER_DIST:
        score -= (3 - d_def) * cfg.home_crowd_penalty

    # Our piece in the opponent's trap becomes rank 0 — very vulnerable.
    if board.is_opponent_trap(piece.col, piece.row, piece.player):
        score -= PIECE_VALUES[piece.piece_type] // cfg.trap_penalty_divisor

    # Adjacent capture threats (we can capture a neighbouring enemy).
    for dc, dr in DIRECTIONS:
        target = pieces_by_pos.get((piece.col + dc, piece.row + dr))
        if (target is not None and target.player != piece.player
                and is_capture_valid(piece.piece_type, piece.player,
                                     piece.col, piece.row, target, board)):
            score += PIECE_VALUES[target.piece_type] // cfg.threat_divisor

    return score


def _terminal_score(game_state: GameState, player: Player) -> tuple[bool, int]:
    """Cheap terminal detection (den-entry + elimination only).

    Stalemate is intentionally NOT checked here — it requires a full legal-move
    generation and is handled by the search via ``GameState.is_over`` (set by
    ``make_move``). Den-entry and elimination are detected in a single pass.
    Returns (is_terminal, score_from_player_perspective).
    """
    board = game_state.board
    blue_count = 0
    red_count = 0
    for piece in game_state.pieces:
        if board.is_opponent_den(piece.col, piece.row, piece.player):
            return True, MATE if piece.player == player else -MATE
        if piece.player == Player.BLUE:
            blue_count += 1
        else:
            red_count += 1
    if blue_count == 0:
        return True, MATE if Player.RED == player else -MATE
    if red_count == 0:
        return True, MATE if Player.BLUE == player else -MATE
    return False, 0


def _mobility(piece, board, pieces_by_pos) -> int:
    """Count open orthogonal neighbours for a piece (cheap mobility proxy)."""
    mobility = 0
    for dc, dr in DIRECTIONS:
        nc, nr = piece.col + dc, piece.row + dr
        if not board.in_bounds(nc, nr):
            continue
        if board.is_water(nc, nr) and not piece.can_enter_water():
            continue
        if board.is_own_den(nc, nr, piece.player):
            continue
        blocker = pieces_by_pos.get((nc, nr))
        if blocker is not None and blocker.player == piece.player:
            continue
        mobility += 1
    return mobility


def _adjacent_to_empty_den(piece, den, board, pieces_by_pos) -> bool:
    """True if ``piece`` is orthogonally adjacent to ``den`` and it is empty."""
    for dc, dr in DIRECTIONS:
        nc, nr = piece.col + dc, piece.row + dr
        if (nc, nr) == den and pieces_by_pos.get(den) is None:
            return True
    return False


def evaluate(game_state: GameState, player: Player) -> int:
    """Evaluate the position from ``player``'s perspective.

    Positive = good for ``player``, negative = bad. Symmetric:
    ``evaluate(g, A) == -evaluate(g, B)``.
    """
    if game_state.is_over:
        return MATE if game_state.winner == player else -MATE

    is_term, term = _terminal_score(game_state, player)
    if is_term:
        return term

    cfg = _active_config
    board = game_state.board
    opp = _opponent(player)
    target_den = DEN_POSITIONS[player]   # opponent's den (we attack)
    own_den = DEN_POSITIONS[opp]          # our den (we defend)
    pieces_by_pos = game_state.pieces_by_pos

    own_pieces = [p for p in game_state.pieces if p.player == player]
    opp_pieces = [p for p in game_state.pieces if p.player == opp]
    total_pieces = len(own_pieces) + len(opp_pieces)
    is_endgame = total_pieces <= ENDGAME_PIECE_COUNT
    endgame_mult = cfg.endgame_mult if is_endgame else 1.0

    score = 0

    own_defenders = []   # (piece, dist_to_own_den) near our den
    opp_defenders = []   # (piece, dist_to_opp_den) near their den
    own_threats_den = 0  # our pieces close to opponent's den
    opp_threats_den = 0  # opponent pieces close to our den

    for piece in own_pieces:
        score += PIECE_VALUES[piece.piece_type]
        score += int(_piece_positional(piece, board, pieces_by_pos) * endgame_mult)
        d_def = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
        if d_def <= DEFENDER_DIST:
            own_defenders.append((piece, d_def))
        d_atk = abs(piece.col - target_den[0]) + abs(piece.row - target_den[1])
        if d_atk <= DEFENDER_DIST:
            own_threats_den += 1

    for piece in opp_pieces:
        score -= PIECE_VALUES[piece.piece_type]
        score -= int(_piece_positional(piece, board, pieces_by_pos) * endgame_mult)
        d_def = abs(piece.col - target_den[0]) + abs(piece.row - target_den[1])
        if d_def <= DEFENDER_DIST:
            opp_defenders.append((piece, d_def))
        d_atk = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
        if d_atk <= DEFENDER_DIST:
            opp_threats_den += 1

    # Symmetric den-defense.
    if opp_threats_den > 0:
        for _, d in own_defenders:
            score += (3 - d) * cfg.defender_bonus
    if own_threats_den > 0:
        for _, d in opp_defenders:
            score -= (3 - d) * cfg.defender_bonus

    # Mobility for both sides (symmetric).
    for piece in own_pieces:
        score += _mobility(piece, board, pieces_by_pos) * cfg.mobility_weight
    for piece in opp_pieces:
        score -= _mobility(piece, board, pieces_by_pos) * cfg.mobility_weight

    # Endgame knowledge (symmetric).
    if is_endgame:
        own_types = {p.piece_type for p in own_pieces}
        opp_types = {p.piece_type for p in opp_pieces}

        if PieceType.RAT in own_types and PieceType.ELEPHANT in opp_types:
            score += cfg.rat_vs_elephant_bonus
        if PieceType.RAT in opp_types and PieceType.ELEPHANT in own_types:
            score -= cfg.rat_vs_elephant_bonus

        own_dominant = (PieceType.LION in own_types or PieceType.TIGER in own_types)
        opp_dominant = (PieceType.LION in opp_types or PieceType.TIGER in opp_types)
        if own_dominant and PieceType.RAT not in opp_types:
            score += cfg.dominant_jumper_bonus
        if opp_dominant and PieceType.RAT not in own_types:
            score -= cfg.dominant_jumper_bonus

    # Immediate winning threat: a piece adjacent to the opponent's EMPTY den.
    for piece in own_pieces:
        if _adjacent_to_empty_den(piece, target_den, board, pieces_by_pos):
            score += cfg.empty_den_adjacency_bonus
    for piece in opp_pieces:
        if _adjacent_to_empty_den(piece, own_den, board, pieces_by_pos):
            score -= cfg.empty_den_adjacency_bonus

    return score