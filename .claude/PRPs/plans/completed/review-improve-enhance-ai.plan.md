# Plan: Review, Improve, and Enhance Jungle Game

## Summary
Comprehensive review and improvement of the Jungle (Dou Shou Qi) game to meet all prompt.md requirements, fix identified bugs, polish the GUI, strengthen the AI engine significantly, improve test quality, and clean up the release package.

## User Story
As a player, I want a polished, bug-free Jungle game with a strong AI opponent, clear visual terrain distinction, and a clean packaged release, so that I can enjoy a complete and challenging gaming experience.

## Problem → Solution
**Current state**: Fully playable but with several bugs (TT flag error, hover alpha, click guard hardcoding), weak visual differentiation (identical den colors, bare trap tiles, no capture indicators), intermediate-strength AI (no null-move pruning, non-incremental hashing, no den-defense eval, no mobility), test quality gaps (duplicated helpers, misleading tests, 91% rules coverage), and release artifacts (pytest cache leaked, no icon).
**Desired state**: Bug-free, visually polished game with distinct terrain, strong AI with 2+ additional search depth, comprehensive tests, and a clean release package.

## Metadata
- **Complexity**: Large
- **Source PRD**: prompt.md
- **PRD Phase**: N/A (full review)
- **Estimated Files**: 15+

---

## UX Design

### Before
```
┌──────────────────────────────────┐
│  Board: identical gold dens      │
│  Traps: gray X, no owner color   │
│  Legal moves: all green dots      │
│  Hover: opaque white border      │
│  Trapped pieces: no indicator     │
│  Game over: no reason shown       │
│  Water: simple color toggle       │
│  Border: flat brown rectangle     │
└──────────────────────────────────┘
```

### After
```
┌──────────────────────────────────┐
│  Board: blue-tinted/ red-tinted  │
│         dens with "B"/"R" label  │
│  Traps: player-tinted with icon  │
│  Legal moves: green=move,        │
│               red ring=capture   │
│  Hover: semi-transparent border │
│  Trapped pieces: chain/outline   │
│  Game over: shows win reason     │
│  Water: multi-wave animation    │
│  Border: beveled wood texture    │
└──────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Click during AI turn | Silently ignored | No change (correct) | Could add cursor feedback |
| Human plays Red | Blocked from clicking own turn | Correctly allowed | Bug fix |
| Capture move | Same green dot as non-capture | Red ring indicator | Visual improvement |
| Piece in opponent trap | Looks identical | Visual trapped indicator | UX improvement |
| Game over | Winner name only | Winner + reason | UX improvement |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 (critical) | `jungle_game/engine/ai.py` | all | AI engine to enhance |
| P0 (critical) | `jungle_game/gui/app.py` | all | Bug fixes and game loop |
| P0 (critical) | `jungle_game/gui/board_renderer.py` | all | Visual improvements |
| P1 (important) | `jungle_game/engine/game.py` | all | Incremental Zobrist support |
| P1 (important) | `jungle_game/gui/piece_renderer.py` | all | Trapped piece indicator |
| P1 (important) | `jungle_game/gui/ui_overlay.py` | all | Win reason display |
| P2 (reference) | `jungle_game/engine/rules.py` | all | Win reason data |
| P2 (reference) | `tests/test_ai.py` | all | Test patterns |
| P2 (reference) | `build.spec` | all | Packaging config |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Null-move pruning | Chess Programming Wiki | R=2 or R=3 reduction, verify no null-move in zugzwang positions |
| Incremental Zobrist | Chess Programming Wiki | XOR out old position, XOR in new position on make/undo |
| Pygame alpha drawing | Pygame docs | Use SRCALPHA temp surface + blit for per-pixel alpha |

---

## Patterns to Mirror

### NAMING_CONVENTION
// SOURCE: jungle_game/engine/pieces.py:1-86
- Enums use UPPER_SNAKE_CASE: `PieceType.RAT`, `Player.BLUE`
- Dataclasses use camelCase fields: `col`, `row`, `piece_type`, `player`
- Constants use UPPER_SNAKE_CASE: `PIECE_VALUES`, `WATER_SQUARES`

### ERROR_HANDLING
// SOURCE: jungle_game/engine/game.py:70-80
- `make_move()` raises `ValueError` for illegal moves when `skip_validation=False`
- Engine uses explicit exceptions, not silent failures

### ENGINE_GUI_SEPARATION
// SOURCE: architecture
- `engine/` has zero GUI imports. All engine code is testable without pygame.
- GUI imports from engine, never the reverse.

### TEST_STRUCTURE
// SOURCE: tests/test_rules.py:1-10
- Tests organized by class grouping related scenarios
- Helper functions at module top for game construction
- Descriptive test names in `test_<scenario>` format

### RENDERING_PATTERN
// SOURCE: jungle_game/gui/board_renderer.py:43-51
- Pre-render static surfaces in `__init__`, cache them
- Use SRCALPHA temp surfaces for semi-transparent overlays
- Draw order: terrain → highlights → pieces → UI overlay

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `jungle_game/engine/ai.py` | UPDATE | Fix TT flag bug, add null-move pruning, incremental Zobrist, den-defense eval, mobility eval, endgame knowledge, improve TT replacement, optimize time checks, rebalance piece values |
| `jungle_game/engine/game.py` | UPDATE | Add incremental Zobrist hash update in make_move/undo_move |
| `jungle_game/engine/pieces.py` | UPDATE | Add Zobrist key constants for incremental hashing |
| `jungle_game/engine/rules.py` | UPDATE | Return win reason from check_win, cover missing lines |
| `jungle_game/gui/app.py` | UPDATE | Fix click guard bug, fix hover alpha bug, add win reason to game-over, improve thread safety |
| `jungle_game/gui/board_renderer.py` | UPDATE | Differentiate dens, differentiate traps, add capture move indicators, improve water animation, improve border |
| `jungle_game/gui/piece_renderer.py` | UPDATE | Add trapped piece visual indicator, fix name truncation |
| `jungle_game/gui/ui_overlay.py` | UPDATE | Display win reason in game-over overlay |
| `tests/conftest.py` | CREATE | Shared test helpers (extract make_game_with_pieces) |
| `tests/test_ai.py` | UPDATE | Remove duplicated helper, add new AI enhancement tests |
| `tests/test_rules.py` | UPDATE | Remove duplicated helper, add missing coverage for river jump edge cases, fix stalemate dead code |
| `tests/test_game.py` | UPDATE | Fix test_multiple_undo, add undo-of-winning-move test |
| `build.spec` | UPDATE | Add icon, add version info |
| `release/README.txt` | UPDATE | Add board flip control, version info, troubleshooting |
| `requirements.txt` | UPDATE | Add pytest-cov |

## NOT Building

- Save/load game feature
- Undo button in GUI
- Difficulty settings UI
- Sound effects
- Network/multiplayer
- Draw by repetition detection
- Custom icon design (use a simple generated icon)

---

## Step-by-Step Tasks

### Task 1: Fix TT Flag Bug in Minimizing Branch
- **ACTION**: Fix the transposition table flag determination for the minimizing player branch in `_alpha_beta`
- **IMPLEMENT**: Save `orig_beta` at the start of the minimizing branch (like `orig_alpha` is saved for maximizing). Use `orig_beta` for the UPPERBOUND comparison: `if min_eval <= orig_alpha: flag = UPPERBOUND` should become `if min_eval >= orig_beta: flag = UPPERBOUND`. The minimizing player's "upper bound" means the score was so high that the maximizer would never allow this path -- so if `min_eval >= orig_beta`, the real value is at least `orig_beta`, which is a lower bound from the minimizer's perspective but an upper bound from the root's perspective. Follow negamax-style flag logic: save original alpha, after search compare final value against original alpha and beta to determine EXACT/UPPERBOUND/LOWERBOUND.
- **MIRROR**: ENGINE_GUI_SEPARATION, ERROR_HANDLING
- **IMPORTS**: No new imports
- **GOTCHA**: The current code mixes maximizer/minimizer flags with negamax-style orig_alpha. The cleanest fix is to use negamax throughout (both sides maximize their own eval), which eliminates the maximizing boolean entirely. However, that's a larger refactor. The minimal fix: in the minimizing branch, save `orig_beta = beta` before the loop, then use `if min_eval <= orig_alpha: flag = UPPERBOUND; elif min_eval >= orig_beta: flag = LOWERBOUND` — wait, this is still wrong. The correct approach: For the minimizer, `orig_alpha` is the bound from the maximizer's perspective. If `min_eval <= orig_alpha`, the minimizer's value is at most `orig_alpha` — this is an upper bound from the maximizer's frame. If `min_eval >= beta`, the minimizer's value is at least `beta` — this is a lower bound from the maximizer's frame. Actually the current code at line 426-431 has: `if min_eval <= orig_alpha: flag = UPPERBOUND` and `elif min_eval >= beta: flag = LOWERBOUND`. The issue is that `orig_alpha` is set to `alpha` at the START of the minimizing branch (line 407), but alpha has already been narrowed by the maximizing parent. The correct value to compare against is the alpha that was passed INTO this node, which IS `orig_alpha`. So actually the code may be correct. Let me re-examine: in the maximizing branch (lines 355-405), `orig_alpha = alpha` is saved, then alpha is narrowed. At the end, `if best_value <= orig_alpha: flag = UPPERBOUND; elif best_value >= beta: flag = LOWERBOUND; else: flag = EXACT`. For the minimizing branch (lines 407-431), the same pattern should apply but with roles swapped: `orig_beta = beta` should be saved, beta narrowed, then `if min_eval >= orig_beta: flag = LOWERBOUND; elif min_eval <= alpha: flag = UPPERBOUND; else: flag = EXACT`. The current code uses `orig_alpha` (which is the alpha passed in, not beta) for the UPPERBOUND comparison. This means it's comparing the minimizer's value against the maximizer's alpha bound, which is incorrect. **Fix**: Save `orig_beta = beta` before the minimizing loop. Change flag logic to: `if min_eval >= orig_beta: flag = LOWERBOUND; elif min_eval <= alpha: flag = UPPERBOUND; else: flag = EXACT`.
- **VALIDATE**: Run `pytest tests/test_ai.py -v`. Add a test that verifies TT correctness for a minimizer position: store a position, retrieve it, verify the flag and score are correct.

### Task 2: Fix Click Guard Bug for Human Playing Red
- **ACTION**: Fix `app.py` line 221-222 to not hardcode human as Blue
- **IMPLEMENT**: Replace `if self.game.current_player == Player.RED:` with a check that uses `self.first_player`. When `first_player == Player.BLUE`, human is Blue (clicks blocked during Red's turn). When `first_player == Player.RED`, human is Red (clicks blocked during Blue's turn). Add a property or method `human_player` that returns `Player.RED if self.first_player == Player.RED else Player.BLUE`. Then guard becomes: `if self.game.current_player != self.human_player:`
- **MIRROR**: NAMING_CONVENTION
- **IMPORTS**: No new imports (Player already imported)
- **GOTCHA**: The AI start logic also hardcodes Blue as human. Check `_start_ai_turn` and related methods. In HUMAN_VS_AI mode, the AI should play the *opposite* of `human_player`.
- **VALIDATE**: Toggle to "AI First" mode, verify Red player (human) can click and move during their turn.

### Task 3: Fix Hover Alpha Rendering Bug
- **ACTION**: Fix `app.py` line 368 where `pygame.draw.rect` ignores the alpha channel on non-SRCALPHA surfaces
- **IMPLEMENT**: Create a temporary SRCALPHA surface the size of the rect, draw the semi-transparent rectangle to it, then blit it to the screen. Pattern already exists in `board_renderer.py` line 200-205 for legal move dots.
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: No new imports
- **GOTCHA**: Must convert screen coordinates correctly; the temp surface position must match the blit position.
- **VALIDATE**: Run the game, hover over own pieces, verify the border is semi-transparent (not fully opaque white).

### Task 4: Differentiate Den Tiles
- **ACTION**: Give each den a distinct visual identity
- **IMPLEMENT**: In `board_renderer.py`: Change `COLOR_DEN_BLUE` to a blue-tinted gold like `(200, 210, 255)` and `COLOR_DEN_RED` to a red-tinted gold like `(255, 200, 200)`. Add a small "B" or "R" letter drawn in the center of each den tile. Alternatively, add a colored border ring around the star in each player's color.
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: No new imports
- **GOTCHA**: Font rendering must use a small font size appropriate for the cell size.
- **VALIDATE**: Visual inspection: the two dens should be clearly distinguishable by color at a glance.

### Task 5: Differentiate Trap Tiles by Owner
- **ACTION**: Color-code each player's traps with a subtle tint
- **IMPLEMENT**: In `board_renderer.py`: For Blue's traps (row 0, cols 2 and 4; row 1, col 3), use a blue-tinted gray like `(180, 180, 210)`. For Red's traps (row 8, cols 2 and 4; row 7, col 3), use a red-tinted gray like `(210, 180, 180)`. Keep the "X" marker but add a small player-colored dot or border. The Board class already has `is_own_trap()` and `is_opponent_trap()` methods — use them.
- **MIRROR**: RENDERING_PATTERN, NAMING_CONVENTION
- **IMPORTS**: No new imports
- **GOTCHA**: Must pass player context to the renderer. BoardRenderer currently has no concept of "which player owns which trap." The trap positions are fixed and known from board.py constants. Use `BLUE_TRAPS` and `RED_TRAPS` sets from board.py.
- **VALIDATE**: Visual inspection: Blue's traps and Red's traps should have distinct tints.

### Task 6: Add Capture Move Indicators
- **ACTION**: Distinguish capture moves from regular moves in the legal-move display
- **IMPLEMENT**: In `board_renderer.py`: The `draw_highlights` method currently receives `legal_moves` as a list of `(from_pos, to_pos)` tuples. It needs to also know which target squares contain enemy pieces. Modify to accept a set of capture targets. For regular legal moves, draw the green dot. For capture moves, draw a red ring (circle outline) in `COLOR_CAPTURE = (220, 50, 50, 180)`. In `app.py`, when computing legal moves for display, also compute which targets are captures by checking `game.piece_at(to_pos) is not None`.
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: No new imports
- **GOTCHA**: Must pass capture info from app.py to board_renderer. The interface change needs to be backward-compatible or updated in both files.
- **VALIDATE**: Select a piece that can both move to empty squares and capture enemy pieces. Verify green dots for moves and red rings for captures.

### Task 7: Add Trapped Piece Visual Indicator
- **ACTION**: Show when a piece is in the opponent's trap (rank 0)
- **IMPLEMENT**: In `piece_renderer.py`: Add a method to draw a visual indicator on trapped pieces. Options: (a) draw a chain-link icon overlay, (b) draw a red "X" or warning symbol, (c) add a pulsing red outline. Simplest: draw a red circle outline around the piece token, or dim the piece, or add a small "×0" label. Check `game.effective_rank(piece)` or `rules._effective_rank()` — if the piece is in an opponent's trap, its rank is 0. Pass this info from app.py to the renderer. Add a `trapped` parameter to `get_piece_surface()`.
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: No new imports
- **GOTCHA**: Pre-rendered surfaces are cached. A trapped piece needs a separate cached surface. Either add a `trapped` variant to the cache key, or draw the indicator dynamically (not pre-cached).
- **VALIDATE**: Move a piece into an opponent's trap. Verify the visual indicator appears.

### Task 8: Show Win Reason in Game Over Overlay
- **ACTION**: Display why the game ended (den entry, elimination, or stalemate) in the game-over overlay
- **IMPLEMENT**: In `rules.py`: Modify `check_win()` to return a tuple `(winner, reason)` where reason is "den_entry", "elimination", or "stalemate". In `game.py`: Store the win reason in `GameState._win_reason`. In `app.py`: Pass the win reason to `ui_overlay.draw_game_over()`. In `ui_overlay.py`: Display the reason below the winner text, e.g., "Blue Wins! — Den Entry" or "Red Wins! — All Pieces Captured" or "Blue Wins! — Opponent Stalemate".
- **MIRROR**: ERROR_HANDLING (use explicit return types)
- **IMPORTS**: No new imports
- **GOTCHA**: `check_win()` currently returns `Player | None`. Changing the return type affects all callers (ai.py calls it too). Approach: add a separate `check_win_reason()` function, or change `check_win()` return type and update all callers.
- **VALIDATE**: Win by den entry and verify the reason is shown. Win by elimination and verify. Win by stalemate and verify.

### Task 9: Improve Water Animation
- **ACTION**: Make the water animation more visually appealing
- **IMPLEMENT**: In `board_renderer.py`: Replace the simple two-color toggle with: (a) multiple wave lines at different heights with sine-offset animation, (b) a subtle color gradient within each water tile, (c) small "ripple" circles that appear and fade. Simplest effective improvement: draw 3 horizontal wavy lines per water cell using sine offsets, with the animation frame advancing each tick. Keep the two-tone base colors but add semi-transparent wave overlay lines.
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: `import math` (for sine)
- **GOTCHA**: Water animation is drawn every frame. Keep it simple enough to not impact FPS. Pre-compute wave patterns if possible.
- **VALIDATE**: Visual inspection: water should look noticeably better than the current simple color toggle.

### Task 10: Improve Board Border
- **ACTION**: Add bevel/3D effect to the wooden border
- **IMPLEMENT**: In `board_renderer.py`: Draw the border as multiple concentric rectangles: outer dark brown, middle medium brown, inner light brown (highlight). This creates a simple bevel effect. Add a thin inner shadow line (1px dark line just inside the board edge).
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: No new imports
- **GOTCHA**: The border dimensions are computed from `self.border_size`. The bevel layers should use decreasing offsets.
- **VALIDATE**: Visual inspection: border should have a subtle 3D bevel look.

### Task 11: Fix Piece Name Truncation
- **ACTION**: Make piece display names consistent and readable
- **IMPLEMENT**: In `piece_renderer.py`: Change `PIECE_DISPLAY_NAMES` to use consistent abbreviations or a different approach. Options: (a) use all full names and reduce font size to fit, (b) use consistent 3-letter abbreviations (Rat, Cat, Dog, Wlf, Lpd, Tgr, Lio, Ele), (c) use Chinese characters for authenticity. Recommended: use 3-letter consistent abbreviations except for short names that fit: "Rat", "Cat", "Dog", "Wlf", "Lpd", "Tgr", "Lio", "Elt". Or simply reduce the font size by 1pt and use full names.
- **MIRROR**: NAMING_CONVENTION
- **IMPORTS**: No new imports
- **GOTCHA**: Font size affects text rendering metrics. Test at the minimum cell size (40px).
- **VALIDATE**: All piece names should be consistent in length and style.

### Task 12: Add Incremental Zobrist Hashing
- **ACTION**: Update Zobrist hash incrementally in make_move/undo_move instead of recomputing from scratch
- **IMPLEMENT**: In `game.py`: Add a `_zobrist_hash` field to `GameState`. In `make_move()`: XOR out the old position key, XOR in the new position key, XOR the captured piece key (if any), XOR the side-to-move key. In `undo_move()`: Reverse the XORs. In `pieces.py`: No changes needed (keys are already in ai.py). Move the Zobrist key arrays from `ai.py` to a shared location or import them. The keys in `ai.py` lines 52-60 are: `_ZOBRIST_PIECE[piece_type_idx][player_idx][col][row]` and `_ZOBRIST_SIDE`. In `game.py`, import these from `ai.py` or duplicate the generation. Best: keep keys in `ai.py` and expose via a `get_zobrist_key()` function, or move to `pieces.py`.
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: Import Zobrist keys from ai.py (or a shared module)
- **GOTCHA**: The hash must be correctly maintained through copy() as well. In `copy()`, copy the `_zobrist_hash` field. Also must handle undo of captures correctly (XOR out the captured piece, XOR in the side-to-move change). The side-to-move XOR must happen once per make_move/undo.
- **VALIDATE**: Run all existing tests. Add test: make a move, compute hash incrementally, compute hash from scratch, verify they match.

### Task 13: Add Null-Move Pruning
- **ACTION**: Implement null-move pruning in the alpha-beta search to increase effective search depth
- **IMPLEMENT**: In `ai.py`: Add a null-move search at the start of `_alpha_beta` for the maximizing player only (when not in check and depth >= 3). Skip the player's turn (give the opponent two moves in a row), search with reduced depth (R=2 or R=3), and use the result to prune. If the null-move search returns a score >= beta, return beta (fail-soft) — the position is so good that even doing nothing beats the bound. Implementation: before the main move loop, if `maximizing and depth >= 3 and not in_endgame`, call `_alpha_beta(game_state, depth - 1 - R, alpha, beta, False, ...)` with the same position (after toggling the side). In Jungle, zugzwang is rare but possible (a piece may be forced to move into a trap). Use conservative R=2 and disable in endgames (pieces <= 4 total).
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: Null-move in Jungle is riskier than in chess because (a) there's no check concept so "in_check" detection is harder, (b) zugzwang can occur when pieces are near traps. Mitigation: only apply when both players have >2 pieces, and use R=2 (not R=3).
- **VALIDATE**: Run `pytest tests/test_ai.py -v`. Add a test that null-move pruning is used in a midgame position. Verify AI-vs-random games still complete.

### Task 14: Add Den-Defense Evaluation Heuristic
- **ACTION**: Add evaluation terms for den defense/attack
- **IMPLEMENT**: In `ai.py` `_evaluate()`: Add two new terms: (1) **Den threat bonus**: For each opponent piece within Manhattan distance 3 of our den, add a penalty proportional to inverse distance. (2) **Den defense bonus**: For each own piece within Manhattan distance 2 of our den, add a bonus if opponent pieces are also nearby (blocking). Specifically: count opponent pieces within distance 3 of own den. If count > 0, bonus for each own piece within distance 2 of own den: `(2 - dist) * 40`. This rewards pieces that stay back to defend when the den is threatened.
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: Must use `game_state.pieces` to iterate, not a static lookup. The den positions are known from board.py: Blue den = (3,0), Red den = (3,8).
- **VALIDATE**: Add a test: position with an opponent piece near the den should score lower for the defending player when no defenders are present vs when defenders are present.

### Task 15: Add Mobility Evaluation
- **ACTION**: Count legal moves per piece and add a mobility bonus to the evaluation
- **IMPLEMENT**: In `ai.py` `_evaluate()`: For each piece, count the number of legal moves available (call `generate_legal_moves` filtered for that piece, or approximate by counting open adjacent squares). Add a small bonus: `mobility_bonus = total_moves * 5` (tuned). This helps the AI avoid positions where pieces are boxed in.
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: Import `generate_legal_moves` from rules (already imported)
- **GOTCHA**: Computing full legal moves for every piece at every leaf node is expensive. Optimization: only count at the top level of quiescence search, or use a cheaper approximation (count open orthogonal neighbors that are not blocked). Recommended: use a cheap approximation — count orthogonal neighbors that are in bounds, not water (unless rat), and not occupied by own piece. This is O(4) per piece instead of O(n).
- **VALIDATE**: Add a test: position with many open moves should score slightly higher than identical material with few open moves.

### Task 16: Add Late Move Reduction (LMR)
- **ACTION**: Reduce search depth for late moves in the move ordering that are unlikely to be best
- **IMPLEMENT**: In `ai.py` `_alpha_beta()`: After move ordering, for moves at index >= 4 (i.e., after the first 4 moves have been searched at full depth), reduce the search depth by 1 if the move is not a capture and not a den-entry move. This is a simple LMR scheme. If the reduced search returns a score > alpha, re-search at full depth.
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: Must track the move index in the loop. Only apply to "quiet" moves (non-captures, non-tactical). Must re-search if the reduced search raises alpha.
- **VALIDATE**: Run `pytest tests/test_ai.py -v`. Verify AI still finds good moves. Run an AI-vs-random game to verify completion.

### Task 17: Optimize Time Checks
- **ACTION**: Reduce the overhead of `time.time()` calls in the search by checking every N nodes instead of every node
- **IMPLEMENT**: In `ai.py`: Add a `_node_count` counter that increments at each node. Only call `time.time()` when `_node_count % 4096 == 0`. This reduces the overhead from thousands of system calls per second to a handful.
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: Must also check in quiescence search. The counter must be accessible from both `_alpha_beta` and `_quiescence`. Use a module-level or class-level counter.
- **VALIDATE**: Run a timed AI search. Verify that the time limit is still respected (may overshoot by up to 4096 nodes worth of time, which is acceptable for a 1.5s budget).

### Task 18: Improve Transposition Table Replacement
- **ACTION**: Replace the full-table-clear strategy with a two-bucket replacement scheme
- **IMPLEMENT**: In `ai.py`: Use two hash tables: (1) `_tt_depth` — depth-preferred, never overwritten by shallower entries (current behavior). (2) `_tt_always` — always-replace, smaller table. On lookup, check both. On store, always write to `_tt_always`, only write to `_tt_depth` if the new entry has >= depth. Set `_tt_always` size to 500K, `_tt_depth` size to 500K. When either exceeds its size, replace the oldest entry (or use a simple aging scheme).
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: The two-table lookup has a small overhead. The total memory usage is the same (1M entries). Must update `clear_tt()` to clear both.
- **VALIDATE**: Run AI-vs-random games. Verify no performance regression.

### Task 19: Rebalance Piece Values
- **ACTION**: Adjust piece values to better reflect their strategic importance
- **IMPLEMENT**: In `ai.py` `PIECE_VALUES`: Current values: Rat=300, Cat=200, Dog=350, Wolf=450, Leopard=600, Tiger=900, Lion=1000, Elephant=1100. Proposed changes: Elephant reduced from 1100 to 950 (cannot capture Rat, and Rat threatens it). Rat increased from 300 to 400 (can capture Elephant, critical tactical piece). Cat reduced from 200 to 150 (weakest piece, rarely useful). Dog increased from 350 to 400 (common defender). Wolf stays 450. Leopard stays 600. Tiger stays 900. Lion stays 1000. New ordering: Cat=150, Rat=400, Dog=400, Wolf=450, Leopard=600, Tiger=900, Lion=1000, Elephant=950.
- **MIRROR**: NAMING_CONVENTION
- **IMPORTS**: No new imports
- **GOTCHA**: The Rat-Elephant circular capture means the Rat's value should be weighted by whether the opponent still has an Elephant. A more sophisticated eval would adjust dynamically, but the base value change is a good start.
- **VALIDATE**: Play 10 AI-vs-AI games with old values and 10 with new values. Verify the new values lead to more wins or at least not fewer.

### Task 20: Add Endgame Knowledge
- **ACTION**: Enhance evaluation in simplified endgame positions (few pieces remaining)
- **IMPLEMENT**: In `ai.py` `_evaluate()`: When total pieces <= 6, add an endgame evaluation layer: (1) Heavily weight den proximity — the advancement bonus multiplier increases by 50%. (2) If a player has a Rat and the opponent has an Elephant, bonus the Rat by 200 (the Rat can eliminate the Elephant). (3) If a player has a Lion or Tiger and the opponent has no pieces that can capture them (no Rat remaining for opponent), bonus by 300 (dominant piece). (4) If a piece can reach the den in one move, add a large bonus (5000).
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: Endgame evaluation must not slow down midgame evaluation significantly. Add a fast piece-count check at the top of `_evaluate()` and branch accordingly.
- **VALIDATE**: Test in a simplified position: 1 Lion vs 1 Cat. The AI should push the Lion toward the opponent's den aggressively.

### Task 21: Extract Shared Test Helpers to conftest.py
- **ACTION**: Create `tests/conftest.py` with shared `make_game_with_pieces` fixture
- **IMPLEMENT**: Move the `make_game_with_pieces()` function from `test_rules.py:10-19` and `test_ai.py:15-23` to `tests/conftest.py`. Both test files currently have identical copies. Import it in both test files.
- **MIRROR**: TEST_STRUCTURE
- **IMPORTS**: `import pytest` in conftest.py
- **GOTCHA**: pytest auto-discovers conftest.py fixtures. The function must be available as a fixture or plain helper. Since it's a factory function (takes arguments), make it a plain function, not a fixture. pytest will still auto-import it.
- **VALIDATE**: Run `pytest tests/ -v`. All 118 tests should still pass.

### Task 22: Fix Test Quality Issues
- **ACTION**: Fix misleading and weak tests
- **IMPLEMENT**:
  1. `test_rules.py:316-340`: Remove dead code (elephant stalemate attempt lines 319-328).
  2. `test_ai.py:97-110`: Fix `test_no_moves_returns_none` to construct a guaranteed no-moves position (all pieces in corners with no adjacent empty squares and no captures).
  3. `test_ai.py:301-309`: Fix `test_skip_validation_rejects_illegal_move` to actually test rejection — call `game.make_move()` with an illegal move and `skip_validation=True`, verify it does NOT raise ValueError (unlike `skip_validation=False`).
  4. `test_game.py:166-173`: Fix `test_multiple_undo` to actually test consecutive undos (make 3 moves, undo all 3, verify state matches original).
- **MIRROR**: TEST_STRUCTURE
- **IMPORTS**: No new imports
- **GOTCHA**: The `test_no_moves_returns_none` fix requires careful position construction. Use pieces on the edge of the board, surrounded by own pieces and water.
- **VALIDATE**: Run `pytest tests/ -v`. All tests pass.

### Task 23: Add Missing Test Coverage
- **ACTION**: Cover the missing lines in rules.py (91%) and add new AI enhancement tests
- **IMPLEMENT**:
  1. Add tests for `_get_river_jump_landing` edge cases: out-of-bounds landing, water landing.
  2. Add test for own-den check during river jump (rules.py line 210).
  3. Add test for stalemate returning RED as winner (rules.py line 269).
  4. Add test for `Piece.__hash__` and `NotImplemented` path in `__eq__`.
  5. Add test for undo of winning move clearing `_winner`.
  6. Add test for `game.py` missing lines 71 and 106.
  7. Add tests for new AI features: null-move pruning, den-defense eval, mobility eval, LMR, endgame knowledge.
- **MIRROR**: TEST_STRUCTURE
- **IMPORTS**: No new imports
- **GOTCHA**: Some missing lines in rules.py are defensive edge cases that may be impossible to reach in normal play. If truly unreachable, add a comment explaining why rather than a forced test.
- **VALIDATE**: Run `pytest tests/ --cov=jungle_game.engine -v`. Coverage should be >= 95%.

### Task 24: Improve Thread Safety in AI Worker
- **ACTION**: Move all `ai_thinking` state management to the main thread
- **IMPLEMENT**: In `app.py`: Remove `self.ai_thinking = False` from the worker thread exception handler (line 295). Instead, in `_execute_ai_move()` and the main loop (line 179), always set `self.ai_thinking = False`. If the AI raises an exception, `ai_done` will still be set (via `finally`), and the main loop will call `_execute_ai_move()` which sees `ai_result is None`, sets `ai_thinking = False`, and the game recovers.
- **MIRROR**: ENGINE_GUI_SEPARATION
- **IMPORTS**: No new imports
- **GOTCHA**: Must ensure that `ai_done` is always set even on exception (the `finally` block already does this).
- **VALIDATE**: Manually verify by inspecting the code flow for an AI exception scenario.

### Task 25: Clean Release Package and Update README
- **ACTION**: Clean release artifacts and update README
- **IMPLEMENT**:
  1. Delete `release/.pytest_cache/` and add it to `.gitignore`.
  2. Remove the duplicate `release/README.txt` at the top level (keep only `release/jungle_game/README.txt`).
  3. Update `README.txt`: Add `F` key for board flip in Controls section. Add version info (1.0). Add a brief troubleshooting note ("If the exe fails to launch, ensure Windows Defender hasn't quarantined it").
  4. Add `pytest-cov` to `requirements.txt`.
- **MIRROR**: NAMING_CONVENTION
- **IMPORTS**: No new imports
- **GOTCHA**: The `.pytest_cache` may be recreated during builds. Add a cleanup step to the build process or add it to `.gitignore` in the release directory.
- **VALIDATE**: After rebuilding, verify `release/jungle_game/` contains no `.pytest_cache/`.

### Task 26: Add Icon to Executable
- **ACTION**: Generate a simple icon and add it to the PyInstaller build
- **IMPLEMENT**: Use Python to generate a simple `.ico` file programmatically (a small board-square icon with an animal silhouette, or just a colored square with "J" for Jungle). Use `PIL/Pillow` or pygame to create the icon, or use an online tool. Add the `.ico` file path to `build.spec` line 39: `icon='assets/icon.ico'`. Create an `assets/` directory if needed.
- **MIRROR**: RENDERING_PATTERN
- **IMPORTS**: May need Pillow for icon generation
- **GOTCHA**: PyInstaller requires `.ico` format. The icon must be at least 256x256 for modern Windows. Multiple sizes in the .ico are preferred (16x16, 32x32, 48x48, 256x256).
- **VALIDATE**: After building, right-click the exe and verify the icon appears.

### Task 27: Rebuild and Test Packaged Executable
- **ACTION**: Rebuild the executable with all changes and test it
- **IMPLEMENT**: Run `pyinstaller build.spec --distpath release --workpath build --clean -y`. Then run `release/jungle_game/jungle_game.exe` and verify: (1) game starts, (2) can play a full game, (3) board flip works, (4) AI plays, (5) game-over shows win reason, (6) dens are visually distinct, (7) traps are visually distinct, (8) capture moves show red rings, (9) water animation looks good.
- **MIRROR**: Build commands from CLAUDE.md
- **IMPORTS**: No new imports
- **GOTCHA**: Must have all dependencies installed in the build environment. The .spec file must reference any new asset files (icon).
- **VALIDATE**: Full manual test of the packaged exe.

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| TT flag correctness for minimizer | Minimizer position stored in TT | Correct UPPERBOUND/LOWERBOUND/EXACT flag | Yes |
| Incremental Zobrist hash | Make/undo sequence | Incremental hash == full recompute | Yes |
| Null-move pruning | Midgame position, depth >= 3 | Null-move search triggered, not in endgame | Yes |
| Den-defense eval | Opponent piece near den, no defenders | Lower score than with defenders | Yes |
| Mobility eval | Pieces with many/few moves | More mobility = higher score | Yes |
| LMR | Late quiet move at depth >= 3 | Reduced depth search, re-search if raises alpha | Yes |
| Endgame eval | Simplified position (<= 6 pieces) | Stronger den-proximity weighting | Yes |
| Click guard for Red human | first_player=RED, current_player=RED | Clicks allowed | Yes |
| Hover alpha rendering | SRCALPHA surface + blit | Semi-transparent border visible | No |
| Win reason display | Den entry win | "Den Entry" shown | No |
| Consecutive undo | 3 moves made, 3 undos | State matches original | Yes |

### Edge Cases Checklist
- [x] Rat in water vs land capture rules (already tested)
- [x] River jump blocking by Rat (already tested)
- [ ] Null-move in zugzwang-like position (pieces near traps)
- [ ] LMR re-search when reduced search raises alpha
- [ ] Incremental Zobrist hash with captures and undo
- [ ] Human playing Red in HUMAN_VS_AI mode
- [ ] Trapped piece visual indicator
- [ ] Win by stalemate showing reason

---

## Validation Commands

### Static Analysis
```bash
python -m py_compile jungle_game/engine/ai.py
python -m py_compile jungle_game/gui/app.py
python -m py_compile jungle_game/gui/board_renderer.py
```
EXPECT: No syntax errors

### Unit Tests
```bash
pytest tests/ -v
```
EXPECT: All tests pass

### Coverage
```bash
pytest tests/ --cov=jungle_game.engine -v
```
EXPECT: >= 95% coverage

### Full Game Test
```bash
python main.py --cli
```
EXPECT: Smoke test passes, no errors

### AI Strength Test
```bash
pytest tests/test_ai.py -v -k "game"
```
EXPECT: AI-vs-random games complete within timeout

### Build Test
```bash
pyinstaller build.spec --distpath release --workpath build --clean -y
```
EXPECT: Build succeeds, exe created

### Manual Validation
- [ ] Launch game, play as Blue, win by den entry
- [ ] Toggle to "AI First", play as Red, verify clicks work
- [ ] Verify dens are different colors
- [ ] Verify traps are player-tinted
- [ ] Verify capture moves show red rings
- [ ] Verify trapped pieces show indicator
- [ ] Verify game-over shows win reason
- [ ] Verify water animation improved
- [ ] Verify board border has bevel
- [ ] Verify piece names are consistent
- [ ] Press F to flip board, verify visual flip only
- [ ] Start AI vs AI game, verify it plays to completion

---

## Acceptance Criteria
- [ ] All 27 tasks completed
- [ ] All bugs fixed (TT flag, click guard, hover alpha, den colors)
- [ ] AI enhanced with null-move pruning, LMR, den-defense, mobility, endgame knowledge
- [ ] Incremental Zobrist hashing implemented
- [ ] Time check optimization implemented
- [ ] TT replacement scheme improved
- [ ] Piece values rebalanced
- [ ] All visual improvements implemented (dens, traps, captures, trapped pieces, water, border, names)
- [ ] Win reason shown in game-over overlay
- [ ] All validation commands pass
- [ ] Tests written and passing
- [ ] Coverage >= 95% for engine
- [ ] No type errors
- [ ] Packaged exe tested and working
- [ ] Release folder clean (no pytest cache)
- [ ] README updated with controls and version

## Completion Checklist
- [ ] Code follows discovered patterns (engine/GUI separation)
- [ ] Error handling matches codebase style
- [ ] Tests follow test patterns
- [ ] No hardcoded values
- [ ] No unnecessary scope additions
- [ ] Self-contained — no questions needed during implementation

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Null-move pruning causes wrong moves in Jungle (zugzwang) | Medium | High | Conservative R=2, disable in endgames, test extensively |
| Piece value rebalancing weakens AI | Low | Medium | Run AI-vs-AI comparison before/after |
| Incremental Zobrist hash bugs | Medium | High | Add comprehensive make/undo hash consistency tests |
| GUI changes break existing rendering | Low | Low | Test at multiple screen sizes, verify flip still works |
| PyInstaller build fails with new assets | Low | Medium | Test build early, keep icon generation simple |

## Notes
- The AI enhancements (null-move, LMR, incremental hash, den-defense, mobility, endgame) together should increase effective search depth by 2-3 plies, making the AI significantly stronger.
- Visual improvements are important for meeting the "polished and attractive" requirement in prompt.md.
- All engine changes maintain the zero-GUI-import invariant.
- The click guard bug is the most impactful UX bug — it makes the game unplayable when the human chooses to play Red.