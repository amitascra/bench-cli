"""
Runs `bench update` which pulls all apps, reinstalls, and migrates all sites.
Invoked as: python -m admin.backend.tasks.jobs.update_task <bench_root>
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_root")
    args = parser.parse_args()

    bench_root = Path(args.bench_root)
    bench_bin = str(bench_root / "env" / "bin" / "bench")

    result = subprocess.run([bench_bin, "update"], cwd=str(bench_root))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
