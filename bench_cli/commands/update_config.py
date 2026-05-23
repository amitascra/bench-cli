from __future__ import annotations

import click

from bench_cli.core.bench import Bench
from bench_cli.managers.nginx_manager import NginxManager
from bench_cli.managers.process_manager import ProcessManagerFactory
from bench_cli.managers.redis_manager import RedisManager


class UpdateConfigCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        self._update_redis()
        self._update_process_manager()
        self._update_common_site_config()
        self._update_nginx()

    def _update_redis(self) -> None:
        click.echo("Updating Redis configs...")
        RedisManager(self.bench.config.redis, self.bench).generate_configs()

    def _update_process_manager(self) -> None:
        click.echo("Updating process manager config...")
        ProcessManagerFactory.create(self.bench).generate_config()

    def _update_common_site_config(self) -> None:
        click.echo("Updating common_site_config.json...")
        self.bench.write_common_site_config()

    def _update_nginx(self) -> None:
        if not self.bench.config.nginx.enabled:
            return
        click.echo("Updating nginx configs...")
        NginxManager(self.bench).generate_config()
        click.echo("  Note: run 'bench setup nginx' to reload nginx with the new config.")
