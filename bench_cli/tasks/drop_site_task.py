"""
Drops a Frappe site and removes it from bench.toml.
Invoked as: python -m bench_cli.tasks.drop_site_task <bench_root> <site_name>
"""
import sys
import tomllib
from pathlib import Path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("bench_root")
    parser.add_argument("site_name")
    args = parser.parse_args()

    bench_root = Path(args.bench_root)

    from bench_cli.config.bench_config import BenchConfig
    from bench_cli.core.bench import Bench
    from bench_cli.utils import run_command

    cfg = BenchConfig.from_file(bench_root / "bench.toml")
    bench = Bench(cfg, bench_root)
    bench_bin = str(bench.env_path / "bin" / "bench")
    mariadb = cfg.mariadb

    print(f"Dropping site '{args.site_name}'...")
    sys.stdout.flush()

    cmd = [bench_bin, "frappe", "drop-site", "--force", args.site_name]
    if mariadb.root_password:
        cmd += ["--db-root-password", mariadb.root_password]

    run_command(cmd, cwd=bench.sites_path, stream_output=True)

    bench_toml = bench_root / "bench.toml"
    with bench_toml.open("rb") as fh:
        raw = tomllib.load(fh)
    raw["sites"] = [s for s in raw.get("sites", []) if s.get("name") != args.site_name]

    from bench_cli.utils import write_toml
    write_toml(bench_toml, raw)

    print(f"\nSite '{args.site_name}' dropped and removed from bench.toml.")


if __name__ == "__main__":
    main()
