import os
import subprocess
import tkinter as tk
from tkinter import messagebox

# Define your games here: "Display Name": "Full path to executable or script"
GAMES = {
    "Memories of Ladein": r"..\..\ArcadeGames\MemoriesOfLadein\MemoriesOfLadien_v1.1.3\Project_Fallen_Angel.exe",
    "Proyecto Emergencia": r"..\..\ArcadeGames\MasterWorkforceProject\ProyectoEmergencia.exe",
    "Vanishing stars": r"..\..\ArcadeGames\VanishingStars\Windows\Vanishing Stars.exe",
    "Escape from Area 51": r"..\..\ArcadeGames\LockedInArea51\TigerGameJam.exe",
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
    if os.path.exists(path):
      try:
        # subprocess.Popen runs the game independently of the launcher
        subprocess.Popen([path])
      except Exception as e:
        messagebox.showerror("Error", f"Could not launch game:\n{e}")
    else:
      messagebox.showerror(
          "File Not Found", f"The path does not exist:\n{path}"
      )


if __name__ == "__main__":
  app = GameLauncher()
  app.mainloop()
