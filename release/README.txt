Jungle (Dou Shou Qi) - Windows Desktop Game
=============================================

DESCRIPTION
Jungle (also known as Dou Shou Qi or Animal Chess) is a traditional Chinese
strategy board game. Two players compete to either move a piece into the
opponent's den or capture all of the opponent's pieces.

SYSTEM REQUIREMENTS
- Windows 10 or later
- No installation required

HOW TO LAUNCH
Double-click jungle_game.exe to start the game.

GAMEPLAY
You play as Blue (top of the board). The AI plays as Red (bottom).
Blue moves first. Click one of your pieces to select it, then click a
highlighted target square to move there.

CONTROLS
- Left click: Select piece / Move to target
- ESC: Quit the game
- "New Game" button: Start a new Human vs AI game
- "AI vs AI" button: Watch the AI play against itself

PIECE RANKS (strongest to weakest)
 8. Elephant     - Can capture any piece except Rat
 7. Lion         - Can jump across the river (vertical + horizontal)
 6. Tiger        - Can jump across the river (vertical only)
 5. Leopard
 4. Wolf
 3. Dog
 2. Cat
 1. Rat          - Can capture Elephant (from land only); can enter water

CAPTURE RULES
- Higher rank captures lower rank
- Same rank captures each other
- Special: Rat can capture Elephant (but only from land, not from water)
- Special: Elephant cannot capture Rat under any circumstance

SPECIAL TERRAIN
- Water (blue): Only the Rat can enter. Lion and Tiger can jump across
  (blocked if any Rat is in the intervening water squares).
- Traps (dark squares with X): A piece in the opponent's trap becomes
  rank 0 and can be captured by any enemy piece. Effect ends when leaving.
- Den (gold square with star): Move any piece into the opponent's den to win.
  You cannot enter your own den.

WIN CONDITIONS
- Move any piece into the opponent's den, OR
- Capture all of the opponent's pieces

AI VS AI MODE
Click "AI vs AI" to watch the computer play against itself. Both sides
use the alpha-beta search AI. This mode is useful for observing strategy.

RULES REFERENCE
Full rules: https://en.wikipedia.org/wiki/Jungle_(board_game)

TECHNICAL NOTES
This game was developed using Claude Code (claude.ai/code) powered by the GLM-5.1 model.