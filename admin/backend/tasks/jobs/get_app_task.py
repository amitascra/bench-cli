"""
Clones an app repo and pip-installs it into the bench virtualenv.
Invoked as: python -m admin.backend.tasks.jobs.get_app_task <bench_root> <repo> [--branch <branch>]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from bench_cli.config.bench_config import BenchConfig
from bench_cli.core.bench import Bench
from bench_cli.commands.get_app import GetAppCommand


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_root")
    parser.add_argument("repo")
    parser.add_argument("--branch", default="")
    args = parser.parse_args()

    bench_root = Path(args.bench_root)
    bench = Bench(BenchConfig.from_file(bench_root / "bench.toml"), bench_root)
    GetAppCommand(bench, args.repo, args.branch).run()


if __name__ == "__main__":
    main()
