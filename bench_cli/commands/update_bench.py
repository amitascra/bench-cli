from __future__ import annotations

from pathlib import Path

from bench_cli.exceptions import BenchError
from bench_cli.utils import run_command


class UpdateBenchCliCommand:
    def run(self) -> None:
        source = self._find_source()
        print(f"Pulling latest bench-cli from {source}...")
        run_command(["git", "-C", str(source), "pull"], stream_output=True)
        print("\nbench-cli updated successfully.")

    def _find_source(self) -> Path:
        import bench_cli as _pkg
        pkg_root = Path(_pkg.__file__).parent.parent
        if (pkg_root / ".git").exists():
            return pkg_root
        raise BenchError(
            "Cannot find the bench-cli git repository. "
            "Make sure you are running bench-cli from a git clone."
        )
