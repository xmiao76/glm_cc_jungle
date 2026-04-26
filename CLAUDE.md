# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jungle (Dou Shou Qi) — a Windows desktop board game with GUI and built-in AI. Two players (human vs AI or AI vs AI) compete on a 7×9 board with terrain features (rivers, traps, dens) and 8 animal pieces each.

## Tech Stack

- **Language**: Python 3.12+
- **GUI**: Pygame 2.x
- **AI**: Minimax with alpha-beta pruning, null-move pruning, LMR, iterative deepening, two-bucket transposition tables
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
│   ├── rules.py     # Legal move generation, capture validation, win detection (check_win, check_win_with_reason)
│   ├── game.py      # GameState (make_move, undo_move, copy), turn management, win_reason
│   └── ai.py        # Alpha-beta + null-move pruning + LMR, evaluation (material + position + den defense + mobility + endgame), two-bucket TT, Zobrist hashing
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
- **Time checks**: AI uses node-count-based time checks (every 4096 nodes) instead of per-node `time.time()` calls.

## Disambiguated Rules

- Rat captures Elephant only from land (not from water)
- Elephant cannot capture Rat
- Rat in water can only be captured by another Rat also in water
- Piece in opponent's trap becomes rank 0; own trap has no effect
- Cannot enter own den
- Stalemate (no legal moves) = loss for that player