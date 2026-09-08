"""
Entry point: wires the game data/launch logic (game_launcher.py) to the
Steam-like grid UI (ui.py). Run this file to start the launcher.
"""

from game_launcher import GAMES, launch_game
from ui import LauncherWindow

if __name__ == "__main__":
  app = LauncherWindow(GAMES, on_launch=lambda game: launch_game(game["path"]))
  app.mainloop()