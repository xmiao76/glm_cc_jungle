"""AI engine for Jungle (Dou Shou Qi) using minimax with alpha-beta pruning.

Features:
- Iterative deepening with time limit
- Alpha-beta pruning (fail-soft) with null-move pruning
- Late move reduction (LMR) for quiet moves
- Move ordering (captures first via MVV-LVA, den-entry moves, TT best move)
- Transposition table with Zobrist hashing (two-bucket replacement)
- Quiescence search to avoid horizon effect
- Evaluation: material + position + threats + trap control + den defense + mobility + endgame
- Node-count-based time checks for efficiency
"""

from __future__ import annotations
import time
import random
from jungle_game.engine.pieces import PieceType, Player
from jungle_game.engine.rules import generate_legal_moves, check_win, is_capture_valid

# Piece material values (tuned for Jungle)
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

# Position bonus: Manhattan distance from opponent's den
DEN_POSITIONS = {
    Player.BLUE: (3, 8),
    Player.RED: (3, 0),
}

# Piece advancement multipliers
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

# Zobrist hashing for transposition table
_random = random.Random(42)
ZOBRIST_PIECES = {}
ZOBRIST_SIDE = _random.getrandbits(64)

for player in Player:
    for ptype in PieceType:
        for row in range(9):
            for col in range(7):
                ZOBRIST_PIECES[(ptype, player, col, row)] = _random.getrandbits(64)

# Transposition table entry types
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

DEFAULT_TIME_LIMIT_MS = 1500

# Null-move pruning reduction
NULL_MOVE_R = 2
# Minimum pieces per side for null-move to be safe
NULL_MOVE_MIN_PIECES = 3

# LMR: reduce depth for moves after the first few
LMR_MIN_DEPTH = 3
LMR_MOVE_INDEX = 4  # Reduce moves at index >= this
LMR_REDUCTION = 1

# Time check interval (nodes between time checks)
TIME_CHECK_NODES = 4096

# Orthogonal directions
DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def compute_zobrist_hash(game_state) -> int:
    """Compute Zobrist hash for the current game state."""
    h = 0
    for piece in game_state.pieces:
        key = (piece.piece_type, piece.player, piece.col, piece.row)
        h ^= ZOBRIST_PIECES.get(key, 0)
    if game_state.current_player == Player.RED:
        h ^= ZOBRIST_SIDE
    return h


def evaluate(game_state, player: Player) -> int:
    """Evaluate the position from the given player's perspective.

    Positive = good for player, negative = bad.
    """
    winner = check_win(game_state)
    if winner == player:
        return 100000
    if winner is not None and winner != player:
        return -100000

    score = 0
    board = game_state.board
    opp = Player.RED if player == Player.BLUE else Player.BLUE
    target_den = DEN_POSITIONS[player]
    own_den = DEN_POSITIONS[opp]

    pieces_by_pos = game_state.pieces_by_pos
    own_pieces = []
    opp_pieces = []
    for piece in game_state.pieces:
        if piece.player == player:
            own_pieces.append(piece)
        else:
            opp_pieces.append(piece)

    total_pieces = len(own_pieces) + len(opp_pieces)
    is_endgame = total_pieces <= 6
    endgame_mult = 1.5 if is_endgame else 1.0

    # Den threat tracking
    opp_near_own_den = 0  # opponent pieces near our den
    own_near_own_den = []  # (piece, distance) near our den

    for piece in own_pieces:
        value = PIECE_VALUES[piece.piece_type]

        # Material
        score += value

        # Position: bonus for being closer to opponent's den
        dist_to_den = abs(piece.col - target_den[0]) + abs(piece.row - target_den[1])
        multiplier = ADVANCE_MULTIPLIER.get(piece.piece_type, 1.0)
        score += int((16 - dist_to_den) * 20 * multiplier * endgame_mult)

        # Penalty for being near own den
        dist_from_own = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
        if dist_from_own < 3:
            score -= (3 - dist_from_own) * 25
            own_near_own_den.append((piece, dist_from_own))

        # Penalty if our piece is in opponent's trap
        if board.is_opponent_trap(piece.col, piece.row, piece.player):
            score -= value // 2

        # Den threat tracking
        if dist_from_own <= 3:
            pass  # already tracked above

        # Threat bonus
        for dc, dr in DIRECTIONS:
            nc, nr = piece.col + dc, piece.row + dr
            target = pieces_by_pos.get((nc, nr))
            if target is not None and target.player == opp:
                if is_capture_valid(piece.piece_type, piece.player,
                                    piece.col, piece.row, target, board):
                    score += PIECE_VALUES[target.piece_type] // 4

    for piece in opp_pieces:
        value = PIECE_VALUES[piece.piece_type]

        # Material
        score -= value

        # Position: opponent closer to our den is threatening
        dist_to_our_den = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
        score -= int((16 - dist_to_our_den) * 15 * endgame_mult)

        # Opponent in our trap = good for us
        if board.is_opponent_trap(piece.col, piece.row, piece.player):
            score += value // 2

        # Track opponent den proximity
        if dist_to_our_den <= 3:
            opp_near_own_den += 1

        # Penalty if opponent threatens our pieces
        for dc, dr in DIRECTIONS:
            nc, nr = piece.col + dc, piece.row + dr
            target = pieces_by_pos.get((nc, nr))
            if target is not None and target.player == player:
                if is_capture_valid(piece.piece_type, piece.player,
                                    piece.col, piece.row, target, board):
                    score -= PIECE_VALUES[target.piece_type] // 5

    # Den defense bonus: reward defenders when opponent threatens our den
    if opp_near_own_den > 0:
        for piece, dist in own_near_own_den:
            score += (3 - dist) * 40

    # Mobility: cheap approximation (count open orthogonal neighbors)
    for piece in own_pieces:
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
            if blocker is not None and blocker.player == player:
                continue
            mobility += 1
        score += mobility * 5

    # Endgame knowledge
    if is_endgame:
        own_types = {p.piece_type for p in own_pieces}
        opp_types = {p.piece_type for p in opp_pieces}

        # Rat can threaten Elephant: bonus if opponent has Elephant and we have Rat
        if PieceType.RAT in own_types and PieceType.ELEPHANT in opp_types:
            score += 200

        # Dominant piece: Lion/Tiger with no Rat on opponent side
        if (PieceType.LION in own_types or PieceType.TIGER in own_types) and PieceType.RAT not in opp_types:
            score += 300

        # One move from den: check if any piece can enter den
        for piece in own_pieces:
            for dc, dr in DIRECTIONS:
                nc, nr = piece.col + dc, piece.row + dr
                if board.in_bounds(nc, nr) and board.is_opponent_den(nc, nr, piece.player):
                    blocker = pieces_by_pos.get((nc, nr))
                    if blocker is None:
                        score += 5000

    return score


def order_moves(moves, game_state) -> list:
    """Order moves for better alpha-beta pruning.

    Priority:
    1. Captures (sorted by MVV-LVA)
    2. Den-entry moves
    3. Other moves
    """
    pieces_by_pos = game_state.pieces_by_pos
    scored_moves = []

    for from_pos, to_pos in moves:
        priority = 0
        target = pieces_by_pos.get(to_pos)

        if target is not None:
            victim_value = PIECE_VALUES[target.piece_type]
            attacker = pieces_by_pos.get(from_pos)
            attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
            priority = 10000 + victim_value * 10 - attacker_value
        elif game_state.board.is_opponent_den(to_pos[0], to_pos[1],
                                               game_state.current_player):
            priority = 5000

        scored_moves.append((priority, from_pos, to_pos))

    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return [(fp, tp) for _, fp, tp in scored_moves]


class TranspositionTable:
    """Two-bucket transposition table using Zobrist hashing.

    Uses depth-preferred + always-replace buckets for better retention.
    """

    def __init__(self, depth_size=500_000, always_size=500_000):
        self._depth_table = {}
        self._always_table = {}
        self._depth_max = depth_size
        self._always_max = always_size

    def lookup(self, hash_key: int, depth: int):
        """Look up a position. Returns (score, flag, best_move) or None."""
        # Check depth-preferred table first
        entry = self._depth_table.get(hash_key)
        if entry is not None and entry['depth'] >= depth:
            return entry['score'], entry['flag'], entry['best_move']
        # Check always-replace table
        entry = self._always_table.get(hash_key)
        if entry is not None and entry['depth'] >= depth:
            return entry['score'], entry['flag'], entry['best_move']
        return None

    def store(self, hash_key: int, depth: int, score: int, flag: int, best_move):
        """Store a position in both tables."""
        # Always store in always-replace table
        if len(self._always_table) >= self._always_max:
            self._always_table.clear()
        self._always_table[hash_key] = {
            'depth': depth,
            'score': score,
            'flag': flag,
            'best_move': best_move,
        }

        # Store in depth-preferred table only if deeper or equal
        existing = self._depth_table.get(hash_key)
        if existing is not None and existing['depth'] > depth:
            return
        if len(self._depth_table) >= self._depth_max:
            self._depth_table.clear()
        self._depth_table[hash_key] = {
            'depth': depth,
            'score': score,
            'flag': flag,
            'best_move': best_move,
        }

    def clear(self):
        self._depth_table.clear()
        self._always_table.clear()


# Persistent transposition table
_tt = TranspositionTable()

# Node counter for time checks
_node_count = 0


def clear_tt():
    """Clear the persistent transposition table (call between games)."""
    _tt.clear()


def _quiescence(game_state, alpha: int, beta: int, maximizing: bool,
                player: Player, start_time: float, time_limit: float,
                q_depth: int = 0, max_q_depth: int = 3) -> int:
    """Quiescence search: extend search on captures to avoid horizon effect."""
    global _node_count
    _node_count += 1

    # Time check (every N nodes)
    if _node_count % TIME_CHECK_NODES == 0:
        if time.time() - start_time > time_limit:
            return evaluate(game_state, player)

    stand_pat = evaluate(game_state, player)

    if game_state.is_over:
        return stand_pat

    if maximizing:
        if stand_pat >= beta:
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat
    else:
        if stand_pat <= alpha:
            return stand_pat
        if stand_pat < beta:
            beta = stand_pat

    if q_depth >= max_q_depth:
        return stand_pat

    current = game_state.current_player
    moves = generate_legal_moves(game_state, current)

    capture_moves = []
    pieces_by_pos = game_state.pieces_by_pos
    for from_pos, to_pos in moves:
        target = pieces_by_pos.get(to_pos)
        if target is not None:
            capture_moves.append((from_pos, to_pos))
        elif game_state.board.is_opponent_den(to_pos[0], to_pos[1], current):
            capture_moves.append((from_pos, to_pos))

    if not capture_moves:
        return stand_pat

    capture_moves = order_moves(capture_moves, game_state)

    if maximizing:
        max_eval = stand_pat
        for from_pos, to_pos in capture_moves:
            if _node_count % TIME_CHECK_NODES == 0 and time.time() - start_time > time_limit:
                break
            game_state.make_move(from_pos, to_pos, skip_validation=True)
            eval_score = _quiescence(game_state, alpha, beta, False, player,
                                     start_time, time_limit, q_depth + 1,
                                     max_q_depth)
            game_state.undo_move()
            if eval_score > max_eval:
                max_eval = eval_score
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = stand_pat
        for from_pos, to_pos in capture_moves:
            if _node_count % TIME_CHECK_NODES == 0 and time.time() - start_time > time_limit:
                break
            game_state.make_move(from_pos, to_pos, skip_validation=True)
            eval_score = _quiescence(game_state, alpha, beta, True, player,
                                     start_time, time_limit, q_depth + 1,
                                     max_q_depth)
            game_state.undo_move()
            if eval_score < min_eval:
                min_eval = eval_score
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval


def _count_pieces(game_state, player: Player) -> int:
    """Count pieces for a player."""
    count = 0
    for p in game_state.pieces:
        if p.player == player:
            count += 1
    return count


def _alpha_beta(game_state, depth: int, alpha: int, beta: int,
                maximizing: bool, player: Player,
                start_time: float, time_limit: float) -> int:
    """Alpha-beta search with null-move pruning, LMR, and transposition table."""
    global _node_count
    _node_count += 1

    # Time check (every N nodes)
    if _node_count % TIME_CHECK_NODES == 0:
        if time.time() - start_time > time_limit:
            return evaluate(game_state, player)

    hash_key = compute_zobrist_hash(game_state)

    # Transposition table lookup
    tt_entry = _tt.lookup(hash_key, depth)
    if tt_entry is not None:
        score, flag, _ = tt_entry
        if flag == EXACT:
            return score
        elif flag == LOWERBOUND and score > alpha:
            alpha = score
        elif flag == UPPERBOUND and score < beta:
            beta = score
        if alpha >= beta:
            return score

    # Terminal check
    winner = check_win(game_state)
    if winner is not None:
        if winner == player:
            return 100000 + depth
        return -100000 - depth

    if depth == 0:
        return _quiescence(game_state, alpha, beta, maximizing, player,
                           start_time, time_limit)

    current = game_state.current_player
    moves = generate_legal_moves(game_state, current)
    if not moves:
        if current == player:
            return -100000
        return 100000

    moves = order_moves(moves, game_state)

    # Try TT best move first
    if tt_entry is not None:
        _, _, best_move_tt = tt_entry
        if best_move_tt is not None and best_move_tt in moves:
            moves.remove(best_move_tt)
            moves.insert(0, best_move_tt)

    # Null-move pruning (maximizing side only, not in endgame)
    own_count = _count_pieces(game_state, player)
    opp_count = _count_pieces(game_state, Player.RED if player == Player.BLUE else Player.BLUE)
    if (maximizing and depth >= 3
            and own_count >= NULL_MOVE_MIN_PIECES
            and opp_count >= NULL_MOVE_MIN_PIECES):
        # Skip the current player's turn
        game_state.current_player = Player.RED if game_state.current_player == Player.BLUE else Player.BLUE
        null_score = _alpha_beta(game_state, depth - 1 - NULL_MOVE_R,
                                 alpha, beta, False, player,
                                 start_time, time_limit)
        game_state.current_player = Player.RED if game_state.current_player == Player.BLUE else Player.BLUE
        if null_score >= beta:
            return beta

    best_move = moves[0]
    pieces_by_pos = game_state.pieces_by_pos

    if maximizing:
        orig_alpha = alpha
        max_eval = -999999
        for move_idx, (from_pos, to_pos) in enumerate(moves):
            if _node_count % TIME_CHECK_NODES == 0 and time.time() - start_time > time_limit:
                break

            # Late move reduction for quiet moves
            target = pieces_by_pos.get(to_pos)
            is_capture = target is not None
            is_den_entry = game_state.board.is_opponent_den(to_pos[0], to_pos[1], current)
            do_reduce = (move_idx >= LMR_MOVE_INDEX and depth >= LMR_MIN_DEPTH
                         and not is_capture and not is_den_entry)

            game_state.make_move(from_pos, to_pos, skip_validation=True)

            if do_reduce:
                # Search with reduced depth
                eval_score = _alpha_beta(game_state, depth - 1 - LMR_REDUCTION,
                                         alpha, beta, False, player,
                                         start_time, time_limit)
                # Re-search at full depth if it raises alpha
                if eval_score > alpha:
                    eval_score = _alpha_beta(game_state, depth - 1,
                                             alpha, beta, False, player,
                                             start_time, time_limit)
            else:
                eval_score = _alpha_beta(game_state, depth - 1, alpha, beta,
                                         False, player, start_time, time_limit)

            game_state.undo_move()

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (from_pos, to_pos)

            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break

        if max_eval <= orig_alpha:
            flag = UPPERBOUND
        elif max_eval >= beta:
            flag = LOWERBOUND
        else:
            flag = EXACT
        _tt.store(hash_key, depth, max_eval, flag, best_move)
        return max_eval
    else:
        orig_beta = beta
        min_eval = 999999
        for move_idx, (from_pos, to_pos) in enumerate(moves):
            if _node_count % TIME_CHECK_NODES == 0 and time.time() - start_time > time_limit:
                break

            target = pieces_by_pos.get(to_pos)
            is_capture = target is not None
            is_den_entry = game_state.board.is_opponent_den(to_pos[0], to_pos[1], current)
            do_reduce = (move_idx >= LMR_MOVE_INDEX and depth >= LMR_MIN_DEPTH
                         and not is_capture and not is_den_entry)

            game_state.make_move(from_pos, to_pos, skip_validation=True)

            if do_reduce:
                eval_score = _alpha_beta(game_state, depth - 1 - LMR_REDUCTION,
                                         alpha, beta, True, player,
                                         start_time, time_limit)
                if eval_score < beta:
                    eval_score = _alpha_beta(game_state, depth - 1,
                                             alpha, beta, True, player,
                                             start_time, time_limit)
            else:
                eval_score = _alpha_beta(game_state, depth - 1, alpha, beta,
                                         True, player, start_time, time_limit)

            game_state.undo_move()

            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (from_pos, to_pos)

            beta = min(beta, eval_score)
            if beta <= alpha:
                break

        if min_eval >= orig_beta:
            flag = LOWERBOUND
        elif min_eval <= alpha:
            flag = UPPERBOUND
        else:
            flag = EXACT
        _tt.store(hash_key, depth, min_eval, flag, best_move)
        return min_eval


def find_best_move(game_state, player: Player = None,
                   time_limit_ms: int = DEFAULT_TIME_LIMIT_MS) -> tuple | None:
    """Find the best move using iterative deepening alpha-beta search.

    Returns (from_pos, to_pos) or None if no moves available.
    """
    global _node_count
    _node_count = 0

    if player is None:
        player = game_state.current_player

    moves = generate_legal_moves(game_state, player)
    if not moves:
        return None

    if len(moves) == 1:
        return moves[0]

    start_time = time.time()
    time_limit = time_limit_ms / 1000.0

    best_move = moves[0]

    # Iterative deepening
    for depth in range(1, 20):
        if time.time() - start_time > time_limit * 0.8:
            break

        current_best = None
        current_best_score = -999999

        ordered_moves = order_moves(moves, game_state)

        # Try TT best move first from previous iteration
        if best_move in ordered_moves:
            ordered_moves.remove(best_move)
            ordered_moves.insert(0, best_move)

        for from_pos, to_pos in ordered_moves:
            if _node_count % TIME_CHECK_NODES == 0 and time.time() - start_time > time_limit * 0.9:
                break

            game_state.make_move(from_pos, to_pos, skip_validation=True)
            score = _alpha_beta(game_state, depth - 1, -999999, 999999,
                                False, player, start_time,
                                time_limit - (time.time() - start_time))
            game_state.undo_move()

            if score > current_best_score:
                current_best_score = score
                current_best = (from_pos, to_pos)

        if current_best is not None:
            best_move = current_best

    return best_move