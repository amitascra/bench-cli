from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.exceptions import BenchError
from bench_cli.managers.process_manager import ProcessManager

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class HonchoProcessManager(ProcessManager):
    def __init__(self, bench: "Bench") -> None:
        super().__init__(bench)
        self._procs: dict[str, subprocess.Popen] = {}
        self._stopping = False

    @property
    def procfile_path(self) -> Path:
        return self.bench.config_path / "Procfile"

    @property
    def pid_file(self) -> Path:
        return self.bench.pids_path / "bench.pid"

    def generate_config(self) -> None:
        lines = [
            f"{pd.name}: {pd.command}\n"
            for pd in self._process_definitions()
        ]
        self.procfile_path.write_text("".join(lines))

    def start(self) -> None:
        self.pid_file.write_text(str(os.getpid()))
        try:
            self._run_procfile()
        finally:
            self.pid_file.unlink(missing_ok=True)
            self._cleanup_proc_pid_files()

    def stop(self) -> None:
        if not self.pid_file.exists():
            raise BenchError("Bench is not running (no PID file found at pids/bench.pid).")
        pid = int(self.pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self.pid_file.unlink(missing_ok=True)
            raise BenchError(f"Process {pid} is not running. Removed stale PID file.")

    def is_running(self) -> bool:
        process_names = [pd.name for pd in self._process_definitions()]
        pattern = "|".join(process_names)
        result = subprocess.run(["pgrep", "-f", pattern], capture_output=True)
        return bool(result.stdout.strip())

    # ------------------------------------------------------------------ #
    # Procfile runner (stdlib replacement for honcho)                      #
    # ------------------------------------------------------------------ #

    def _run_procfile(self) -> None:
        entries = self._parse_procfile()

        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        def _stop(signum, frame):
            self._stopping = True
            self._stop_all()

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)

        for name, command in entries:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )
            self._procs[name] = proc
            (self.bench.pids_path / f"{name}.pid").write_text(str(proc.pid))
            t = threading.Thread(target=self._stream, args=(name, proc), daemon=True)
            t.start()

        while not self._stopping:
            for name, proc in list(self._procs.items()):
                if proc.poll() is not None:
                    print(f"[{name}] exited with code {proc.returncode}", file=sys.stderr)
                    self._stopping = True
                    break
            if not self._stopping:
                time.sleep(0.5)

        self._stop_all()

        signal.signal(signal.SIGTERM, original_sigterm)
        signal.signal(signal.SIGINT, original_sigint)

    def _parse_procfile(self) -> list[tuple[str, str]]:
        entries = []
        for line in self.procfile_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, _, command = line.partition(":")
            entries.append((name.strip(), command.strip()))
        return entries

    def _stream(self, name: str, proc: subprocess.Popen) -> None:
        prefix = f"[{name}] "
        assert proc.stdout is not None
        for raw in proc.stdout:
            sys.stdout.write(prefix + raw.decode(errors="replace"))
            sys.stdout.flush()

    def _cleanup_proc_pid_files(self) -> None:
        for name in self._procs:
            (self.bench.pids_path / f"{name}.pid").unlink(missing_ok=True)

    def _stop_all(self) -> None:
        for name, proc in self._procs.items():
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        for proc in self._procs.values():
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
