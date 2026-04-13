"""AI engine for Jungle (Dou Shou Qi) using minimax with alpha-beta pruning.

Features:
- Iterative deepening with time limit
- Alpha-beta pruning (fail-soft)
- Move ordering (captures first via MVV-LVA, den-entry moves)
- Transposition table with Zobrist hashing
- Evaluation: material + position + mobility + trap control
"""

from __future__ import annotations
import time
import random
from jungle_game.engine.pieces import PieceType, Player
from jungle_game.engine.rules import generate_legal_moves, check_win

# Piece material values (tuned for Jungle)
PIECE_VALUES = {
    PieceType.RAT: 300,
    PieceType.CAT: 200,
    PieceType.DOG: 350,
    PieceType.WOLF: 450,
    PieceType.LEOPARD: 600,
    PieceType.TIGER: 900,
    PieceType.LION: 1000,
    PieceType.ELEPHANT: 1100,
}

# Position bonus: Manhattan distance from opponent's den
# Closer = more valuable for advancing pieces
# Blue's target den is (3,8), Red's target den is (3,0)
DEN_POSITIONS = {
    Player.BLUE: (3, 8),
    Player.RED: (3, 0),
}

# Zobrist hashing for transposition table
_random = random.Random(42)  # Deterministic for reproducibility
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
    own_den = DEN_POSITIONS[opp]  # Opponent's den = our own den area

    for piece in game_state.pieces:
        value = PIECE_VALUES[piece.piece_type]

        if piece.player == player:
            # Material
            score += value

            # Position: bonus for being closer to opponent's den
            dist_to_den = abs(piece.col - target_den[0]) + abs(piece.row - target_den[1])
            score += (16 - dist_to_den) * 10  # Max bonus ~160

            # Penalty for being near own den (we want to advance, not defend)
            dist_from_own = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
            if dist_from_own < 3:
                score -= (3 - dist_from_own) * 15

            # Trap control: bonus if threatening opponent's trapped pieces
            # and penalty if our piece is in opponent's trap
            if board.is_opponent_trap(piece.col, piece.row, piece.player):
                score -= value // 2  # Our piece is weakened

        else:
            # Opponent's piece
            score -= value

            # Position: opponent closer to our den is threatening
            dist_to_our_den = abs(piece.col - own_den[0]) + abs(piece.row - own_den[1])
            score -= (16 - dist_to_our_den) * 8  # Threat factor

            # Opponent in our trap = good for us
            if board.is_opponent_trap(piece.col, piece.row, piece.player):
                score += value // 2

    # Mobility: count legal moves for both sides
    player_moves = len(generate_legal_moves(game_state, player))
    opp_moves = len(generate_legal_moves(game_state, opp))
    score += (player_moves - opp_moves) * 5

    return score


def order_moves(moves, game_state) -> list:
    """Order moves for better alpha-beta pruning.

    Priority:
    1. Captures (sorted by MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
    2. Den-entry moves
    3. Other moves
    """
    pieces_by_pos = game_state.pieces_by_pos
    scored_moves = []

    for from_pos, to_pos in moves:
        priority = 0
        target = pieces_by_pos.get(to_pos)

        if target is not None:
            # Capture: MVV-LVA score (high victim value, low attacker value = best)
            victim_value = PIECE_VALUES[target.piece_type]
            attacker = pieces_by_pos.get(from_pos)
            attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
            priority = 10000 + victim_value * 10 - attacker_value
        elif game_state.board.is_opponent_den(to_pos[0], to_pos[1],
                                               game_state.current_player):
            # Den-entry move
            priority = 5000

        scored_moves.append((priority, from_pos, to_pos))

    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return [(fp, tp) for _, fp, tp in scored_moves]


class TranspositionTable:
    """Simple fixed-size transposition table using Zobrist hashing."""

    def __init__(self, max_size=1_000_000):
        self._table = {}
        self._max_size = max_size

    def lookup(self, hash_key: int, depth: int):
        """Look up a position. Returns (score, flag, best_move) or None."""
        entry = self._table.get(hash_key)
        if entry is None:
            return None
        if entry['depth'] >= depth:
            return entry['score'], entry['flag'], entry['best_move']
        return None

    def store(self, hash_key: int, depth: int, score: int, flag: int, best_move):
        """Store a position in the table."""
        existing = self._table.get(hash_key)
        if existing is not None and existing['depth'] > depth:
            return  # Don't overwrite deeper entries
        self._table[hash_key] = {
            'depth': depth,
            'score': score,
            'flag': flag,
            'best_move': best_move,
        }
        # Evict oldest entries if table is too large
        if len(self._table) > self._max_size:
            # Simple eviction: clear half the table
            keys = list(self._table.keys())
            for k in keys[:len(keys) // 2]:
                del self._table[k]

    def clear(self):
        self._table.clear()


def _alpha_beta(game_state, depth: int, alpha: int, beta: int,
                maximizing: bool, player: Player, tt: TranspositionTable,
                start_time: float, time_limit: float) -> int:
    """Alpha-beta search with transposition table."""

    # Time check
    if time.time() - start_time > time_limit:
        return evaluate(game_state, player)

    hash_key = compute_zobrist_hash(game_state)

    # Transposition table lookup
    tt_entry = tt.lookup(hash_key, depth)
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
            return 100000 + depth  # Prefer faster wins
        return -100000 - depth  # Prefer slower losses

    if depth == 0:
        return evaluate(game_state, player)

    current = game_state.current_player
    moves = generate_legal_moves(game_state, current)
    if not moves:
        # Stalemate: current player loses
        if current == player:
            return -100000
        return 100000

    moves = order_moves(moves, game_state)

    # Try TT best move first
    if tt_entry is not None:
        _, _, best_move = tt_entry
        if best_move is not None and best_move in moves:
            moves.remove(best_move)
            moves.insert(0, best_move)

    best_move = moves[0]

    if maximizing:
        max_eval = -999999
        for from_pos, to_pos in moves:
            if time.time() - start_time > time_limit:
                break
            captured = game_state.make_move(from_pos, to_pos)
            eval_score = _alpha_beta(game_state, depth - 1, alpha, beta,
                                     False, player, tt, start_time, time_limit)
            game_state.undo_move()

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (from_pos, to_pos)

            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break

        tt.store(hash_key, depth, max_eval,
                 EXACT if max_eval > alpha and max_eval < beta
                 else (LOWERBOUND if max_eval >= beta else UPPERBOUND),
                 best_move)
        return max_eval
    else:
        min_eval = 999999
        for from_pos, to_pos in moves:
            if time.time() - start_time > time_limit:
                break
            captured = game_state.make_move(from_pos, to_pos)
            eval_score = _alpha_beta(game_state, depth - 1, alpha, beta,
                                     True, player, tt, start_time, time_limit)
            game_state.undo_move()

            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (from_pos, to_pos)

            beta = min(beta, eval_score)
            if beta <= alpha:
                break

        tt.store(hash_key, depth, min_eval,
                 EXACT if min_eval > alpha and min_eval < beta
                 else (LOWERBOUND if min_eval >= beta else UPPERBOUND),
                 best_move)
        return min_eval


def find_best_move(game_state, player: Player = None,
                   time_limit_ms: int = DEFAULT_TIME_LIMIT_MS) -> tuple | None:
    """Find the best move using iterative deepening alpha-beta search.

    Returns (from_pos, to_pos) or None if no moves available.
    """
    if player is None:
        player = game_state.current_player

    moves = generate_legal_moves(game_state, player)
    if not moves:
        return None

    if len(moves) == 1:
        return moves[0]

    tt = TranspositionTable()
    start_time = time.time()
    time_limit = time_limit_ms / 1000.0

    best_move = moves[0]
    maximizing = (player == Player.BLUE)

    # Iterative deepening
    for depth in range(1, 20):
        if time.time() - start_time > time_limit * 0.8:
            break

        current_best = None
        current_best_score = -999999 if maximizing else 999999

        ordered_moves = order_moves(moves, game_state)

        # Try TT best move first from previous iteration
        if best_move in ordered_moves:
            ordered_moves.remove(best_move)
            ordered_moves.insert(0, best_move)

        for from_pos, to_pos in ordered_moves:
            if time.time() - start_time > time_limit * 0.9:
                break

            captured = game_state.make_move(from_pos, to_pos)
            score = _alpha_beta(game_state, depth - 1, -999999, 999999,
                                not maximizing, player, tt, start_time,
                                time_limit - (time.time() - start_time))
            game_state.undo_move()

            if maximizing:
                if score > current_best_score:
                    current_best_score = score
                    current_best = (from_pos, to_pos)
            else:
                if score < current_best_score:
                    current_best_score = score
                    current_best = (from_pos, to_pos)

        if current_best is not None:
            best_move = current_best

    return best_move