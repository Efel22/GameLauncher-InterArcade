import os
import subprocess
import webbrowser
from tkinter import messagebox
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


# all work (through Pillow), aim for roughly a 3:4 portrait ratio (e.g.
# 300x400px) since that's the case shape in the grid - other ratios still
# work, they just get center-cropped to fit instead of stretched.
COVERS_DIR = BASE_DIR / "covers"

# Background photo for the launcher window, or None for a plain dark color.
# Point this at any image to swap the wallpaper - e.g.:
#   BACKGROUND_IMAGE = str(BASE_DIR / "backgrounds" / "space.jpg")
BACKGROUND_IMAGE = None


def _cover(filename):
  """Path to a file in covers/, or None if this game has no art yet."""
  return str(COVERS_DIR / filename) if filename else None


# Define your games here. "cover" is optional - give _cover() the filename of
# an image you dropped in covers/ and the grid UI will show it; leave it
# _cover(None) (or just None) and you'll get a colored placeholder with the
# game's initials instead. Run check_covers.py any time to verify these
# actually resolve to real, openable image files before firing up the UI.
GAMES = [
    {
        "name": "Memories of Ladein",
        "path": r"..\..\ArcadeGames\MemoriesOfLadein\MemoriesOfLadien_v1.1.3\Project_Fallen_Angel.exe",
        "cover": _cover("memories_of_ladein.png"),
    },
    {
        "name": "Proyecto Emergencia",
        "path": r"..\..\ArcadeGames\MasterWorkforceProject\Windows\ProyectoEmergencia.exe",
        "cover": _cover("proyecto_emergencia.png"),
    },
    {
        "name": "Vanishing stars",
        "path": r"..\..\ArcadeGames\VanishingStars\Windows\Vanishing Stars.exe",
        "cover": _cover("vanishing_stars.png"),
    },
    {
        "name": "Escape from Area 51",
        "path": r"..\..\ArcadeGames\LockedInArea51\TigerGameJam.exe",
        "cover": _cover("escape_from_area_51.png"),
    },

    {
      "name" : "Medieval_Mission_1",
      "path": r"..\..\ArcadeGames\Medieval_Mission_1\Windows\Medieval_Mission_1.html",
      "cover": _cover(None)
    },
    # HTML/browser-based game example:
    # {"name": "Some Web Game", "path": r"..\..\ArcadeGames\SomeWebGame\index.html", "cover": _cover(None)},


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

      subprocess.Popen([str(full_path)], cwd=str(full_path.parent), shell=True)

    else:
      # Fallback for any other file type: let Windows decide how to open it.
      os.startfile(str(full_path))

  except Exception as e:
    messagebox.showerror("Error", f"Could not launch game:\n{e}")