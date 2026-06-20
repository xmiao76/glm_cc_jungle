"""Lightweight self-play tuning harness for the evaluation weights.

Does a small coordinate search over a few weight scale factors, playing each
candidate against the shipped DEFAULT_CONFIG and reporting the win rate. The
search space and game count are intentionally tiny — eval tuning is noisy and
slow, so this is an advisory tool, not an optimizer. A candidate is only worth
adopting if it wins >= 55% over a large (>= 30) game sample; this script can be
run with --games 30 --rounds more for a serious pass.

Usage:
    python scripts/tune_eval.py [--games N] [--time-ms MS] [--seed S]

Prints each candidate's win rate vs the default and the best candidate found.
Does NOT modify the codebase — adopt a winner manually by editing DEFAULT_CONFIG
in jungle_game/engine/evaluation.py.
"""
from __future__ import annotations
import argparse
import random
import sys
from dataclasses import replace

from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Player
from jungle_game.engine.ai import find_best_move, clear_tt, set_extensions_enabled
from jungle_game.engine.evaluation import (
    EvalConfig, set_eval_config, reset_eval_config, DEFAULT_CONFIG,
)


def _play(cand_is_blue: bool, candidate: EvalConfig, time_ms: int,
          max_moves: int, seed: int) -> str:
    random.seed(seed)
    g = GameState(first_player=Player.BLUE)
    for _ in range(max_moves):
        if g.is_over:
            break
        clear_tt()
        set_eval_config(candidate if (g.current_player == Player.BLUE) == cand_is_blue
                        else DEFAULT_CONFIG)
        set_extensions_enabled(True)
        move = find_best_move(g, g.current_player, time_limit_ms=time_ms)
        if move is None:
            break
        g.make_move(move[0], move[1])
    reset_eval_config()
    if g.is_over and g.winner is not None:
        cand_player = Player.BLUE if cand_is_blue else Player.RED
        return "cand" if g.winner == cand_player else "default"
    return "draw"


def _match(candidate: EvalConfig, games: int, time_ms: int, seed: int) -> float:
    res = {"cand": 0, "default": 0, "draw": 0}
    for i in range(games):
        cand_blue = (i % 2 == 0)
        r = _play(cand_blue, candidate, time_ms, 90, seed + i)
        res[r] += 1
    decisive = res["cand"] + res["default"]
    rate = (res["cand"] / decisive * 100) if decisive else 0.0
    print(f"  cand={candidate} -> cand={res['cand']} default={res['default']} "
          f"draw={res['draw']} (win-rate {rate:.0f}%)")
    return rate


# A small, hand-picked set of scale variations to explore. Real tuning would
# sweep more values; kept tiny here so the script finishes in reasonable time.
CANDIDATES = {
    "default (reference)": DEFAULT_CONFIG,
    "mobility x1.5": replace(DEFAULT_CONFIG, mobility_weight=6),
    "center x2": replace(DEFAULT_CONFIG, center_weight=12),
    "rat-water x2": replace(DEFAULT_CONFIG, rat_water_bonus=60),
    "near-den x1.5": replace(DEFAULT_CONFIG, near_den_bonus=180),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--time-ms", type=int, default=100)
    ap.add_argument("--seed", type=int, default=777)
    args = ap.parse_args()

    print(f"Tuning: {len(CANDIDATES)} candidates x {args.games} games "
          f"@ {args.time_ms}ms/move vs DEFAULT_CONFIG\n")
    results = []
    for name, cfg in CANDIDATES.items():
        print(f"[{name}]")
        rate = _match(cfg, args.games, args.time_ms, args.seed)
        results.append((name, rate, cfg))

    results.sort(key=lambda x: x[1], reverse=True)
    best_name, best_rate, best_cfg = results[0]
    print(f"\nBest: {best_name} ({best_rate:.0f}% win-rate vs default)")
    if best_rate >= 55 and best_name != "default (reference)":
        print("Candidate meets the >=55% bar — consider adopting it in "
              "evaluation.py's DEFAULT_CONFIG (run with --games 30 to confirm).")
    else:
        print("No candidate beat the default by >=55% — keep DEFAULT_CONFIG.")
    return 0


if __name__ == "__main__":
    sys.exit(main())