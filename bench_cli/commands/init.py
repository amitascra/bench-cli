from __future__ import annotations

from bench_cli.core.bench import Bench
from bench_cli.managers.python_env_manager import PythonEnvManager
from bench_cli.managers.redis_manager import RedisManager
from bench_cli.managers.process_manager import ProcessManagerFactory


class InitCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        self._step(1, "Validate bench.toml")
        self.bench.config.validate()

        self._step(2, "Install system packages")
        self._install_system_packages()

        self._step(3, "Create bench directory structure")
        self.bench.create_directories()
        self.bench.write_common_site_config()

        self._step(4, "Create Python virtualenv")
        python_env_manager = PythonEnvManager(self.bench)
        python_env_manager.ensure_python()
        python_env_manager.create_venv()
        python_env_manager.generate_bench_script()

        self._step(5, "Clone and install framework app")
        for app in self.bench.init_apps():
            if not app.is_cloned:
                print(f"  Cloning {app.config.name}...")
                app.clone()
            print(f"  Installing {app.config.name}...")
            python_env_manager.install_app(app)
        self.bench.write_apps_txt()

        self._step(6, "Install Node.js")
        python_env_manager.install_node()

        self._step(7, "Install Node.js dependencies")
        python_env_manager.install_node_dependencies()

        self._step(8, "Configure Redis")
        RedisManager(self.bench.config.redis, self.bench).generate_configs()

        self._step(9, "Generate Procfile")
        ProcessManagerFactory.create(self.bench).generate_config()

        print("\nBench initialised. Next steps:")
        print("  bench new-site site1.localhost   # create your first site")
        print("  bench start                      # start all processes")

    def _step(self, number: int, description: str) -> None:
        print(f"[{number}/9] {description}...", flush=True)

    def _install_system_packages(self) -> None:
        from bench_cli.managers.mariadb_manager import MariaDBManager
        from bench_cli.platform import get_package_manager, is_linux
        mariadb_manager = MariaDBManager(self.bench.config.mariadb)
        mariadb_manager.install()
        mariadb_manager.start()
        RedisManager(self.bench.config.redis, self.bench).install()
        if is_linux():
            pkg = get_package_manager()
            pkg.install("build-essential", "pkg-config", "libmariadb-dev", "git")
        PythonEnvManager(self.bench).ensure_python()
