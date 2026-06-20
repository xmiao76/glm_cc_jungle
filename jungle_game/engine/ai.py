"""AI engine for Jungle (Dou Shou Qi).

Negamax search with alpha-beta pruning and a collection of standard
strength-enhancing techniques:

- Iterative deepening with a hard time limit
- **Clean time abort**: when the time budget runs out the search raises
  ``_TimeUp`` instead of returning a meaningless stand-pat score. The root
  only commits the best move from a *fully completed* iteration, so a
  time-aborted deep iteration never replaces a good move with a garbage one
  (this was the critical bug in the previous implementation).
- Principal Variation Search (PVS / zero-window) for non-first moves
- Late move reduction (LMR) for late quiet moves
- Null-move pruning (zero-window, side-to-move agnostic via negamax)
- Move ordering: transposition-table best move -> winning den entry ->
  captures (MVV-LVA) -> killer moves -> history heuristic
- Two-bucket transposition table with Zobrist hashing and ply-aware
  mate-score encoding/decoding
- Quiescence search over captures and den-entry moves to avoid the horizon
  effect
- Node-count-based time checks for efficiency

The evaluation lives in :mod:`jungle_game.engine.evaluation` and is symmetric
(``evaluate(g, A) == -evaluate(g, B)``), which is what makes negamax valid.
"""

from __future__ import annotations
import time

from jungle_game.engine.pieces import PieceType, Player
from jungle_game.engine.rules import generate_legal_moves
from jungle_game.engine.game import GameState
from jungle_game.engine.evaluation import evaluate, PIECE_VALUES, MATE
from jungle_game.engine.zobrist import ZOBRIST_PIECES, ZOBRIST_SIDE

# Re-exported so callers can ``from jungle_game.engine.ai import evaluate``.
__all__ = [
    "find_best_move", "evaluate", "order_moves", "PIECE_VALUES",
    "compute_zobrist_hash", "TranspositionTable",
    "EXACT", "LOWERBOUND", "UPPERBOUND", "clear_tt",
    "DEFAULT_TIME_LIMIT_MS", "NULL_MOVE_R", "LMR_MIN_DEPTH",
]

DEFAULT_TIME_LIMIT_MS = 1500

# Null-move pruning reduction and safety threshold.
NULL_MOVE_R = 2
NULL_MOVE_MIN_PIECES = 3

# Late move reduction parameters.
LMR_MIN_DEPTH = 3
LMR_MOVE_INDEX = 4   # reduce moves at index >= this
LMR_REDUCTION = 1

# Quiescence search depth cap.
MAX_Q_DEPTH = 4

# Den-threat search extensions: extend depth by 1 when a move puts a piece
# adjacent to the opponent's empty den (a forced-win threat the opponent must
# answer, analogous to a check extension). Capped per path to avoid explosion.
MAX_EXTENSIONS = 2

# Time-check interval (nodes between time checks). Smaller => tighter time
# compliance at the cost of marginally more time.time() calls (negligible).
TIME_CHECK_NODES = 2048

# Search bounds.
INF = 1_000_000
MATE_THRESHOLD = MATE - 1000   # scores with abs > this are mate scores
MAX_PLY = 64                   # maximum search depth in plies
MAX_ITER_DEPTH = 40            # iterative-deepening depth cap

# Board index helpers for the history heuristic (7 cols x 9 rows = 63 squares).
_NCOLS = 7
_NROWS = 9
_NSQ = _NCOLS * _NROWS


def _sq(pos: tuple[int, int]) -> int:
    return pos[1] * _NCOLS + pos[0]


# --- Zobrist hashing -------------------------------------------------------
# Keys live in jungle_game.engine.zobrist (shared with GameState, which maintains
# the hash incrementally on make_move/undo_move). compute_zobrist_hash below is a
# recompute fallback used by tests; the search uses game_state.zobrist_hash.

# Transposition-table entry flags.
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2


def compute_zobrist_hash(game_state: GameState) -> int:
    """Compute the Zobrist hash for the current game state."""
    h = 0
    for piece in game_state.pieces:
        h ^= ZOBRIST_PIECES.get((piece.piece_type, piece.player, piece.col, piece.row), 0)
    if game_state.current_player == Player.RED:
        h ^= ZOBRIST_SIDE
    return h


def _opponent(player: Player) -> Player:
    return Player.RED if player == Player.BLUE else Player.BLUE


def _tt_encode(score: int, ply: int) -> int:
    """Make a mate score ply-independent before storing in the TT."""
    if score > MATE_THRESHOLD:
        return score + ply
    if score < -MATE_THRESHOLD:
        return score - ply
    return score


def _tt_decode(score: int, ply: int) -> int:
    """Restore a mate score to the current ply after retrieving from the TT."""
    if score > MATE_THRESHOLD:
        return score - ply
    if score < -MATE_THRESHOLD:
        return score + ply
    return score


class TranspositionTable:
    """Two-bucket transposition table (depth-preferred + always-replace)."""

    def __init__(self, depth_size: int = 500_000, always_size: int = 500_000):
        self._depth_table: dict[int, dict] = {}
        self._always_table: dict[int, dict] = {}
        self._depth_max = depth_size
        self._always_max = always_size

    def lookup(self, hash_key: int, depth: int) -> tuple[int, int, tuple] | None:
        """Return (score, flag, best_move) for a sufficient-depth entry, or None."""
        entry = self._depth_table.get(hash_key)
        if entry is not None and entry['depth'] >= depth:
            return entry['score'], entry['flag'], entry['best_move']
        entry = self._always_table.get(hash_key)
        if entry is not None and entry['depth'] >= depth:
            return entry['score'], entry['flag'], entry['best_move']
        return None

    def store(self, hash_key: int, depth: int, score: int, flag: int,
              best_move: tuple | None) -> None:
        """Store a position in both buckets."""
        record = {'depth': depth, 'score': score, 'flag': flag, 'best_move': best_move}

        if len(self._always_table) >= self._always_max:
            self._always_table.clear()
        self._always_table[hash_key] = record

        existing = self._depth_table.get(hash_key)
        if existing is not None and existing['depth'] > depth:
            return
        if len(self._depth_table) >= self._depth_max:
            self._depth_table.clear()
        self._depth_table[hash_key] = record

    def clear(self):
        self._depth_table.clear()
        self._always_table.clear()


# Persistent transposition table and per-search state.
_tt = TranspositionTable()
_node_count = 0
_history: list[int] = []          # [_NSQ * _NSQ] flat array, reset per search
_killers: list[list] = []         # [[move, move], ...] per ply, reset per search
_last_depth = 0                   # depth of the last completed iteration
# Den-threat extensions are OFF by default: self-play measurement (see
# scripts/elo_match.py) found them net-harmful at the tested time control (the
# engine over-commits to refutable den attacks). They remain selectable via
# set_extensions_enabled(True) for experimentation.
_extensions_enabled = False


def clear_tt():
    """Clear the persistent transposition table (call between games)."""
    _tt.clear()


def set_extensions_enabled(enabled: bool) -> None:
    """Toggle den-threat search extensions (used by the elo-match harness)."""
    global _extensions_enabled
    _extensions_enabled = enabled


def _reset_search_state():
    """Reset history and killer tables for a new search."""
    global _history, _killers
    _history = [0] * (_NSQ * _NSQ)
    _killers = [[None, None] for _ in range(MAX_PLY)]


class _TimeUp(Exception):
    """Raised internally when the search budget is exhausted."""


def _time_up(start_time: float, time_limit: float) -> bool:
    return _node_count % TIME_CHECK_NODES == 0 and time.time() - start_time > time_limit


def _is_capture_or_den(game_state, pieces_by_pos, to_pos, current) -> tuple[bool, bool]:
    """Return (is_capture, is_winning_den_entry) for a move's destination."""
    target = pieces_by_pos.get(to_pos)
    is_capture = target is not None
    is_den = game_state.board.is_opponent_den(to_pos[0], to_pos[1], current)
    return is_capture, is_den


def order_moves(moves: list, game_state: GameState, tt_move: tuple | None = None,
                killers: list | None = None, history: list | None = None) -> list:
    """Order moves for better alpha-beta pruning.

    Priority (highest first):
    1. Transposition-table best move
    2. Winning den-entry moves
    3. Captures (MVV-LVA: most valuable victim, least valuable attacker)
    4. Killer moves (quiet cutoff moves)
    5. History heuristic score
    6. Remaining quiet moves

    The public 2-argument form ``order_moves(moves, game_state)`` keeps the
    captures-first / den-entry-prioritised behaviour relied on by tests.
    """
    pieces_by_pos = game_state.pieces_by_pos
    current = game_state.current_player
    board = game_state.board
    scored = []

    killer_set = set(killers) if killers else set()

    for from_pos, to_pos in moves:
        if tt_move is not None and (from_pos, to_pos) == tt_move:
            priority = 1_000_000
        elif board.is_opponent_den(to_pos[0], to_pos[1], current):
            priority = 900_000
        else:
            target = pieces_by_pos.get(to_pos)
            if target is not None:
                victim = PIECE_VALUES[target.piece_type]
                attacker = pieces_by_pos.get(from_pos)
                attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
                priority = 100_000 + victim * 16 - attacker_value
            elif (from_pos, to_pos) in killer_set:
                priority = 80_000
            elif history is not None:
                priority = history[_sq(from_pos) * _NSQ + _sq(to_pos)]
            else:
                priority = 0
        scored.append((priority, from_pos, to_pos))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(fp, tp) for _, fp, tp in scored]


def _order_quiescence(moves, game_state) -> list:
    """Order quiescence moves (captures + den entries) by MVV-LVA / den value."""
    pieces_by_pos = game_state.pieces_by_pos
    current = game_state.current_player
    board = game_state.board
    scored = []
    for from_pos, to_pos in moves:
        if board.is_opponent_den(to_pos[0], to_pos[1], current):
            priority = 900_000
        else:
            target = pieces_by_pos.get(to_pos)
            victim = PIECE_VALUES[target.piece_type]
            attacker = pieces_by_pos.get(from_pos)
            attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
            priority = 100_000 + victim * 16 - attacker_value
        scored.append((priority, from_pos, to_pos))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(fp, tp) for _, fp, tp in scored]


def _quiescence(game_state, alpha: int, beta: int, ply: int,
                start_time: float, time_limit: float, q_depth: int) -> int:
    """Quiescence search: extend on captures and den-entry moves.

    Returns a score from the side-to-move's perspective (negamax convention).
    """
    global _node_count
    _node_count += 1
    if _time_up(start_time, time_limit):
        raise _TimeUp()

    # Terminal positions (winner already set by the move that led here).
    if game_state.is_over:
        winner = game_state._winner
        if winner == game_state.current_player:
            return MATE - ply
        return -MATE + ply

    stand_pat = evaluate(game_state, game_state.current_player)
    if stand_pat >= beta:
        return stand_pat
    if stand_pat > alpha:
        alpha = stand_pat
    if q_depth >= MAX_Q_DEPTH:
        return alpha

    current = game_state.current_player
    pieces_by_pos = game_state.pieces_by_pos
    board = game_state.board

    # Only consider forcing moves: captures and immediate den entries.
    forcing = []
    for from_pos, to_pos in generate_legal_moves(game_state, current):
        target = pieces_by_pos.get(to_pos)
        if target is not None or board.is_opponent_den(to_pos[0], to_pos[1], current):
            forcing.append((from_pos, to_pos))
    if not forcing:
        return alpha

    best = stand_pat
    for from_pos, to_pos in _order_quiescence(forcing, game_state):
        game_state.make_move(from_pos, to_pos, skip_validation=True)
        try:
            score = -_quiescence(game_state, -beta, -alpha, ply + 1,
                                 start_time, time_limit, q_depth + 1)
        finally:
            game_state.undo_move()
        if score >= beta:
            return score
        if score > best:
            best = score
            if best > alpha:
                alpha = best
    return best


def _count_pieces(game_state, player: Player) -> int:
    return sum(1 for p in game_state.pieces if p.player == player)


# Dens each side attacks (mover wins by entering the opponent's den).
_DEN_TARGET = {Player.BLUE: (3, 8), Player.RED: (3, 0)}


def _move_creates_den_threat(game_state, to_pos: tuple[int, int],
                              mover: Player) -> bool:
    """True if the just-moved piece now threatens to enter the opponent's den.

    The piece at ``to_pos`` (belonging to ``mover``) is a forced-win threat when
    it is orthogonally adjacent to ``mover``'s target den AND that den is empty —
    the opponent must respond or lose next move. Used for the den-threat
    (check-style) search extension.
    """
    target_den = _DEN_TARGET[mover]
    if abs(to_pos[0] - target_den[0]) + abs(to_pos[1] - target_den[1]) != 1:
        return False
    return game_state.pieces_by_pos.get(target_den) is None


def _negamax(game_state, depth: int, alpha: int, beta: int, ply: int,
             start_time: float, time_limit: float, can_null: bool = True,
             ext_left: int = MAX_EXTENSIONS) -> int:
    """Negamax with PVS, null-move pruning, LMR, killers, history and the TT.

    Returns a score from the side-to-move's perspective. ``ext_left`` bounds the
    number of den-threat extensions remaining on the current search path.
    """
    global _node_count, _history, _killers
    _node_count += 1
    if _time_up(start_time, time_limit):
        raise _TimeUp()

    # Terminal: the move that led here already ended the game.
    if game_state.is_over:
        winner = game_state._winner
        if winner == game_state.current_player:
            return MATE - ply
        return -MATE + ply

    hash_key = game_state.zobrist_hash
    tt_move = None
    tt_entry = _tt.lookup(hash_key, depth)
    if tt_entry is not None:
        tt_score, tt_flag, tt_move = tt_entry
        tt_score = _tt_decode(tt_score, ply)
        if tt_flag == EXACT:
            return tt_score
        if tt_flag == LOWERBOUND and tt_score > alpha:
            alpha = tt_score
        elif tt_flag == UPPERBOUND and tt_score < beta:
            beta = tt_score
        if alpha >= beta:
            return tt_score

    if depth <= 0:
        return _quiescence(game_state, alpha, beta, ply, start_time, time_limit, 0)

    current = game_state.current_player
    opp = _opponent(current)
    moves = generate_legal_moves(game_state, current)
    if not moves:
        return -MATE + ply   # stalemate: side to move loses (safety net)

    moves = order_moves(moves, game_state, tt_move, _killers[ply], _history)
    pieces_by_pos = game_state.pieces_by_pos
    board = game_state.board

    # Null-move pruning: pass and search at reduced depth; fail-high => cutoff.
    # Only worth it from depth 3, so skip the (cheap but repeated) piece counts
    # at shallower nodes where the bulk of the tree lives.
    if can_null and depth >= 3:
        own_count = _count_pieces(game_state, current)
        opp_count = _count_pieces(game_state, opp)
        if own_count >= NULL_MOVE_MIN_PIECES and opp_count >= NULL_MOVE_MIN_PIECES:
            # Flip the side-to-move AND the incremental hash's side key together
            # so the child reads the correct zobrist_hash for the passed position
            # (a direct current_player assignment alone leaves the hash stale,
            # causing wrong TT cutoffs and TT pollution under time abort).
            game_state.current_player = opp
            game_state._zobrist ^= ZOBRIST_SIDE
            try:
                null_score = -_negamax(game_state, depth - 1 - NULL_MOVE_R,
                                       -beta, -beta + 1, ply + 1,
                                       start_time, time_limit, can_null=False,
                                       ext_left=ext_left)
            finally:
                game_state.current_player = current
                game_state._zobrist ^= ZOBRIST_SIDE
            if null_score >= beta:
                return null_score

    best = -INF
    best_move = None
    orig_alpha = alpha

    for move_idx, (from_pos, to_pos) in enumerate(moves):
        is_capture, is_den = _is_capture_or_den(game_state, pieces_by_pos, to_pos, current)
        is_quiet = not is_capture and not is_den

        game_state.make_move(from_pos, to_pos, skip_validation=True)
        # Den-threat extension: if this move puts the mover's piece next to the
        # opponent's empty den (a forced-win threat), search at full depth
        # instead of depth-1. Capped per path via ext_left.
        extend = (_extensions_enabled and ext_left > 0
                  and _move_creates_den_threat(game_state, to_pos, current))
        child_depth = depth if extend else depth - 1
        child_ext = ext_left - 1 if extend else ext_left
        try:
            if move_idx == 0:
                # First (expected-best) move: full window.
                score = -_negamax(game_state, child_depth, -beta, -alpha, ply + 1,
                                  start_time, time_limit, ext_left=child_ext)
            else:
                # Late move reduction for late quiet moves (not applied when
                # extending, since child_depth is already full depth).
                if (not extend and move_idx >= LMR_MOVE_INDEX
                        and depth >= LMR_MIN_DEPTH and is_quiet):
                    score = -_negamax(game_state, child_depth - LMR_REDUCTION,
                                      -alpha - 1, -alpha, ply + 1,
                                      start_time, time_limit, ext_left=child_ext)
                else:
                    score = -_negamax(game_state, child_depth, -alpha - 1, -alpha,
                                      ply + 1, start_time, time_limit, ext_left=child_ext)
                # Re-search with the full window if the reduced/zero-window beat alpha.
                if score > alpha and score < beta:
                    score = -_negamax(game_state, child_depth, -beta, -alpha, ply + 1,
                                      start_time, time_limit, ext_left=child_ext)
        finally:
            # Keep make/undo paired even when a _TimeUp abort propagates up.
            game_state.undo_move()

        if score > best:
            best = score
            best_move = (from_pos, to_pos)
            if best > alpha:
                alpha = best

        if alpha >= beta:
            # Beta cutoff: record quiet cutoff moves for future ordering.
            if is_quiet:
                _record_killer(ply, (from_pos, to_pos))
                _history[_sq(from_pos) * _NSQ + _sq(to_pos)] += depth * depth
            break

    if best <= orig_alpha:
        flag = UPPERBOUND
    elif best >= beta:
        flag = LOWERBOUND
    else:
        flag = EXACT
    _tt.store(hash_key, depth, _tt_encode(best, ply), flag, best_move)
    return best


def _record_killer(ply: int, move):
    """Store a quiet cutoff move in the killer slots (no duplicates)."""
    killers = _killers[ply]
    if killers[0] == move:
        return
    killers[1] = killers[0]
    killers[0] = move


def _search_root(game_state: GameState, moves: list, depth: int,
                 alpha: int, beta: int, start_time: float,
                 time_limit: float) -> tuple:
    """Search all root moves at ``depth`` within [alpha, beta].

    Returns (best_move, best_score). Raises ``_TimeUp`` if the budget runs out
    mid-iteration (the caller discards the partial result).
    """
    depth_best = None
    depth_best_score = -INF
    for from_pos, to_pos in moves:
        game_state.make_move(from_pos, to_pos, skip_validation=True)
        try:
            score = -_negamax(game_state, depth - 1, -beta, -alpha, 1,
                              start_time, time_limit, ext_left=MAX_EXTENSIONS)
        finally:
            game_state.undo_move()
        if score > depth_best_score:
            depth_best_score = score
            depth_best = (from_pos, to_pos)
            if score > alpha:
                alpha = score
    return depth_best, depth_best_score


def find_best_move(game_state: GameState, player: Player | None = None,
                   time_limit_ms: int = DEFAULT_TIME_LIMIT_MS) -> tuple | None:
    """Find the best move using iterative-deepening negamax search.

    Returns ``(from_pos, to_pos)`` or ``None`` if the player has no legal moves
    (or the game is already over). ``player`` must equal the side to move
    (``game_state.current_player``); pass ``None`` to use the side to move.

    Only the result of a *fully completed* iteration is ever returned: if the
    time budget runs out partway through a deeper iteration, that partial
    result is discarded and the best move from the last completed depth is used.
    """
    global _node_count, _last_depth
    _node_count = 0
    _last_depth = 0
    _reset_search_state()

    if player is None:
        player = game_state.current_player
    elif player != game_state.current_player:
        raise ValueError(
            f"player ({player}) must equal the side to move "
            f"({game_state.current_player})")

    # A terminal position has no move to make.
    if game_state.is_over:
        return None

    moves = generate_legal_moves(game_state, player)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]

    start_time = time.time()
    time_limit = time_limit_ms / 1000.0

    best_move = moves[0]
    best_score = -INF
    completed_depth = 0

    for depth in range(1, MAX_ITER_DEPTH):
        # Full-window search each iteration. (Aspiration windows were tried but
        # removed: a narrow window combined with null-move pruning could return
        # an optimistic "exact" bound for a losing move — the classic fail-soft
        # over-pruning inside a tight window. The full window is verified correct
        # at every depth and only sacrifices a small root-level speedup.)
        alpha = -INF
        beta = INF

        ordered = order_moves(moves, game_state, best_move, _killers[0], _history)

        try:
            depth_best, depth_best_score = _search_root(
                game_state, ordered, depth, alpha, beta, start_time, time_limit)
            if depth_best is not None:
                best_move = depth_best
                best_score = depth_best_score
                completed_depth = depth
        except _TimeUp:
            # Partial iteration discarded; keep the last completed best_move.
            # The aborted work still filled the transposition table, which helps
            # the next move's search.
            break

        # Stop early on a forced win/loss found at this depth.
        if abs(best_score) > MATE_THRESHOLD:
            break

    _last_depth = completed_depth
    return best_move