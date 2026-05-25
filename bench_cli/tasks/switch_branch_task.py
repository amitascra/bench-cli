"""
Switches an app to a different git branch, reinstalls it, and rebuilds assets.
Invoked as: python -m bench_cli.tasks.switch_branch_task <bench_root> <app_name> <branch>
"""
import argparse
import subprocess
import sys
import tomllib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_root")
    parser.add_argument("app_name")
    parser.add_argument("branch")
    args = parser.parse_args()

    bench_root = Path(args.bench_root)
    app_path = bench_root / "apps" / args.app_name
    python_bin = str(bench_root / "env" / "bin" / "python")

    from bench_cli.config.bench_config import BenchConfig
    from bench_cli.core.bench import Bench
    from bench_cli.managers.python_env_manager import PythonEnvManager
    cfg = BenchConfig.from_file(bench_root / "bench.toml")
    uv = PythonEnvManager(Bench(cfg, bench_root))._ensure_uv()

    if not (app_path / ".git").exists():
        print(f"Error: '{args.app_name}' is not cloned at {app_path}")
        sys.exit(1)

    print(f"Fetching all remote branches for {args.app_name}...")
    sys.stdout.flush()
    subprocess.run(
        ["git", "-C", str(app_path), "fetch", "origin",
         "+refs/heads/*:refs/remotes/origin/*"],
        check=False,
    )

    subprocess.run(["git", "-C", str(app_path), "merge", "--abort"],
                   capture_output=True, check=False)
    subprocess.run(["git", "-C", str(app_path), "rebase", "--abort"],
                   capture_output=True, check=False)

    stash_result = subprocess.run(
        ["git", "-C", str(app_path), "stash", "--include-untracked"],
        capture_output=True, text=True, check=False,
    )
    stashed = "No local changes" not in stash_result.stdout

    print(f"Switching to branch '{args.branch}'...")
    sys.stdout.flush()

    result = subprocess.run(
        ["git", "-C", str(app_path), "checkout", "-B", args.branch,
         f"origin/{args.branch}"],
        check=False,
    )
    if result.returncode != 0:
        if stashed:
            subprocess.run(["git", "-C", str(app_path), "stash", "pop"], check=False)
        print(f"Error: could not switch to branch '{args.branch}'")
        sys.exit(result.returncode)

    print(f"Reinstalling {args.app_name}...")
    sys.stdout.flush()
    subprocess.run([uv, "pip", "install", "--python", python_bin, "-e", str(app_path)], check=False)

    # Update bench.toml to reflect the new active branch
    bench_toml = bench_root / "bench.toml"
    with bench_toml.open("rb") as fh:
        raw = tomllib.load(fh)
    for app_entry in raw.get("apps", []):
        if app_entry.get("name") == args.app_name:
            app_entry["branch"] = args.branch
            break
    from bench_cli.utils import write_toml
    write_toml(bench_toml, raw)
    print(f"Updated bench.toml: {args.app_name} -> {args.branch}")
    sys.stdout.flush()

    from bench_cli.tasks.build_assets import build_app_assets
    build_app_assets(bench_root, args.app_name)

    print(f"\n'{args.app_name}' switched to '{args.branch}' successfully.")


if __name__ == "__main__":
    main()
