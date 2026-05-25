from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppInfo:
    name: str
    repo: str
    branch: str
    branches: list
    is_cloned: bool
    current_commit: str
    commit_message: str
    uncommitted_changes: bool
    installed_version: str


class AppReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def read_all(self) -> list[AppInfo]:
        apps_path = self._bench_root / "apps"
        if not apps_path.is_dir():
            return []
        return [
            self._read_app(d.name)
            for d in sorted(apps_path.iterdir())
            if d.is_dir() and (d / ".git").exists()
        ]

    def read_one(self, app_name: str) -> AppInfo:
        return self._read_app(app_name)

    def _read_app(self, name: str) -> AppInfo:
        app_path = self._bench_root / "apps" / name
        is_cloned = (app_path / ".git").exists()

        if not is_cloned:
            return AppInfo(
                name=name,
                repo="",
                branch="",
                branches=[],
                is_cloned=False,
                current_commit="",
                commit_message="",
                uncommitted_changes=False,
                installed_version=self._pip_version(name),
            )

        return AppInfo(
            name=name,
            repo=self._git_remote(app_path),
            branch=self._git_branch(app_path),
            branches=[],
            is_cloned=True,
            current_commit=self._git_short_sha(app_path),
            commit_message=self._git_commit_message(app_path),
            uncommitted_changes=self._git_is_dirty(app_path),
            installed_version=self._pip_version(name),
        )

    def _git_remote(self, path: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True, text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_branch(self, path: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), "branch", "--show-current"],
            capture_output=True, text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_short_sha(self, path: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_commit_message(self, path: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_is_dirty(self, path: Path) -> bool:
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip()) if result.returncode == 0 else False

    def _pip_version(self, name: str) -> str:
        uv = shutil.which("uv")
        if not uv:
            return ""
        python_bin = str(self._bench_root / "env" / "bin" / "python")
        result = subprocess.run(
            [uv, "pip", "show", "--python", python_bin, name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ""
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        return ""
