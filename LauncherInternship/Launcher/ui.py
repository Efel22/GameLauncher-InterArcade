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
  from PIL import Image, ImageTk, ImageOps
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

    self._photo = self._load_cover(game) 

    # Fixed-size box in actual pixels, so every case is exactly the same
    # size whether it has real cover art or falls back to a placeholder.
    # (A text-only Label's width/height are in character/line units, not
    # pixels, which is what made placeholders a different size than covers
    # before - pack_propagate(False) below is what locks this frame down.)
    
    self.art_frame = tk.Frame(self, width=CASE_WIDTH, height=CASE_HEIGHT, bg=CASE_BG)
    self.art_frame.pack_propagate(False)
    self.art_frame.pack(padx=2, pady=(2, 0))

    if self._photo is not None:
      self.image_label = tk.Label(self.art_frame, image=self._photo, bd=0, cursor="hand2")
    else:
      self.image_label = tk.Label(
          self.art_frame,
          text=self._initials(game["name"]),
          bg=_placeholder_color(game["name"]),
          fg="#ffffff",
          font=("Arial", 16, "bold"),
          cursor="hand2",
      )
    self.image_label.pack(fill="both", expand=True)

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

    for widget in (self, self.art_frame, self.image_label, self.title_label):
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
        # Crop-to-fill instead of stretch, so covers that aren't exactly
        # CASE_WIDTH x CASE_HEIGHT don't come out squished.

        img = ImageOps.fit(img, (CASE_WIDTH, CASE_HEIGHT), Image.LANCZOS)
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
  background_image: path to a photo to fill the window with, or None for a
      plain BG_COLOR background. The photo is drawn on the same canvas that
      holds the game grid, cropped to always cover the current window size
      (like CSS background-size: cover), and re-drawn whenever the window
      is resized. The grid itself sits on its own solid panel on top of it -
      the photo shows around that panel, not through the gaps between cases.
  """

  def __init__(self, parent, games, on_launch, columns=COLUMNS, background_image=None):
    super().__init__(parent, bg=BG_COLOR)
    self.games = games
    self.on_launch = on_launch
    self.columns = columns
    self.cases = []

    self.background_image_path = background_image
    self._bg_photo = None
    self._bg_item = None

    self._build_grid()

  def _build_grid(self):
    self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
    scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
    self.grid_frame = tk.Frame(self.canvas, bg=BG_COLOR)

    self.grid_frame.bind(
        "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    )
    self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
    self.canvas.configure(yscrollcommand=scrollbar.set)

    self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scrollbar.pack(side="right", fill="y")

    # Mouse wheel scrolling (Windows/Mac uses <MouseWheel>, Linux uses Button-4/5).
    self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
    self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
    self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    # Redraw the background photo (if any) to fit whenever the window resizes.
    self.canvas.bind("<Configure>", lambda e: self._draw_background())

    for i, game in enumerate(self.games):
      row, col = divmod(i, self.columns)
      case = GameCase(self.grid_frame, game, self.on_launch)
      case.grid(row=row, column=col, padx=GRID_PADDING, pady=GRID_PADDING)
      self.cases.append(case)

  def _draw_background(self):
    if not self.background_image_path or not _HAS_PIL:
      return

    path = Path(self.background_image_path)
    if not path.is_file():
      return

    width = self.canvas.winfo_width()
    height = self.canvas.winfo_height()
    if width <= 1 or height <= 1:
      return  # canvas hasn't been laid out yet

    try:
      img = Image.open(path).convert("RGB")
      img = ImageOps.fit(img, (width, height), Image.LANCZOS)
      self._bg_photo = ImageTk.PhotoImage(img)
    except Exception:
      return

    if self._bg_item is None:
      self._bg_item = self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)
      self.canvas.tag_lower(self._bg_item)  # keep it behind the game grid
    else:
      self.canvas.itemconfigure(self._bg_item, image=self._bg_photo)


class LauncherWindow(tk.Tk):
  """Top-level window wrapping the GameLibrary grid. Opens full screen by default."""

  def __init__(self, games, on_launch, background_image=None, title="Game Library"):
    super().__init__()
    self.title(title)
    self.configure(bg=BG_COLOR)

    # Full screen on open. Escape drops to a normal maximized window rather
    # than closing the app, so testing/alt-tabbing doesn't leave you stuck.
    self.attributes("-fullscreen", True)
    self.bind("<Escape>", self._toggle_fullscreen)

    self.library = GameLibrary(self, games, on_launch, background_image=background_image)
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