"""Jungle (Dou Shou Qi) - Entry point."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from jungle_game.engine.game import GameState
        from jungle_game.engine.pieces import Player
        # Simple CLI smoke test
        game = GameState()
        print("Jungle (Dou Shou Qi) - CLI Mode")
        print(f"Current player: {game.current_player.name}")
        print(f"Legal moves: {len(game.get_legal_moves())}")
        print(f"Blue pieces: {len(game.get_player_pieces(Player.BLUE))}")
        print(f"Red pieces: {len(game.get_player_pieces(Player.RED))}")
    else:
        # Launch GUI
        from jungle_game.gui.app import JungleApp
        app = JungleApp()
        app.run()


if __name__ == "__main__":
    main()