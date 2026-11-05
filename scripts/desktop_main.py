"""Entry point for the standalone desktop build (PyInstaller): the sidecar + a native window."""
import multiprocessing
import os
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if getattr(sys, "frozen", False) and sys.stdout is None:  # windowed build: no console streams
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
    from florist import config
    from florist.desktop import run

    config.load()
    run(int(os.environ.get("FLORIST_PORT") or config.get().port))
