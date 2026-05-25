from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


@dataclass
class ProcessDefinition:
    name: str
    command: str
    log_file: Path


class ProcessManager(ABC):
    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    @abstractmethod
    def generate_config(self) -> None:
        """Write the process manager config file(s) to bench.config_path."""

    @abstractmethod
    def start(self) -> None:
        """Start all bench processes."""

    @abstractmethod
    def stop(self) -> None:
        """Stop all bench processes."""

    @abstractmethod
    def is_running(self) -> bool:
        """Return True if any managed process is currently running."""

    def _process_definitions(self) -> List[ProcessDefinition]:
        definitions = [
            self._web_definition(),
            self._socketio_definition(),
            *self._worker_definitions("default", self.bench.config.workers.default_count),
            *self._worker_definitions("short", self.bench.config.workers.short_count),
            *self._worker_definitions("long", self.bench.config.workers.long_count),
        ]
        if self.bench.config.redis.is_single_instance:
            definitions.append(self._redis_definition("redis", "redis.conf"))
        else:
            definitions.append(self._redis_definition("redis_cache", "redis_cache.conf"))
            definitions.append(self._redis_definition("redis_queue", "redis_queue.conf"))
            definitions.append(self._redis_definition("redis_socketio", "redis_socketio.conf"))
        return definitions

    def _web_definition(self) -> ProcessDefinition:
        port = self.bench.config.http_port
        sites = self.bench.sites_path
        bench_bin = self.bench.env_path / "bin" / "bench"
        return ProcessDefinition(
            name="web",
            command=f"cd {sites} && {bench_bin} frappe serve --port {port} --noreload",
            log_file=self.bench.logs_path / "web.log",
        )

    def _socketio_definition(self) -> ProcessDefinition:
        sites = self.bench.sites_path
        return ProcessDefinition(
            name="socketio",
            command=f"cd {sites} && node {self.bench.apps_path}/frappe/socketio.js",
            log_file=self.bench.logs_path / "socketio.log",
        )

    def _worker_definitions(self, queue: str, count: int) -> List[ProcessDefinition]:
        sites = self.bench.sites_path
        return [
            ProcessDefinition(
                name=f"worker_{queue}_{i}",
                command=f"cd {sites} && {self.bench.env_path}/bin/bench frappe worker --queue {queue}",
                log_file=self.bench.logs_path / f"worker_{queue}_{i}.log",
            )
            for i in range(1, count + 1)
        ]

    def _redis_definition(self, name: str, config_filename: str) -> ProcessDefinition:
        return ProcessDefinition(
            name=name,
            command=f"redis-server {self.bench.config_path}/{config_filename}",
            log_file=self.bench.logs_path / f"{name}.log",
        )


class ProcessManagerFactory:
    @staticmethod
    def create(bench: "Bench") -> ProcessManager:
        from bench_cli.managers.honcho_process_manager import HonchoProcessManager
        return HonchoProcessManager(bench)
