from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class AdminEnvManager:
    """
    Manages an isolated venv at <cli_root>/.admin-venv/ that contains Flask.
    Created on first use; subsequent calls are instant (venv already exists).
    """

    def __init__(self, cli_root: Path) -> None:
        self.venv_path = cli_root / ".admin-venv"

    @property
    def python(self) -> Path:
        return self.venv_path / "bin" / "python"

    def ensure(self) -> None:
        """Create the admin venv and install flask if not already done."""
        if self.python.exists():
            return
        print("Setting up admin environment (one-time)...")
        print("  Creating virtual environment...", end=" ", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], check=True)
        print("done")
        print("  Installing flask...", end=" ", flush=True)
        pip = self.venv_path / "bin" / "pip"
        subprocess.run(
            [str(pip), "install", "--quiet", "flask>=3.0"],
            check=True,
        )
        print("done")
