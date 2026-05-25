from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessInfo:
    name: str
    status: str  # 'running' | 'stopped' | 'unknown'
    pid: int | None
    uptime: str | None
    log_file: Path


class ProcessReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def read_all(self) -> list[ProcessInfo]:
        pids_dir = self._bench_root / "pids"
        if not pids_dir.exists():
            return []

        processes = []
        for pid_file in sorted(pids_dir.glob("*.pid")):
            name = pid_file.stem
            processes.append(self._read_process(name, pid_file))
        return processes

    def _read_process(self, name: str, pid_file: Path) -> ProcessInfo:
        log_file = self._bench_root / "logs" / f"{name}.log"
        try:
            pid = int(pid_file.read_text().strip())
        except (ValueError, OSError):
            return ProcessInfo(name=name, status="unknown", pid=None, uptime=None, log_file=log_file)

        try:
            os.kill(pid, 0)
            status = "running"
        except OSError:
            status = "stopped"

        return ProcessInfo(name=name, status=status, pid=pid, uptime=None, log_file=log_file)
