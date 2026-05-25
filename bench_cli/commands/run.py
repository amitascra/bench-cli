from __future__ import annotations

from bench_cli.core.bench import Bench
from bench_cli.exceptions import BenchError
from bench_cli.managers.process_manager import ProcessManagerFactory


class RunCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        process_manager = ProcessManagerFactory.create(self.bench)
        procfile = process_manager.procfile_path
        if not procfile.exists():
            raise BenchError(
                f"Procfile not found at {procfile}. "
                "Run 'bench init' first to initialise the bench."
            )
        process_manager.start()
