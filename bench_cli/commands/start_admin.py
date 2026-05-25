from __future__ import annotations

import os
import subprocess
import sys
from subprocess import DEVNULL
from typing import TYPE_CHECKING

from bench_cli.exceptions import BenchError

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


def _cli_root():
    import bench_cli as _pkg
    from pathlib import Path
    return Path(_pkg.__file__).parent.parent


class StartAdminCommand:
    def __init__(self, bench: "Bench", port: int | None = None) -> None:
        self.bench = bench
        self.port = port if port is not None else bench.config.admin.port

    @property
    def _pid_file(self):
        return self.bench.pids_path / "admin.pid"

    @property
    def _port_file(self):
        return self.bench.pids_path / "admin.port"

    def _admin_python(self) -> str:
        from bench_cli.managers.admin_env_manager import AdminEnvManager
        mgr = AdminEnvManager(_cli_root())
        mgr.ensure()
        return str(mgr.python)

    def _admin_cmd(self, python: str) -> list[str]:
        return [
            python,
            "-m", "admin.backend.server",
            "--bench-root", str(self.bench.path),
            "--port", str(self.port),
            "--timeout", str(self.bench.config.admin.timeout),
        ]

    def run(self) -> None:
        """Start admin as a background daemon."""
        self._check_not_already_running()
        python = self._admin_python()
        proc = subprocess.Popen(
            self._admin_cmd(python),
            start_new_session=True,
            stdout=DEVNULL,
            stderr=DEVNULL,
            env={**os.environ, "PYTHONPATH": str(_cli_root())},
        )
        self._write_state(proc.pid)
        timeout_minutes = self.bench.config.admin.timeout // 60
        print(f"Admin UI started at http://0.0.0.0:{self.port}/")
        print(f"Will auto-stop after {timeout_minutes} minutes of inactivity.")

    def run_foreground(self, host: str = "127.0.0.1") -> None:
        """Start admin in the foreground (bench admin command)."""
        python = self._admin_python()
        env = {**os.environ, "PYTHONPATH": str(_cli_root())}
        os.execve(python, self._admin_cmd(python) + ["--host", host], env)

    def _check_not_already_running(self) -> None:
        if not self._pid_file.exists():
            return
        pid = int(self._pid_file.read_text().strip())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            self._pid_file.unlink(missing_ok=True)
            self._port_file.unlink(missing_ok=True)
            return
        saved_port = self._port_file.read_text().strip() if self._port_file.exists() else str(self.port)
        raise BenchError(f"Admin is already running on port {saved_port}.")

    def _write_state(self, pid: int) -> None:
        self.bench.pids_path.mkdir(parents=True, exist_ok=True)
        self._pid_file.write_text(str(pid))
        self._port_file.write_text(str(self.port))
