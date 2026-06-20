# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jungle (Dou Shou Qi) — a Windows desktop board game with GUI and built-in AI. Two players (human vs AI or AI vs AI) compete on a 7×9 board with terrain features (rivers, traps, dens) and 8 animal pieces each.

## Tech Stack

- **Language**: Python 3.12+
- **GUI**: Pygame 2.x
- **AI**: Negamax with alpha-beta / Principal Variation Search, null-move pruning, late move reductions, killer moves + history heuristic, iterative deepening, two-bucket transposition table with incremental Zobrist hashing and ply-aware mate scoring, exception-based clean time abort. Piece-square tables and den-threat extensions are implemented but **off by default** (self-play measured them net-harmful; selectable via `EvalConfig(use_pst=True)` / `set_extensions_enabled(True)`).
- **Testing**: pytest
- **Packaging**: PyInstaller (--onedir)

## Build / Run / Test

```bash
python -m venv venv
source venv/Scripts/activate      # Windows
pip install -r requirements.txt

# Run the game
python main.py

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_rules.py -v

# Build packaged exe
pyinstaller build.spec --distpath release --workpath build --clean -y
```

## Architecture

```
jungle_game/
├── engine/          # Pure game logic (no GUI dependencies)
│   ├── board.py     # Board terrain map (7×9), coordinate queries, starting positions
│   ├── pieces.py    # PieceType enum, Piece dataclass, Player enum
│   ├── rules.py     # Legal move generation, capture validation, win detection (check_win, check_win_with_reason, check_win_fast, has_any_legal_move)
│   ├── zobrist.py   # Shared Zobrist keys + helpers (used by GameState incremental hash and ai compute_zobrist_hash)
│   ├── game.py      # GameState (make_move, undo_move, copy), turn management, win_reason, incremental _zobrist hash maintained on make/undo
│   ├── evaluation.py  # Symmetric evaluation (material + piece-square tables + den defense + traps + threats + mobility + endgame); MATE; EvalConfig for tunable weights; required by negamax: evaluate(g, A) == -evaluate(g, B)
│   └── ai.py        # Negamax + PVS + null-move + LMR + den-threat extensions + killers + history; two-bucket TT (incremental Zobrist, ply-aware mate scoring); iterative deepening with exception-based clean time abort (only completed iterations committed); re-exports evaluate/PIECE_VALUES
├── gui/             # Pygame rendering and input
│   ├── app.py       # Game loop, event dispatch, mode management (HUMAN_VS_AI, AI_VS_AI)
│   ├── board_renderer.py  # Terrain (water, trap, den, land), grid, highlights
│   ├── piece_renderer.py  # Animal piece tokens (pre-rendered surfaces)
│   ├── ui_overlay.py      # Turn indicator, captured pieces, buttons, game-over
├── main.py          # Entry point
tests/               # pytest tests for engine, rules, AI
release/             # Packaged output (jungle_game.exe + README.txt)
```

## Key Design Decisions

- **Engine/GUI separation**: `engine/` has zero GUI imports. Game logic is testable without Pygame.
- **AI threading**: AI runs in a daemon thread; `ai_result` is polled in the main game loop.
- **Capture validation**: `is_capture_valid()` takes the attacker's *original* position (not target) to correctly handle terrain context (rat in water vs land).
- **Board coordinates**: (col, row) where col 0–6, row 0–8. Row 0 = Blue's home (top), row 8 = Red's home (bottom).
- **River jumps**: Lion jumps vertically and horizontally; Tiger only vertically. Both blocked by any Rat in intervening water.
- **Board flip**: Pressing `F` toggles visual flip of the board (row/col mirrored). This is display-only — it does not affect game state, turn order, or AI logic.
- **Human player**: Determined by `first_player` setting. When `first_player == Player.RED`, human plays Red and AI plays Blue. The `human_player` property resolves this.
- **Capture indicators**: Legal moves show green dots; capture moves show red rings.
- **Trapped pieces**: Pieces in the opponent's trap show a red ring overlay.
- **Win reason**: `check_win_with_reason()` returns `(winner, reason)` where reason is "den_entry", "elimination", or "stalemate". Stored in `GameState._win_reason`, displayed in game-over overlay.
- **Time checks**: AI uses node-count-based time checks (every 2048 nodes) instead of per-node `time.time()` calls.
- **AI search**: Negamax (side-relative scores) with Principal Variation Search. The evaluation in `evaluation.py` is symmetric — `evaluate(g, A) == -evaluate(g, B)` — which is what makes negamax valid (guarded by `tests/test_ai_strength.py::TestEvaluationSymmetry`). Aspiration windows were tried and removed: a narrow window combined with null-move pruning could return an optimistic "exact" bound for a losing move (fail-soft over-pruning), so the root searches with the full window each iteration (verified correct at every depth; small root-level speed cost).
- **AI time abort**: When the time budget runs out, the search raises a `_TimeUp` exception (instead of returning a meaningless stand-pat score). `find_best_move` only commits the best move from a *fully completed* iterative-deepening iteration; a time-aborted partial iteration is discarded. Every `make_move` is paired with `undo_move` inside `try/finally` (including the null-move `current_player` swap) so the game state is never left mutated when an abort propagates. This fixed a critical bug where a deep interrupted iteration previously committed a garbage move.
- **Incremental Zobrist**: `GameState` maintains `_zobrist` incrementally in `make_move`/`undo_move` (keys in `zobrist.py`); the search reads `game_state.zobrist_hash` in O(1) instead of recomputing over all pieces. `tests/test_zobrist.py` verifies incremental == recompute after every make/undo (including captures and river jumps).
- **Fast win check**: `make_move(skip_validation=True)` (the search path) uses `check_win_fast` (den-entry + elimination in one pass + short-circuit stalemate via `has_any_legal_move`); the GUI path keeps the full `check_win_with_reason` for stable `win_reason` text. This removed ~27% of per-node search time (the stalemate move-generation that ran on every move).
- **Den-threat extensions**: when a move puts a piece next to the opponent's empty den (a forced-win threat the opponent must answer, like a check), the search extends depth by 1 for that line, capped at `MAX_EXTENSIONS=2` per path to avoid explosion. **Off by default** — self-play (`scripts/elo_match.py`) measured them net-harmful at the tested time control (the engine over-commits to refutable den attacks, losing 0-5 vs the no-extension baseline). Selectable via `set_extensions_enabled(True)`.
- **Piece-square tables & tunable eval**: `evaluation.py` builds mirror-symmetric per-piece PSTs (den-advancement + central control + Rat-near-water + Lion/Tiger jump-lane bonuses) read via a vertical-mirror lookup so symmetry holds by construction. **Off by default** (`EvalConfig.use_pst=False`) — self-play measured the PST extras net-harmful vs the plain advancement formula (the central/jump-lane bonuses misvalue positions). The shipped engine uses the inlined advancement formula; PSTs are opt-in via `EvalConfig(use_pst=True)`. All weights live in `EvalConfig` (swap via `set_eval_config`; rebuilds the PSTs). `scripts/tune_eval.py` and `scripts/elo_match.py` are self-play harnesses for tuning and A/B measurement.
- **Shipped engine strength**: formula eval + no extensions + incremental Zobrist + `check_win_fast`. This searches ~11% more nodes than the Phase 1 baseline at 1500ms (depth 7 at 3000ms vs 6) and is verified sound (deeper search beats shallower 7-0 at a 5× time gap; beats a random mover; finds forced den wins and avoids trap blunders).

## Disambiguated Rules

- Rat captures Elephant only from land (not from water)
- Elephant cannot capture Rat
- Rat in water can only be captured by another Rat also in water
- Piece in opponent's trap becomes rank 0; own trap has no effect. A piece's effective rank for a capture is determined by its **current (pre-move) position**: an attacker currently in the opponent's trap is rank 0; entering the opponent's trap to capture does NOT reduce the attacker's rank for that capture, so a higher-rank piece can capture a lower-rank piece sitting in the defender's own trap. (Wikipedia is ambiguous on the attacker-entering-trap case; this is the chosen standard interpretation, consistent with `is_capture_valid` using the attacker's original position.)
- Cannot enter own den
- Stalemate (no legal moves) = loss for that player