"""Self-play win-rate match to quantify the Phase 2 enhancement.

Compares the "enhanced" engine (piece-square tables ON, den-threat extensions
ON) against the shipped "baseline" engine (PST OFF -> advancement formula,
extensions OFF) at equal time, alternating colours, with the transposition
table cleared before each move so the weaker side cannot free-ride on the
stronger side's deeper entries.

The shared infrastructure (incremental Zobrist, short-circuit check_win_fast)
is on for both sides, so this isolates the contribution of the PST + extensions.

Measurement result (6 games, 150ms/move, 150-move cap): enhanced 0 - baseline 5
- draw 1, i.e. the PST + extensions were NET-HARMFUL at this time control, which
is why they are OFF by default. Re-run to reproduce or try other time controls.

Usage:
    python scripts/elo_match.py [--games N] [--time-ms MS] [--seed S]

Exit code 0 if the enhanced side wins > 50% of decisive games; 1 otherwise.
"""
from __future__ import annotations
import argparse
import random
import sys

from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Player
from jungle_game.engine.ai import find_best_move, clear_tt, set_extensions_enabled
from jungle_game.engine.evaluation import (
    EvalConfig, set_eval_config, reset_eval_config, DEFAULT_CONFIG,
)

# Enhanced = PST on + extensions on (the experimental config). Baseline = the
# shipped default (formula, no extensions).
ENHANCED_CONFIG = EvalConfig(use_pst=True)
BASELINE_CONFIG = DEFAULT_CONFIG   # EvalConfig(use_pst=False)


def _set_engine(pst: bool, extensions: bool) -> None:
    set_eval_config(ENHANCED_CONFIG if pst else BASELINE_CONFIG)
    set_extensions_enabled(extensions)


def play_one(enhanced_is_blue: bool, time_ms: int, max_moves: int,
             seed: int) -> str:
    """Return 'enhanced', 'baseline', or 'draw' for one game."""
    random.seed(seed)
    g = GameState(first_player=Player.BLUE)
    for _ in range(max_moves):
        if g.is_over:
            break
        clear_tt()
        is_enh = (g.current_player == Player.BLUE) == enhanced_is_blue
        _set_engine(pst=is_enh, extensions=is_enh)
        move = find_best_move(g, g.current_player, time_limit_ms=time_ms)
        if move is None:
            break
        g.make_move(move[0], move[1])
    reset_eval_config()
    set_extensions_enabled(True)
    if g.is_over and g.winner is not None:
        enh_player = Player.BLUE if enhanced_is_blue else Player.RED
        return "enhanced" if g.winner == enh_player else "baseline"
    return "draw"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=12)
    ap.add_argument("--time-ms", type=int, default=120)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--max-moves", type=int, default=90)
    args = ap.parse_args()

    res = {"enhanced": 0, "baseline": 0, "draw": 0}
    for i in range(args.games):
        enh_blue = (i % 2 == 0)
        r = play_one(enh_blue, args.time_ms, args.max_moves, args.seed + i)
        res[r] += 1
        side = "enh=Blue" if enh_blue else "enh=Red"
        print(f"  game {i:2d} ({side}): {r}")

    decisive = res["enhanced"] + res["baseline"]
    rate = (res["enhanced"] / decisive * 100) if decisive else 0.0
    print(f"\nTotals: enhanced={res['enhanced']} baseline={res['baseline']} "
          f"draw={res['draw']}  (enhanced win-rate of decisive: {rate:.0f}%)")
    return 0 if (res["enhanced"] > res["baseline"]) else 1


if __name__ == "__main__":
    sys.exit(main())