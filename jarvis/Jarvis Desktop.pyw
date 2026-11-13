"""Double-click to open the desktop application."""
import os
from pathlib import Path
import subprocess
import sys


runtime = Path(os.environ["LOCALAPPDATA"]) / "Jarvis" / "desktop-venv" / "Scripts" / "pythonw.exe"
if Path(sys.executable).resolve() != runtime.resolve():
    if not runtime.is_file():
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, "Install the Jarvis Desktop requirements into the desktop virtual environment.",
            "Jarvis Desktop", 0x10,
        )
        sys.exit(1)
    subprocess.Popen([str(runtime), "-B", str(Path(__file__).resolve())])
else:
    from desktop.window import run
    sys.exit(run())

