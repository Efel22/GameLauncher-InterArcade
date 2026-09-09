"""
launcher_server.py

Local helper for launcher.html.

Features:
    - Serves launcher.html and assets
    - Opens Google Chrome automatically in kiosk mode
    - Launches local .exe games
    - Finds the actual game window (including child processes
      spawned by launcher/bootstrapper executables)
    - Attempts to force the game window to the foreground
    - Keeps the launcher server running while games are open

USAGE
-----

1. Put this file in the SAME folder as launcher.html.

2. Run:

       python launcher_server.py

3. Chrome will automatically open the launcher in kiosk mode.

4. Click a game poster to launch the game.

5. The game should be brought to the foreground automatically.

6. When the game closes, Chrome remains open with the launcher.
"""


import json
import subprocess
import webbrowser
import time
import threading
import ctypes
import ctypes.wintypes as wintypes

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

HTML_FILE = BASE_DIR / "launcher.html"

PORT = 8765


# Static files live one level above this script.
#
# Example:
#
# LauncherInternado/
# ├── ArcadeGames/
# │
# └── LauncherInternship/
#     └── Launcher/
#         ├── launcher.html
#         └── launcher_server.py
#

WEB_ROOT = BASE_DIR.parent


# ============================================================
# CONTENT TYPES
# ============================================================

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

    ".ico": "image/x-icon",

    ".ttf": "font/ttf",

    ".otf": "font/otf",

    ".woff": "font/woff",

    ".woff2": "font/woff2",
}


# ============================================================
# WINDOWS PROCESS TREE HELPERS
#
# Some packaged games (this shows up a lot with Unreal builds)
# are shipped with a small "bootstrapper" .exe at the path you
# actually launch. That bootstrapper checks/install prereqs and
# then spawns the REAL game binary as a CHILD PROCESS, often
# from a different folder and with a different file name
# (e.g. "Binaries\\Win64\\Game-Win64-Shipping.exe").
#
# The original version of this script only looked for windows
# owned by (a) a process whose exe path matched the launched
# exe exactly, or (b) the exact PID returned by Popen(). Both
# checks fail for a bootstrapper/child-process setup, because
# the window actually belongs to a *different* process with a
# *different* exe path and a *different* PID.
#
# Unity builds usually don't have this indirection - the exe
# you launch IS the process that owns the window - which is
# why those already worked.
#
# To fix this generally (regardless of engine or bootstrapper
# behavior) we walk the whole process tree rooted at the PID we
# launched, and match against ANY process in that tree.
# ============================================================

TH32CS_SNAPPROCESS = 0x00000002

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

STILL_ACTIVE = 259


class PROCESSENTRY32(ctypes.Structure):

    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def get_pid_to_parent_map():
    """
    Snapshots every running process on the system and returns
    a dict of {pid: parent_pid}.
    """

    kernel32 = ctypes.windll.kernel32

    mapping = {}


    snapshot = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPPROCESS,
        0
    )


    # INVALID_HANDLE_VALUE
    if snapshot in (0, -1, 0xFFFFFFFFFFFFFFFF):

        return mapping


    try:

        entry = PROCESSENTRY32()

        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)


        has_entry = kernel32.Process32First(
            snapshot,
            ctypes.byref(entry)
        )


        while has_entry:

            mapping[entry.th32ProcessID] = (
                entry.th32ParentProcessID
            )


            has_entry = kernel32.Process32Next(
                snapshot,
                ctypes.byref(entry)
            )


    finally:

        kernel32.CloseHandle(
            snapshot
        )


    return mapping


def get_process_tree_pids(root_pid):
    """
    Returns the set of {root_pid} plus every descendant PID
    (children, grandchildren, etc).

    This is recomputed fresh on every call, so it also picks
    up child processes that are spawned AFTER the initial
    launch (e.g. a bootstrapper that takes a moment before it
    spawns the real game binary).
    """

    pid_to_parent = get_pid_to_parent_map()

    parent_to_children = {}

    for pid, parent_pid in pid_to_parent.items():

        parent_to_children.setdefault(
            parent_pid,
            []
        ).append(pid)


    tree = set()

    queue = [root_pid]


    while queue:

        pid = queue.pop()

        if pid in tree:

            continue


        tree.add(pid)


        for child_pid in parent_to_children.get(pid, []):

            queue.append(child_pid)


    return tree


def is_any_process_alive(pids):
    """
    Returns True if any PID in the given collection still
    refers to a running process.
    """

    kernel32 = ctypes.windll.kernel32


    for pid in pids:

        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            pid
        )


        if not handle:

            continue


        try:

            exit_code = wintypes.DWORD()


            got_code = kernel32.GetExitCodeProcess(
                handle,
                ctypes.byref(exit_code)
            )


            if got_code and exit_code.value == STILL_ACTIVE:

                return True


        finally:

            kernel32.CloseHandle(
                handle
            )


    return False


# ============================================================
# WINDOWS GAME WINDOW HANDLING
# ============================================================

def find_windows_for_pids(pids):
    """
    Finds visible, titled top-level windows owned by any
    process in the given set of PIDs.
    """

    user32 = ctypes.windll.user32

    windows = []


    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_long
    )


    def enum_window_callback(hwnd, lParam):

        if not user32.IsWindowVisible(hwnd):

            return True


        if user32.GetWindowTextLengthW(hwnd) == 0:

            return True


        process_id = ctypes.c_ulong()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(process_id)
        )


        if process_id.value in pids:

            windows.append(hwnd)


        return True


    callback = EnumWindowsProc(
        enum_window_callback
    )


    user32.EnumWindows(
        callback,
        0
    )


    return windows


def find_game_windows(exe_path):
    """
    Finds visible top-level windows belonging to exe_path.

    Kept as a secondary fallback: it matches purely by full
    resolved executable path, independent of the process
    tree. This still helps in edge cases where a game window
    ends up owned by a process that isn't a descendant of the
    one we launched (for example, a launcher that hands off
    to an already-running process via IPC instead of spawning
    a child).
    """

    user32 = ctypes.windll.user32

    kernel32 = ctypes.windll.kernel32

    windows = []


    def get_window_process_path(hwnd):

        process_id = ctypes.c_ulong()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(process_id)
        )

        if process_id.value == 0:

            return None


        process_handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            process_id.value
        )

        if not process_handle:

            return None


        try:

            buffer_size = ctypes.c_ulong(32768)

            buffer = ctypes.create_unicode_buffer(
                buffer_size.value
            )


            success = kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                buffer,
                ctypes.byref(buffer_size)
            )


            if success:

                return buffer.value


        finally:

            kernel32.CloseHandle(
                process_handle
            )


        return None


    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_long
    )


    def enum_window_callback(hwnd, lParam):

        if not user32.IsWindowVisible(hwnd):

            return True


        title_length = (
            user32.GetWindowTextLengthW(hwnd)
        )

        if title_length == 0:

            return True


        window_path = get_window_process_path(
            hwnd
        )


        if window_path:

            try:

                if (
                    Path(window_path).resolve()
                    == exe_path.resolve()
                ):

                    windows.append(hwnd)


            except Exception:

                pass


        return True


    callback = EnumWindowsProc(
        enum_window_callback
    )


    user32.EnumWindows(
        callback,
        0
    )


    return windows


# ============================================================
# FORCE WINDOW TO FOREGROUND
# ============================================================

def force_window_to_front(hwnd):
    """
    Attempts to force a Windows window to the foreground.

    Several Windows APIs are used because Windows normally
    restricts applications from stealing foreground focus.
    """

    user32 = ctypes.windll.user32

    kernel32 = ctypes.windll.kernel32


    # --------------------------------------------------------
    # Window constants
    # --------------------------------------------------------

    SW_RESTORE = 9

    HWND_TOPMOST = -1

    HWND_NOTOPMOST = -2

    SWP_NOSIZE = 0x0001

    SWP_NOMOVE = 0x0002

    SWP_SHOWWINDOW = 0x0040


    # --------------------------------------------------------
    # Restore the window
    # --------------------------------------------------------

    user32.ShowWindow(
        hwnd,
        SW_RESTORE
    )


    # --------------------------------------------------------
    # Get thread IDs
    # --------------------------------------------------------

    game_thread_id = (
        user32.GetWindowThreadProcessId(
            hwnd,
            None
        )
    )


    current_thread_id = (
        kernel32.GetCurrentThreadId()
    )


    foreground_hwnd = (
        user32.GetForegroundWindow()
    )


    foreground_thread_id = 0


    if foreground_hwnd:

        foreground_thread_id = (
            user32.GetWindowThreadProcessId(
                foreground_hwnd,
                None
            )
        )


    # --------------------------------------------------------
    # Attach input queues
    # --------------------------------------------------------

    attached_game = False

    attached_foreground = False


    try:

        if (
            game_thread_id
            and game_thread_id != current_thread_id
        ):

            attached_game = bool(
                user32.AttachThreadInput(
                    current_thread_id,
                    game_thread_id,
                    True
                )
            )


        if (
            foreground_thread_id
            and foreground_thread_id != current_thread_id
            and foreground_thread_id != game_thread_id
        ):

            attached_foreground = bool(
                user32.AttachThreadInput(
                    current_thread_id,
                    foreground_thread_id,
                    True
                )
            )


        # ----------------------------------------------------
        # Make sure the window is restored.
        # ----------------------------------------------------

        user32.ShowWindow(
            hwnd,
            SW_RESTORE
        )


        # ----------------------------------------------------
        # Bring window to top.
        # ----------------------------------------------------

        user32.BringWindowToTop(
            hwnd
        )


        # ----------------------------------------------------
        # Temporarily make the game TOPMOST.
        #
        # This helps the game get in front of Chrome kiosk
        # mode.
        # ----------------------------------------------------

        user32.SetWindowPos(
            hwnd,

            HWND_TOPMOST,

            0,
            0,
            0,
            0,

            SWP_NOMOVE
            | SWP_NOSIZE
            | SWP_SHOWWINDOW
        )


        # ----------------------------------------------------
        # Remove TOPMOST again.
        #
        # The game should remain in front but won't stay
        # permanently "always on top".
        # ----------------------------------------------------

        user32.SetWindowPos(
            hwnd,

            HWND_NOTOPMOST,

            0,
            0,
            0,
            0,

            SWP_NOMOVE
            | SWP_NOSIZE
            | SWP_SHOWWINDOW
        )


        # ----------------------------------------------------
        # Activate the window.
        # ----------------------------------------------------

        user32.SetActiveWindow(
            hwnd
        )


        user32.SetForegroundWindow(
            hwnd
        )


        # ----------------------------------------------------
        # Additional Windows foreground attempt.
        # ----------------------------------------------------

        try:

            user32.SwitchToThisWindow(
                hwnd,
                True
            )

        except Exception:

            pass


        # ----------------------------------------------------
        # Final foreground attempt.
        # ----------------------------------------------------

        user32.BringWindowToTop(
            hwnd
        )


        user32.SetForegroundWindow(
            hwnd
        )


        return True


    finally:

        # ----------------------------------------------------
        # Detach game thread.
        # ----------------------------------------------------

        if attached_game:

            user32.AttachThreadInput(
                current_thread_id,
                game_thread_id,
                False
            )


        # ----------------------------------------------------
        # Detach foreground thread.
        # ----------------------------------------------------

        if attached_foreground:

            user32.AttachThreadInput(
                current_thread_id,
                foreground_thread_id,
                False
            )


# ============================================================
# BRING GAME PROCESS TO FRONT
# ============================================================

def bring_process_to_front(root_pid, exe_path):
    """
    Finds the actual game window and brings it to the front.

    Search order:

        1. Any process in the launched process's full tree
           (the launched process plus all of its descendants,
           recomputed fresh so newly-spawned children are
           picked up). This is the primary fix for
           bootstrapper-style launchers (common in Unreal
           builds) that spawn the real game as a child
           process with a different exe path/PID.

        2. Fallback: match purely by resolved exe path, as
           before, in case the real game window ends up owned
           by a process that isn't a descendant (e.g. handed
           off to an already-running process via IPC).

        3. Fallback: match the original PID directly, as a
           last resort.
    """

    windows = []


    # --------------------------------------------------------
    # 1. Search the whole process tree.
    # --------------------------------------------------------

    try:

        tree_pids = get_process_tree_pids(
            root_pid
        )


        windows = find_windows_for_pids(
            tree_pids
        )


    except Exception as e:

        print(
            "[launcher_server] "
            f"Process tree window search failed: {e}"
        )


    # --------------------------------------------------------
    # 2. Fallback: search by executable path.
    # --------------------------------------------------------

    if not windows:

        try:

            windows = find_game_windows(
                exe_path
            )

        except Exception as e:

            print(
                "[launcher_server] "
                f"Executable window search failed: {e}"
            )


    # --------------------------------------------------------
    # 3. Fallback: search by original PID only.
    # --------------------------------------------------------

    if not windows:

        windows = find_windows_for_pids(
            {root_pid}
        )


    # --------------------------------------------------------
    # No window found.
    # --------------------------------------------------------

    if not windows:

        return False


    # --------------------------------------------------------
    # Try each matching window.
    # --------------------------------------------------------

    for hwnd in windows:

        try:

            print(
                "[launcher_server] "
                f"Found game window: {hwnd}"
            )


            if force_window_to_front(
                hwnd
            ):

                print(
                    "[launcher_server] "
                    "Game window brought to foreground."
                )


                return True


        except Exception as e:

            print(
                "[launcher_server] "
                f"Could not activate window "
                f"{hwnd}: {e}"
            )


    return False


# ============================================================
# WAIT FOR GAME WINDOW
# ============================================================

def wait_for_game_window(process, exe_path):
    """
    Waits for the game window to appear.

    Unity games can take several seconds to initialize, so
    we keep checking for up to 15 seconds.

    Note: we deliberately do NOT stop just because
    `process` (the process we originally launched via
    Popen) has exited. Some packaged games - this is common
    with Unreal builds - use a small bootstrapper exe that
    launches the real game as a child process and then exits
    itself almost immediately. If we bailed out here based on
    `process.poll()`, we'd give up before the real game window
    ever had a chance to appear. Instead we keep polling as
    long as SOMETHING in the process's tree is still alive.
    """

    # --------------------------------------------------------
    # 60 attempts × 0.25 seconds = 15 seconds.
    # --------------------------------------------------------

    for attempt in range(60):


        # ----------------------------------------------------
        # Try to find and activate the window. This also
        # covers child processes spawned by a bootstrapper.
        # ----------------------------------------------------

        if bring_process_to_front(
            process.pid,
            exe_path
        ):

            print(
                "[launcher_server] "
                "Game successfully activated."
            )

            return


        # ----------------------------------------------------
        # Stop if nothing in the process's tree is alive
        # anymore (the launched process AND any children it
        # may have spawned). This replaces the old check that
        # only looked at the original process, which false-
        # positived on bootstrapper-style launchers.
        # ----------------------------------------------------

        tree_pids = get_process_tree_pids(
            process.pid
        )


        if not is_any_process_alive(tree_pids):

            print(
                "[launcher_server] "
                "Game process tree exited before its window "
                "appeared."
            )

            return


        # ----------------------------------------------------
        # Wait before trying again.
        # ----------------------------------------------------

        time.sleep(0.25)


    print(
        "[launcher_server] "
        "Could not find the game window after "
        "15 seconds:"
    )

    print(
        f"    {exe_path}"
    )


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):


    # ========================================================
    # GET
    # ========================================================

    def do_GET(self):

        url_path = (
            urlparse(self.path).path
        )


        # ----------------------------------------------------
        # Root URL -> launcher.html
        # ----------------------------------------------------

        if url_path == "/":

            target = HTML_FILE


        else:

            target = (
                WEB_ROOT
                / url_path.lstrip("/")
            ).resolve()


        # ----------------------------------------------------
        # Check file
        # ----------------------------------------------------

        if (
            not target.exists()
            or not target.is_file()
        ):

            self.send_error(
                404,
                f"Not found: {url_path}"
            )

            return


        # ----------------------------------------------------
        # Content type
        # ----------------------------------------------------

        content_type = CONTENT_TYPES.get(
            target.suffix.lower(),
            "application/octet-stream"
        )


        # ----------------------------------------------------
        # Read file
        # ----------------------------------------------------

        try:

            data = target.read_bytes()

        except Exception as e:

            self.send_error(
                500,
                f"Could not read file: {e}"
            )

            return


        # ----------------------------------------------------
        # Send response
        # ----------------------------------------------------

        self.send_response(
            200
        )


        self.send_header(
            "Content-Type",
            content_type
        )


        self.send_header(
            "Content-Length",
            str(len(data))
        )


        self.end_headers()


        self.wfile.write(
            data
        )


    # ========================================================
    # POST /launch
    # ========================================================

    def do_POST(self):

        if (
            urlparse(self.path).path
            != "/launch"
        ):

            self.send_error(
                404,
                "Not found"
            )

            return


        # ----------------------------------------------------
        # Read request body
        # ----------------------------------------------------

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

        except ValueError:

            length = 0


        body = (
            self.rfile.read(length)
            if length
            else b"{}"
        )


        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        try:

            payload = json.loads(
                body or b"{}"
            )


            exe_arg = payload.get(
                "exe",
                ""
            )


        except Exception:

            self._json_response(
                400,
                {
                    "ok": False,
                    "error": "Invalid request body"
                }
            )

            return


        # ----------------------------------------------------
        # Validate executable path
        # ----------------------------------------------------

        if not exe_arg:

            self._json_response(
                400,
                {
                    "ok": False,
                    "error": "Missing 'exe' path"
                }
            )

            return


        # ----------------------------------------------------
        # Resolve executable path.
        # ----------------------------------------------------

        exe = Path(
            exe_arg
        )


        if not exe.is_absolute():

            exe = (
                BASE_DIR
                / exe
            ).resolve()


        # ----------------------------------------------------
        # Check executable exists.
        # ----------------------------------------------------

        if not exe.exists():

            self._json_response(
                404,
                {
                    "ok": False,
                    "error": (
                        f"Could not find: {exe}"
                    )
                }
            )

            return


        if not exe.is_file():

            self._json_response(
                400,
                {
                    "ok": False,
                    "error": (
                        f"Not a file: {exe}"
                    )
                }
            )

            return


        # ----------------------------------------------------
        # Launch game.
        # ----------------------------------------------------

        try:

            print()

            print(
                "[launcher_server] "
                f"Launching: {exe}"
            )


            process = subprocess.Popen(
                [str(exe)],
                cwd=str(exe.parent)
            )


            print(
                "[launcher_server] "
                f"Game PID: {process.pid}"
            )


        except Exception as e:

            print(
                "[launcher_server] "
                f"Launch failed: {e}"
            )


            self._json_response(
                500,
                {
                    "ok": False,
                    "error": str(e)
                }
            )

            return


        # ----------------------------------------------------
        # Wait for the game window and bring it forward.
        #
        # This runs separately so the HTTP request can
        # immediately return to the browser.
        # ----------------------------------------------------

        threading.Thread(
            target=wait_for_game_window,
            args=(
                process,
                exe
            ),
            daemon=True
        ).start()


        # ----------------------------------------------------
        # Tell browser launch succeeded.
        # ----------------------------------------------------

        self._json_response(
            200,
            {
                "ok": True,
                "pid": process.pid
            }
        )


    # ========================================================
    # JSON RESPONSE
    # ========================================================

    def _json_response(
        self,
        status,
        payload
    ):

        data = json.dumps(
            payload
        ).encode("utf-8")


        self.send_response(
            status
        )


        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )


        self.send_header(
            "Content-Length",
            str(len(data))
        )


        self.end_headers()


        self.wfile.write(
            data
        )


    # ========================================================
    # QUIET REQUEST LOGGING
    # ========================================================

    def log_message(
        self,
        format,
        *args
    ):

        print(
            "[launcher_server] "
            f"{self.address_string()} - "
            f"{format % args}"
        )


# ============================================================
# OPEN CHROME IN KIOSK MODE
# ============================================================

def open_chrome_kiosk(url):
    """
    Opens Google Chrome in kiosk mode.

    Kiosk mode removes:

        - Tabs
        - Address bar
        - Browser toolbar
        - Normal browser UI

    This makes the browser behave like a dedicated
    arcade launcher.
    """


    # --------------------------------------------------------
    # Common Chrome installation locations.
    # --------------------------------------------------------

    chrome_paths = [

        Path(
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        ),

        Path(
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ),

        Path(
            Path.home()
            / r"AppData\Local\Google\Chrome\Application\chrome.exe"
        ),

    ]


    chrome = None


    # --------------------------------------------------------
    # Find Chrome.
    # --------------------------------------------------------

    for path in chrome_paths:

        if path.exists():

            chrome = path

            break


    # --------------------------------------------------------
    # Chrome found.
    # --------------------------------------------------------

    if chrome:

        print(
            "[launcher_server] "
            "Opening Chrome in kiosk mode..."
        )


        subprocess.Popen([

            str(chrome),

            "--kiosk",

            "--no-first-run",

            url

        ])


        return True


    # --------------------------------------------------------
    # Chrome not found.
    # --------------------------------------------------------

    print(
        "[launcher_server] "
        "Could not find Google Chrome."
    )


    print(
        "[launcher_server] "
        "Opening launcher using the default browser instead."
    )


    webbrowser.open(
        url
    )


    return False


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Check launcher.html.
    # --------------------------------------------------------

    if not HTML_FILE.exists():

        print(
            "[launcher_server] "
            "Could not find launcher.html:"
        )


        print(
            f"    {HTML_FILE}"
        )


        print(
            "\nPut launcher_server.py in the same folder "
            "as launcher.html and try again."
        )


        return


    # --------------------------------------------------------
    # Create server.
    # --------------------------------------------------------

    server = ThreadingHTTPServer(
        (
            "127.0.0.1",
            PORT
        ),
        Handler
    )


    url = (
        f"http://127.0.0.1:{PORT}/"
    )


    # --------------------------------------------------------
    # Console information.
    # --------------------------------------------------------

    print()

    print(
        "=" * 60
    )

    print(
        "       INTER ARCADE GAMES LAUNCHER"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Server running at: {url}"
    )

    print()

    print(
        "Chrome will open in kiosk mode."
    )

    print(
        "Games will automatically be brought to the foreground."
    )

    print()

    print(
        "Press Ctrl+C in this window to stop the launcher."
    )

    print()


    # --------------------------------------------------------
    # Open Chrome.
    # --------------------------------------------------------

    open_chrome_kiosk(
        url
    )


    # --------------------------------------------------------
    # Start server.
    # --------------------------------------------------------

    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print()

        print(
            "[launcher_server] "
            "Shutting down..."
        )


        server.shutdown()


        print(
            "[launcher_server] "
            "Launcher stopped."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()