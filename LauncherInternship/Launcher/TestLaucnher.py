import os
import subprocess
import webbrowser
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Folder this script lives in. All GAME paths are resolved relative to this,
# so the launcher works no matter what directory it's double-clicked or run from.
BASE_DIR = Path(__file__).resolve().parent

# Define your games here: "Display Name": "Path to executable or html file"
# Paths can be relative (resolved against BASE_DIR) or absolute.
GAMES = {
    "Memories of Ladein": r"..\..\ArcadeGames\MemoriesOfLadein\MemoriesOfLadien_v1.1.3\Project_Fallen_Angel.exe",
    "Proyecto Emergencia": r"..\..\ArcadeGames\MasterWorkforceProject\ProyectoEmergencia.exe",
    "Vanishing stars": r"..\..\ArcadeGames\VanishingStars\Windows\Vanishing Stars.exe",
    "Escape from Area 51": r"..\..\ArcadeGames\LockedInArea51\TigerGameJam.exe",
    # HTML/browser-based game example:
    # "Some Web Game": r"..\..\ArcadeGames\SomeWebGame\index.html",
}


class GameLauncher(tk.Tk):

  def __init__(self):
    super().__init__()
    self.title("Test Game launcher")
    self.geometry("400x300")
    self.configure(bg="#222222")

    title_label = tk.Label(
        self,
        text="Games",
        font=("Arial", 18, "bold"),
        fg="#ffffff",
        bg="#222222",
    )
    title_label.pack(pady=20)

    for name, path in GAMES.items():
      btn = tk.Button(
          self,
          text=name,
          font=("Arial", 12),
          width=25,
          bg="#444444",
          fg="#ffffff",
          command=lambda p=path: self.launch_game(p),
      )
      btn.pack(pady=10)

  def launch_game(self, path):
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


if __name__ == "__main__":
  app = GameLauncher()
  app.mainloop()