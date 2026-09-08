"""
Sanity-checks the cover art referenced in GAMES (game_launcher.py) without
opening the full UI. Run this after adding images to covers/:

    python check_covers.py

For each game it reports one of:
  [ok]               file exists and opens correctly - shows its real size
  [no cover set]      "cover" is None - that game will use the placeholder
  [MISSING FILE]      "cover" points at a path that doesn't exist
  [UNREADABLE]        the file exists but Pillow couldn't open it (corrupt /
                       not actually an image / unsupported format)
"""

from pathlib import Path

from game_launcher import GAMES, COVERS_DIR

try:
  from PIL import Image
  HAS_PIL = True
except ImportError:
  HAS_PIL = False
  print("Pillow is not installed - install it to get real cover-art checks:")
  print("    pip install pillow")
  print("Without it, covers can only be confirmed to exist, not opened.\n")

print(f"Looking for cover art in: {COVERS_DIR}\n")

problems = 0

for game in GAMES:
  name = game["name"]
  cover = game.get("cover")

  if not cover:
    print(f"[no cover set]   {name}")
    continue

  path = Path(cover)

  if not path.is_file():
    print(f"[MISSING FILE]   {name} -> {path}")
    problems += 1
    continue

  if HAS_PIL:
    try:
      with Image.open(path) as img:
        ratio = img.width / img.height
        note = "" if 0.6 <= ratio <= 0.85 else "  (not close to the 3:4 case shape - will get cropped)"
        print(f"[ok]             {name} -> {path.name}  ({img.width}x{img.height}, {img.format}){note}")
    except Exception as e:
      print(f"[UNREADABLE]     {name} -> {path.name}  ({e})")
      problems += 1
  else:
    print(f"[found]          {name} -> {path.name}")

print()
if problems:
  print(f"{problems} game(s) have a cover path that won't work - fix those, then re-run this check.")
else:
  print("All set - every cover either resolves to a real image or is intentionally unset.")