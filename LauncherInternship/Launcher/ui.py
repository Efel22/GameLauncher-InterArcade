
"""
Steam-like library UI for the game launcher.
 
This file only handles layout and clicks: a scrollable grid of cover-art
"cases," each with its title shown underneath at all times. Clicking a case
launches that game immediately - no separate selection step. It doesn't know
how to launch anything itself - pass in an on_launch(game) callback (e.g.
launch_game from game_launcher.py) and this module calls it on click.
 
Requires Pillow for resizing cover art to a uniform size:
    pip install pillow
Without Pillow, games with no usable cover fall back to a colored
placeholder with the game's initials, so the layout still works.
"""
 
import tkinter as tk
from pathlib import Path
 
try:
  from PIL import Image, ImageTk
  _HAS_PIL = True
except ImportError:
  _HAS_PIL = False
 
CASE_WIDTH = 90
CASE_HEIGHT = 120
GRID_PADDING = 12
COLUMNS = 6
 
BG_COLOR = "#1b1f27"
CASE_BG = "#2b3040"
BORDER_COLOR = "#2b3040"
HOVER_BORDER = "#66c0f4"  # Steam blue
TEXT_COLOR = "#ffffff"
 
_PLACEHOLDER_PALETTE = ["#3a4a6b", "#4a3a6b", "#6b3a4a", "#3a6b55", "#6b5a3a", "#3a5a6b"]
 
 
def _placeholder_color(name):
  """Deterministic color per game name, so cover-less games still look distinct."""
  return _PLACEHOLDER_PALETTE[hash(name) % len(_PLACEHOLDER_PALETTE)]
 
 
class GameCase(tk.Frame):
  """One clickable cover-art 'case' in the grid. Title sits below it, always visible."""
 
  def __init__(self, parent, game, on_click):
    super().__init__(
        parent,
        bg=BG_COLOR,
        highlightthickness=2,
        highlightbackground=BORDER_COLOR,
    )
    self.game = game
    self.on_click = on_click
 
    self._photo = self._load_cover(game)  # keep a reference so it isn't GC'd
 
    if self._photo is not None:
      self.image_label = tk.Label(self, image=self._photo, bd=0, cursor="hand2")
    else:
      self.image_label = tk.Label(
          self,
          text=self._initials(game["name"]),
          width=CASE_WIDTH // 10,
          height=CASE_HEIGHT // 20,
          bg=_placeholder_color(game["name"]),
          fg="#ffffff",
          font=("Arial", 16, "bold"),
          cursor="hand2",
      )
    self.image_label.pack(padx=2, pady=(2, 0))
 
    self.title_label = tk.Label(
        self,
        text=game["name"],
        bg=BG_COLOR,
        fg=TEXT_COLOR,
        font=("Arial", 9),
        wraplength=CASE_WIDTH,
        justify="center",
        cursor="hand2",
    )
    self.title_label.pack(padx=2, pady=(4, 4))
 
    for widget in (self, self.image_label, self.title_label):
      widget.bind("<Button-1>", self._handle_click)
      widget.bind("<Enter>", self._handle_enter)
      widget.bind("<Leave>", self._handle_leave)
 
  @staticmethod
  def _initials(name):
    words = name.split()
    return "".join(w[0].upper() for w in words[:2]) or "?"
 
  def _load_cover(self, game):
    cover = game.get("cover")
    if not cover:
      return None
    path = Path(cover)
    if not path.is_file():
      return None
    try:
      if _HAS_PIL:
        img = Image.open(path).convert("RGB")
        img = img.resize((CASE_WIDTH, CASE_HEIGHT), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
      # No Pillow: tkinter can only load gif/png natively and can't resize,
      # so this only looks right if the source image is already the right size.
      return tk.PhotoImage(file=str(path))
    except Exception:
      return None
 
  def _handle_click(self, _event):
    self.on_click(self.game)
 
  def _handle_enter(self, _event):
    self.configure(highlightbackground=HOVER_BORDER)
 
  def _handle_leave(self, _event):
    self.configure(highlightbackground=BORDER_COLOR)
 
 
class GameLibrary(tk.Frame):
  """
  Scrollable Steam-like grid of games. Clicking a case launches it directly.
 
  games: list of dicts, each {"name": str, "path": str, "cover": str | None}
  on_launch: called with the game dict as soon as its case is clicked
  """
 
  def __init__(self, parent, games, on_launch, columns=COLUMNS):
    super().__init__(parent, bg=BG_COLOR)
    self.games = games
    self.on_launch = on_launch
    self.columns = columns
    self.cases = []
 
    self._build_grid()
 
  def _build_grid(self):
    canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
    scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
    self.grid_frame = tk.Frame(canvas, bg=BG_COLOR)
 
    self.grid_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
 
    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scrollbar.pack(side="right", fill="y")
 
    # Mouse wheel scrolling (Windows/Mac uses <MouseWheel>, Linux uses Button-4/5).
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
 
    for i, game in enumerate(self.games):
      row, col = divmod(i, self.columns)
      case = GameCase(self.grid_frame, game, self.on_launch)
      case.grid(row=row, column=col, padx=GRID_PADDING, pady=GRID_PADDING)
      self.cases.append(case)
 
 
class LauncherWindow(tk.Tk):
  """Top-level window wrapping the GameLibrary grid. Opens full screen by default."""
 
  def __init__(self, games, on_launch, title="Game Library"):
    super().__init__()
    self.title(title)
    self.configure(bg=BG_COLOR)
 
    # Full screen on open. Escape drops to a normal maximized window rather
    # than closing the app, so testing/alt-tabbing doesn't leave you stuck.
    self.attributes("-fullscreen", True)
    self.bind("<Escape>", self._toggle_fullscreen)
 
    self.library = GameLibrary(self, games, on_launch)
    self.library.pack(fill="both", expand=True)
 
  def _toggle_fullscreen(self, _event=None):
    is_fullscreen = bool(self.attributes("-fullscreen"))
    self.attributes("-fullscreen", not is_fullscreen)
    if is_fullscreen:
      self.state("zoomed")  # land on a maximized window, not a tiny default one
 
 
if __name__ == "__main__":
  # Standalone preview: no cover art needed to see the layout, since GameCase
  # falls back to a colored placeholder + initials when "cover" is None.
  demo_games = [
      {"name": "Memories of Ladein", "path": "", "cover": None},
      {"name": "Proyecto Emergencia", "path": "", "cover": None},
      {"name": "Vanishing Stars", "path": "", "cover": None},
      {"name": "Escape from Area 51", "path": "", "cover": None},
  ]
 
  def demo_launch(game):
    print(f"Would launch: {game['name']}")
 
  app = LauncherWindow(demo_games, demo_launch)
  app.mainloop()