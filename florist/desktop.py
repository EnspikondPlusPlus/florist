"""Desktop shell: the sidecar in a background thread + a native window.

pywebview (WebView2 on Windows, WKWebView on macOS, GTK/Qt on Linux) when installed
(``uv sync --extra desktop``); otherwise a chromeless Edge/Chrome ``--app`` window; otherwise the
default browser.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

from . import paths


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _serve(port: int) -> None:
    import uvicorn

    from .server import app  # import the object (not a string) so frozen builds work

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", log_config=None)


def _app_browser() -> str | None:
    cands = ["msedge", "chrome", "google-chrome", "chromium", "chromium-browser"]
    if os.name == "nt":
        pf = [os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""),
              os.environ.get("LOCALAPPDATA", "")]
        for base in pf:
            for rel in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                p = Path(base) / rel
                if base and p.exists():
                    return str(p)
    for c in cands:
        if shutil.which(c):
            return shutil.which(c)
    return None


def run(port: int) -> None:
    if not _port_open(port):
        threading.Thread(target=_serve, args=(port,), daemon=True).start()
        for _ in range(100):
            if _port_open(port):
                break
            time.sleep(0.1)
    url = f"http://127.0.0.1:{port}"
    # WinForms (System.Drawing.Icon) only accepts .ico; GTK/Qt/Cocoa take the PNG.
    icon = paths.RESOURCES / "app" / "public" / ("florist-icon.ico" if os.name == "nt" else "florist-icon.png")
    try:
        import webview  # pywebview

        webview.create_window("Florist", url, width=1440, height=920, min_size=(960, 640))
        webview.start(icon=str(icon) if icon.exists() else None)
        return
    except ImportError:
        pass
    except Exception as e:  # missing WebView2 runtime, no GUI backend, ...
        print(f"pywebview unavailable ({e}); falling back to an app window")
    browser = _app_browser()
    if browser:
        profile_dir = paths.sub("browser-profile")
        proc = subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={profile_dir}", "--window-size=1440,920"])
        proc.wait()
    else:
        webbrowser.open(url)
        print(f"Florist is running at {url} — Ctrl+C to quit")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
