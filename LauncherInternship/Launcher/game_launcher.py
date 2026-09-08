"""
Game data + launch logic, kept free of any UI code.

ui.py imports GAMES and calls launch_game() through a callback - this file
doesn't know or care whether the UI is the old button list or the new
Steam-like grid.
"""

import os
import subprocess
import webbrowser
from tkinter import messagebox
from pathlib import Path

# Folder this script lives in. All paths below are resolved relative to this,
# so the launcher works no matter what directory it's double-clicked or run from.
BASE_DIR = Path(__file__).resolve().parent

# Define your games here. "cover" is optional - point it at a cover-art image
# (png/jpg) and the grid UI will show it; leave it None and you'll get a
# colored placeholder with the game's initials instead.
GAMES = [
    {
        "name": "Memories of Ladein",
        "path": r"..\..\ArcadeGames\MemoriesOfLadein\MemoriesOfLadien_v1.1.3\Project_Fallen_Angel.exe",
        "cover": None,
    },
    {
        "name": "Proyecto Emergencia",
        "path": r"..\..\ArcadeGames\MasterWorkforceProject\Windows\ProyectoEmergencia.exe",
        "cover": None,
    },
    {
        "name": "Vanishing stars",
        "path": r"..\..\ArcadeGames\VanishingStars\Windows\Vanishing Stars.exe",
        "cover": None,
    },
    {
        "name": "Escape from Area 51",
        "path": r"..\..\ArcadeGames\LockedInArea51\TigerGameJam.exe",
        "cover": None,
    },
    # HTML/browser-based game example:
    # {"name": "Some Web Game", "path": r"..\..\ArcadeGames\SomeWebGame\index.html", "cover": None},
]


def launch_game(path):
  """Resolve `path` and open it the right way for its file type."""
  # Resolve relative paths against the launcher's own folder, not the
  # current working directory (which changes depending on how this is run).
  full_path = Path(path)
  if not full_path.is_absolute():
    full_path = BASE_DIR / full_path
  full_path = full_path.resolve()

  if not full_path.exists():
    messagebox.showerror(
        "File Not Found", f"The path does not exist:\n{full_path}"
    )
    return

  suffix = full_path.suffix.lower()

  try:
    if suffix in (".html", ".htm"):
      # Open local HTML games in the default browser. as_uri() gives a
      # proper file:// URL, and this needs no internet connection.
      webbrowser.open(full_path.as_uri())

    elif suffix == ".exe":
      # Launch with cwd set to the game's own folder so it can find its
      # data/asset files (Unreal/Unity builds often assume this).
      subprocess.Popen([str(full_path)], cwd=str(full_path.parent))

    else:
      # Fallback for any other file type: let Windows decide how to open it.
      os.startfile(str(full_path))

  except Exception as e:
    messagebox.showerror("Error", f"Could not launch game:\n{e}")