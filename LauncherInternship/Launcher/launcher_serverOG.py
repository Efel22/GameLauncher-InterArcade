"""
launcher_server.py

Tiny local helper for launcher.html.

Browsers can't spawn local .exe files on their own (that's a deliberate
sandbox restriction — any website could otherwise run programs on your
machine). This script is the piece that runs natively on your OS instead,
the same way the old PySide6 app's GameCard.launch_game() did:

    - It serves launcher.html (and any files next to it / above it, like
      your ../assets/images/... posters) over http://localhost:8765/
    - It exposes POST /launch, which resolves the requested .exe path
      and calls subprocess.Popen on it, exactly like the Qt version did.

USAGE
-----
1. Put this file in the SAME folder as launcher.html
   (i.e. wherever the old launcher.py used to live, so that
   "../assets/..." and "../../ArcadeGames/..." resolve the same way).
2. Run:  python launcher_server.py
3. It opens your browser to http://localhost:8765/ automatically.
4. Click a game poster -> it launches for real.

No third-party packages required (standard library only).
"""

import json
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "launcher.html"
PORT = 8765

# Static files (posters, logo, tiger, fonts) live one level up from this
# script, e.g. BASE_DIR.parent / "assets/images/...". launcher.html refers
# to them with plain paths like "assets/images/..." (no "../"), since a
# browser can't ever navigate above the server root with "../". We make
# that path resolve correctly by treating BASE_DIR.parent as the web root
# for every GET except "/" itself.
WEB_ROOT = BASE_DIR.parent

# Map file extensions to content types for the static file server.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # GET: serve launcher.html and any file relative to BASE_DIR
    # (including "../" paths, so posters/logo/tiger/fonts resolve
    # exactly like they did for the desktop app).
    # --------------------------------------------------------
    def do_GET(self):
        url_path = urlparse(self.path).path

        if url_path == "/":
            target = HTML_FILE
        else:
            # Resolve against WEB_ROOT (one level up), not BASE_DIR,
            # so "assets/images/..." in the HTML lands on the real
            # assets folder. Traversal is allowed on purpose: this is
            # a local trusted tool serving your own game folders, same
            # trust level as the old desktop app.
            target = (WEB_ROOT / url_path.lstrip("/")).resolve()

        if not target.exists() or not target.is_file():
            self.send_error(404, f"Not found: {url_path}")
            return

        content_type = CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")

        try:
            data = target.read_bytes()
        except Exception as e:
            self.send_error(500, f"Could not read file: {e}")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --------------------------------------------------------
    # POST /launch  { "exe": "../../ArcadeGames/.../Game.exe" }
    # Mirrors GameCard.launch_game() from the Qt app.
    # --------------------------------------------------------
    def do_POST(self):
        if urlparse(self.path).path != "/launch":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"

        try:
            payload = json.loads(body or b"{}")
            exe_arg = payload.get("exe", "")
        except Exception:
            self._json_response(400, {"ok": False, "error": "Invalid request body"})
            return

        if not exe_arg:
            self._json_response(400, {"ok": False, "error": "Missing 'exe' path"})
            return

        exe = Path(exe_arg)
        if not exe.is_absolute():
            exe = (BASE_DIR / exe).resolve()

        if not exe.exists():
            self._json_response(404, {"ok": False, "error": f"Could not find: {exe}"})
            return

        try:
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
        except Exception as e:
            self._json_response(500, {"ok": False, "error": str(e)})
            return

        self._json_response(200, {"ok": True})

    def _json_response(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # Quiet the default request logging a little.
    def log_message(self, format, *args):
        print(f"[launcher_server] {self.address_string()} - {format % args}")


def main():
    if not HTML_FILE.exists():
        print(f"Could not find launcher.html next to this script at: {HTML_FILE}")
        print("Put launcher_server.py in the same folder as launcher.html and try again.")
        return

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"

    print(f"Inter Arcade Games launcher running at {url}")
    print("Press Ctrl+C to stop.")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()