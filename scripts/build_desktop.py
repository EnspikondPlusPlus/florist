"""Build a standalone Florist desktop app with PyInstaller.

    cd app && pnpm build && cd ..
    uv run python scripts/build_desktop.py          # → dist/Florist/Florist.exe (Windows) or dist/Florist.app (macOS)

The result bundles Python, the sidecar, pywebview and the built UI. User data still lives in ~/.florist.
"""
import os
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
SEP = ";" if os.name == "nt" else ":"
if not (ROOT / "app" / "dist" / "index.html").exists():
    sys.exit("Build the UI first: cd app && pnpm install && pnpm build")

data = ["skills", "schemas", "adapters", "docs", "app/dist", "app/public", "florist/store/migrations",
        "README.md", "ASSUMPTIONS.md", "SKILL.md", "PLAYBOOK.md", "LICENSE"]
args = [str(ROOT / "scripts" / "desktop_main.py"), "--name", "Florist", "--windowed", "--onedir", "--noconfirm",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
        "--icon", str(ROOT / "app" / "public" / ("florist-icon.ico" if os.name == "nt" else "florist-icon.png")),
        "--collect-submodules", "florist", "--collect-submodules", "uvicorn", "--collect-all", "webview",
        "--collect-all", "litellm", "--collect-data", "tiktoken_ext", "--hidden-import", "tiktoken_ext.openai_public",
        "--exclude-module", "pytest", "--exclude-module", "tkinter"]
for d in data:
    src = ROOT / d
    if src.exists():
        dest = d if src.is_dir() else "."
        args += ["--add-data", f"{src}{SEP}{dest}"]
PyInstaller.__main__.run(args)
print("\nBuilt:", ROOT / "dist" / "Florist")
