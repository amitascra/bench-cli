# Commands Specification

---

## `bench new`

Scaffolds a starter `bench.yml` in the current directory.

**Pre-conditions:** No `bench.yml` exists in the current directory.

**Steps:**
1. Check that no `bench.yml` exists. If one exists, print an error and exit.
2. Write a minimal `bench.yml` with placeholder values to the current directory.
3. Print a message telling the user to edit the file and then run `bench init`.

**Does not** touch the filesystem beyond writing `bench.yml`.

---

## `bench init`

Installs and configures the entire environment described in `bench.yml`. Safe to re-run — each step checks whether it has already been done.

### Pre-conditions

- `bench.yml` exists and is valid.
- **Ubuntu:** The process has `sudo` access (required for `apt-get`).
- **macOS:** Homebrew is installed (`brew` is in `$PATH`). No `sudo` required — Homebrew installs to user-owned directories.

### Steps

```
1.  Validate bench.yml
2.  Install system packages
3.  Create bench directory structure
4.  Create Python virtualenv
5.  Clone apps
6.  Install Python dependencies
7.  Install Node.js
8.  Configure Redis
9.  Create sites
10. Install apps on sites
11. Generate Procfile
```

#### Step 1 — Validate bench.yml

`BenchConfig.from_file('bench.yml')` runs all validation rules. On failure, print the error and exit with code 1. No filesystem changes have occurred at this point.

#### Step 2 — Install system packages

`MariaDBManager.install()` and `RedisManager.install()` each check `is_installed()` first and skip if already present. The package manager is selected by `get_package_manager()` from `bench_cli.platform`.

**Ubuntu (apt):**
- `mariadb-server`
- `redis-server`
- `python3-<version>` and `python3-<version>-venv` (from deadsnakes PPA if needed)
- `git`

**macOS (Homebrew):**
- `mariadb`
- `redis`
- `python@<version>` (if the requested version is not already available)
- `git` (usually pre-installed via Xcode CLT)

`libmysqlclient-dev` is **not** needed on either platform — bench uses `PyMySQL`, which is pure Python and requires no C extension.

After installation, `MariaDBManager.start()` ensures the MariaDB service is running:
- Ubuntu: `systemctl start mariadb`
- macOS: `brew services start mariadb`

#### Step 3 — Create bench directory structure

`Bench.create_directories()` creates:
- `apps/`
- `sites/`
- `sites/assets/`
- `logs/`
- `config/`
- `pids/`

All created with `exist_ok=True`.

#### Step 4 — Create Python virtualenv

`PythonEnvManager.create_venv()` runs:
```
python3.<version> -m venv env/
```
Skipped if `env/bin/python` already exists.

#### Step 5 — Clone apps

For each `AppConfig` in order:
- Skip if `App.is_cloned` is already `True`.
- `App.clone()` runs:
  ```
  git clone <repo> --branch <branch> --depth 1 apps/<name>
  ```

#### Step 6 — Install Python dependencies

For each `App` in order:
- `PythonEnvManager.install_app(app)` runs:
  ```
  uv pip install -e apps/<name>
  ```
- This installs the app and all its `requirements.txt` dependencies. `uv` is used instead of pip for speed.

#### Step 7 — Install Node.js

`PythonEnvManager.install_node()` checks if `node` is present. If not, installs Node.js 24 via the NodeSource setup script.

Yarn is installed globally afterward: `npm install -g yarn`.

#### Step 8 — Configure Redis

`RedisManager.generate_configs()` writes config files to `config/`. The output depends on whether single-instance or multi-instance mode is used.

**Single-instance mode** (`redis.port` is set) — one file:

**`redis.conf`**
```
port 13000
bind 127.0.0.1
```

**Multi-instance mode** (`cache_port`/`queue_port`/`socketio_port`) — three files:

**`redis_cache.conf`** / **`redis_queue.conf`** / **`redis_socketio.conf`**
```
port <N>
bind 127.0.0.1
```

Existing files are overwritten.

#### Step 9 — Create sites

For each `SiteConfig`, if `Site.exists` is `False`:
- `Site.create(mariadb_config)` runs the framework app's `new-site` command:
  ```
  env/bin/bench new-site <site.name>
      --mariadb-root-password <root_password>
      --admin-password <site.admin_password>
      --no-mariadb-socket
  ```

frappe generates and manages the database name and credentials internally; they are written into `sites/<name>/site_config.json`. Do not pass `--db-name` or `--db-password`.

Skipped if the site directory already contains `site_config.json`.

#### Step 10 — Install apps on sites

For each `SiteConfig`, for each app in `site.apps` (in order):
- `Site.install_app(app_name)` runs:
  ```
  env/bin/bench --site <site.name> install-app <app_name>
  ```
- `frappe` is always already installed by `new-site`; skip it to avoid a harmless but confusing error.

#### Step 11 — Generate process manager config

`ProcessManagerFactory.create(bench)` returns the right manager based on `bench.config.process_manager`, then `generate_config()` is called.

**When `process_manager: honcho`** — writes `config/Procfile`.

Single-instance Redis (`redis.port`):
```
web: bench frappe serve --port 8000 --noreload
socketio: node apps/frappe/socketio.js
worker_default_1: env/bin/bench worker --queue default
worker_default_2: env/bin/bench worker --queue default
worker_short_1: env/bin/bench worker --queue short
worker_long_1: env/bin/bench worker --queue long
redis: redis-server config/redis.conf
admin: python -m bench_cli.admin.server --bench-root . --port 8002 --no-timeout
```

Multi-instance Redis (`cache_port`/`queue_port`/`socketio_port`):
```
...
redis_cache: redis-server config/redis_cache.conf
redis_queue: redis-server config/redis_queue.conf
redis_socketio: redis-server config/redis_socketio.conf
admin: python -m bench_cli.admin.server --bench-root . --port 8002 --no-timeout
```

The `admin` process is always included. It serves a "Admin is off" page by default; set `admin.enabled: true` in `bench.yml` to activate the full UI without restarting.

**When `process_manager: supervisor`** — writes `config/supervisor.conf` with one `[program:X]` section per process (see architecture.md for the full template). This step does **not** start supervisord; that is done by `bench run`.

---

## `bench run`

Starts all bench processes using whichever process manager is configured.

### Pre-conditions

- `bench init` has been run at least once (the process manager config file exists).
- MariaDB service is running on the host.

### Steps

```
1.  Validate bench.yml
2.  Check process manager config exists
3.  Start processes
```

#### Step 1 — Validate bench.yml

Same as in `bench init`. Exit on error.

#### Step 2 — Check config exists

`ProcessManagerFactory.create(bench)` selects the manager. If the expected config file is missing (`config/Procfile` for honcho, `config/supervisor.conf` for supervisor), print a message telling the user to run `bench init` first and exit with code 1.

#### Step 3 — Start processes

**With honcho (`process_manager: honcho`)**

`HonchoProcessManager.start()` invokes honcho programmatically (via its Python API, not subprocess) with `config/Procfile` as input.

- All process output is multiplexed to stdout with a `<process-name> |` prefix.
- Each process also writes its output to `logs/<process-name>.log`.
- `bench run` **blocks** — it stays in the foreground until the user sends `SIGINT` (Ctrl-C).
- On `SIGINT`, honcho sends `SIGTERM` to all child processes and waits up to 5 seconds before sending `SIGKILL`.

**With supervisor (`process_manager: supervisor`)**

`SupervisorProcessManager.start()` sets the `BENCH_ROOT` environment variable to the bench root path, then:

- If supervisord is **not** running: `supervisord -c config/supervisor.conf`
- If supervisord **is** running (socket exists and responds): `supervisorctl -c config/supervisor.conf reload`

`bench run` **exits immediately** after this. Supervisord runs as a background daemon; process output goes to the per-process log files under `logs/`.

To inspect running processes: `supervisorctl -c config/supervisor.conf status`

To stop all processes: `supervisorctl -c config/supervisor.conf shutdown`

---

## `bench build`

Builds JavaScript and CSS assets for all installed apps.

### Pre-conditions

- `bench init` has been run (apps are cloned, Node.js is installed, virtualenv exists).

### Steps

```
1.  Validate bench.yml
2.  For each app, build assets
3.  Copy built assets to sites/assets/
```

#### Step 2 — Per-app asset build

`App.build_assets()` checks whether the app has a `package.json` at its root.

- If yes: `yarn --cwd apps/<name> build` (or the build script defined in `package.json`).
- If no: skip silently.

#### Step 3 — Copy to sites/assets/

After all per-app builds complete, run the framework app's asset collection command:
```
env/bin/bench build --make-copy
```
This collects all built assets into `sites/assets/`.

---

## `bench update`

Pulls the latest commits for all apps, reinstalls Python packages, and migrates all sites.

### Pre-conditions

- `bench init` has been run.
- All processes are stopped (warn the user if any Procfile processes are detected running).

### Steps

```
1.  Validate bench.yml
2.  Warn if processes are running
3.  For each app: git pull
4.  For each app: uv pip install -e
5.  For each site: bench migrate
```

#### Step 2 — Warn if processes are running

Call `ProcessManagerFactory.create(bench).is_running()`. If it returns `True`, print a warning (not an error) and ask the user to confirm before continuing. In non-interactive mode (`--yes` flag), skip the prompt and proceed.

#### Step 3 — git pull for each app

`App.update()` runs:
```
git -C apps/<name> fetch origin
git -C apps/<name> merge --ff-only origin/<branch>
```

Fast-forward only. If a merge conflict would occur, print an error for that app and skip it (continue with remaining apps).

#### Step 4 — uv pip install -e for each app

`PythonEnvManager.install_app(app)` re-runs `uv pip install -e apps/<name>` to pick up any new Python dependencies added to the app since the last update.

#### Step 5 — bench migrate for each site

`Site.migrate()` runs:
```
env/bin/bench --site <site.name> migrate
```

Runs in order for each site. If migration fails on one site, print the error and continue with remaining sites. Exit with a non-zero code at the end if any migration failed.

---

## `bench update-config`

Regenerates all derived config files from `bench.yml` without running a full `bench init`. Use this after editing `bench.yml` to update ports, worker counts, redis settings, or nginx config.

**Files regenerated:**
- `config/redis.conf` (single-instance) or `config/redis_cache.conf`, `config/redis_queue.conf`, `config/redis_socketio.conf` (multi-instance)
- `config/Procfile` (honcho) or `config/supervisor.conf` (supervisor)
- `sites/common_site_config.json`
- `config/nginx/*.conf` — only if `nginx.enabled: true`

**Does not:** restart processes, reload nginx, or touch apps/sites. Run `bench start` after to pick up process changes. Run `bench setup nginx` to reload nginx.

---

## `bench start-admin`

Starts the admin web interface as a standalone background daemon, independently of the Procfile.

```bash
bench start-admin              # default port 8002
bench start-admin --port 9000  # custom port
```

**Steps:**
1. Check `pids/admin.pid` — if the process is already alive, print its URL and exit.
2. Spawn `bench_cli.admin.server` as a detached subprocess (`start_new_session=True`).
3. Write `pids/admin.pid` and `pids/admin.port`.
4. Print the admin URL.

The admin server includes a watchdog that sends `SIGTERM` to itself after the configured inactivity timeout. Use `bench stop-admin` to stop it immediately.

> **Note:** When using `bench start` (honcho/supervisor), the admin process is already included in the Procfile and starts automatically — `bench start-admin` is only needed when running the admin independently of the full bench.

---

## `bench stop-admin`

Stops the background admin daemon.

**Steps:**
1. Read `pids/admin.pid`. If it does not exist, print "Admin is not running." and exit.
2. Send `SIGTERM` to the process.
3. Remove `pids/admin.pid` and `pids/admin.port`.

Handles stale PID files gracefully — if the process has already exited (e.g. after the inactivity timeout), it still cleans up the state files.

---

## `bench admin`

Starts the admin web interface in the **foreground** (development use). Press `Ctrl-C` to stop.

```bash
bench admin                    # default port 8001
bench admin --port 9000        # custom port
bench admin --host 0.0.0.0     # expose to the network
```

See [docs/admin.md](admin.md) for the full interface specification.

---

## `bench setup nginx`

See [docs/production.md](production.md) for the full step-by-step.

**Summary:** Installs nginx if absent, generates per-site config files into `config/nginx/`, symlinks `include.conf` into `nginx.config_dir`, validates with `nginx -t`, and reloads nginx.

Pre-conditions: `nginx.enabled: true`, `bench init` has been run, process has `sudo` (Ubuntu) or Homebrew (macOS).

> **macOS note:** This command works on macOS with Homebrew nginx for local testing, but its primary use case is production deployment on Ubuntu/Linux servers. The `config_dir` default (`/etc/nginx/conf.d`) does not exist on macOS — set it to `/opt/homebrew/etc/nginx/servers/` (Apple Silicon) or `/usr/local/etc/nginx/servers/` (Intel) in `bench.yml`.

---

## `bench setup letsencrypt`

See [docs/production.md](production.md) for the full step-by-step.

**Summary:** Installs certbot if absent, ensures the webroot directory exists, runs `certbot certonly --webroot` for each `ssl: true` site (with all domains as `-d` arguments), then regenerates nginx config with HTTPS blocks and reloads nginx.

Pre-conditions: `bench setup nginx` has run, nginx is serving port 80, DNS records for all SSL sites point to this server.

> **macOS note:** Let's Encrypt certificates require a publicly reachable server with real DNS records. This command is intended for Ubuntu/Linux production servers only. Do not run it on a local macOS development machine.

---

## `bench setup production`

See [docs/production.md](production.md) for the full step-by-step.

**Summary:** Validates that `process_manager` is `supervisor`, writes `dns_multitenant: 1` to `sites/common_site_config.json`, sets up supervisor, then runs `bench setup nginx` and `bench setup letsencrypt` in sequence.

> **macOS note:** Production setup targets Ubuntu/Linux servers. On macOS, use `bench run` (honcho) for development. Running `bench setup production` on macOS will print an error and exit.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Configuration error or expected failure (printed to stderr) |
| `2` | Unexpected error (printed with traceback if `--verbose`) |

---

## Common flags

All commands accept:

| Flag | Description |
|------|-------------|
| `--bench-dir PATH` | Override the directory containing `bench.yml`. Default: search upward from `$CWD`. |
| `--verbose` | Print full tracebacks on error and all subprocess output. |
| `--yes` | Skip confirmation prompts (useful in CI). |
