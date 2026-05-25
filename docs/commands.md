# Commands Specification

---

## `bench new`

Scaffolds a starter `bench.toml` inside a new bench directory.

**Pre-conditions:** No bench directory with the given name exists under `benches/`.

**Steps:**
1. Check that `benches/<name>/` does not already exist. If it does, print an error and exit.
2. Create `benches/<name>/`.
3. Write a minimal `bench.toml` with placeholder values to `benches/<name>/bench.toml`.
4. Print a message telling the user to edit the file and then run `bench init`.

**Does not** touch the filesystem beyond creating the directory and writing `bench.toml`.

---

## `bench init`

Installs and configures the entire environment described in `bench.toml`. Safe to re-run — each step checks whether it has already been done.

### Pre-conditions

- `bench.toml` exists and is valid.
- **Ubuntu:** The process has `sudo` access (required for `apt-get`).
- **macOS:** Homebrew is installed (`brew` is in `$PATH`). No `sudo` required — Homebrew installs to user-owned directories.

### Steps

```
1.  Validate bench.toml
2.  Install system packages
3.  Create bench directory structure
4.  Create Python virtualenv
5.  Clone and install framework app
6.  Install Node.js
7.  Install Node.js dependencies
8.  Configure Redis
9.  Generate Procfile
```

#### Step 1 — Validate bench.toml

`BenchConfig.from_file('bench.toml')` runs all validation rules. On failure, print the error and exit with code 1. No filesystem changes have occurred at this point.

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

`PythonEnvManager.create_venv()` runs `uv venv` with the requested Python version:
```
uv venv --python <version> env/
```
`uv` is auto-installed if not present. Skipped if `env/bin/python` already exists.

#### Step 5 — Clone and install framework app

For each `AppConfig` in `bench.init_apps()` (reads from `bench.toml [[apps]]`):
- Skip if `App.is_cloned` is already `True`.
- `App.clone()` runs:
  ```
  git clone <repo> --branch <branch> --depth 1 apps/<name>
  ```
- `PythonEnvManager.install_app(app)` runs:
  ```
  uv pip install -e apps/<name>
  ```

This installs the framework app and all its dependencies. After `bench init`, additional apps are added via `bench get-app`.

#### Step 6 — Install Node.js

`PythonEnvManager.install_node()` checks if `node` is present. If not, installs Node.js 24 via the NodeSource setup script.

Yarn is installed globally afterward: `npm install -g yarn`.

#### Step 7 — Install Node.js dependencies

`PythonEnvManager.install_node_dependencies()` runs `yarn install` for each app in `apps/` that has a `package.json`.

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

#### Step 9 — Generate Procfile

Writes `config/Procfile` with one line per process: web server, socketio, workers, and Redis.

Single-instance Redis (`redis.port`):
```
web: bench frappe serve --port 8000 --noreload
socketio: node apps/frappe/socketio.js
worker_default_1: env/bin/bench worker --queue default
worker_default_2: env/bin/bench worker --queue default
worker_short_1: env/bin/bench worker --queue short
worker_long_1: env/bin/bench worker --queue long
redis: redis-server config/redis.conf
```

Multi-instance Redis (`cache_port`/`queue_port`/`socketio_port`):
```
...
redis_cache: redis-server config/redis_cache.conf
redis_queue: redis-server config/redis_queue.conf
redis_socketio: redis-server config/redis_socketio.conf
```

On completion, prints:
```
bench init complete. Next steps:
  bench new-site site1.localhost  # create your first site
  bench start                     # start all processes
```

---

## `bench get-app`

Clones an app from a git repository and installs it into the virtualenv.

```bash
bench get-app https://github.com/frappe/erpnext --branch version-16
```

### Steps

```
1.  Validate bench.toml
2.  Clone the app
3.  Install Python dependencies
4.  Update apps.txt
```

#### Step 2 — Clone the app

`App.clone()` runs `git clone <repo> --branch <branch> --depth 1 apps/<name>`. The app name is inferred from the repository URL (last path component, without `.git`). Skipped if already cloned.

#### Step 3 — Install Python dependencies

`PythonEnvManager.install_app(app)` runs `uv pip install -e apps/<name>`.

#### Step 4 — Update apps.txt

Appends the app name to `sites/apps.txt`. Does **not** modify `bench.toml`.

---

## `bench new-site`

Creates a new Frappe site.

```bash
bench new-site site1.localhost
bench new-site site1.localhost --admin-password admin
```

### Steps

```
1.  Validate bench.toml
2.  Check site does not already exist
3.  Create the site
4.  Update common_site_config.json
```

#### Step 3 — Create the site

`Site.create(mariadb_config)` runs the framework app's `new-site` command:
```
env/bin/bench new-site <site.name>
    --mariadb-root-password <root_password>
    --admin-password <admin_password>
    --no-mariadb-socket
```

frappe generates and manages the database name and credentials internally; they are written into `sites/<name>/site_config.json`. The site directory is created on disk — it is **not** written to `bench.toml`.

#### Step 4 — Update common_site_config.json

`Bench.write_common_site_config()` rewrites `sites/common_site_config.json` with Redis URLs and the default site. Sites are discovered from the filesystem (`sites/` directory), not from `bench.toml`.

---

## `bench start`

Starts all bench processes using the built-in Procfile runner.

### Pre-conditions

- `bench init` has been run at least once (`config/Procfile` exists).
- MariaDB service is running on the host.

### Steps

```
1.  Validate bench.toml
2.  Check Procfile exists
3.  Start processes
```

#### Step 2 — Check Procfile exists

If `config/Procfile` is missing, print a message telling the user to run `bench init` first and exit with code 1.

#### Step 3 — Start processes

`HonchoProcessManager.start()` reads `config/Procfile` and spawns each process with `subprocess.Popen`. A dedicated thread per process streams output to stdout with a `<process-name> |` prefix and writes to `logs/<process-name>.log`. Per-process PID files are written to `pids/<name>.pid`.

`bench start` **blocks** — it stays in the foreground until the user sends `SIGINT` (Ctrl-C). On `SIGINT`, all child processes receive `SIGTERM` and are waited on before the parent exits.

---

## `bench stop`

Stops a running bench that was started with `bench start`.

### Steps

1. Read `pids/bench.pid`. If it does not exist, print "Bench is not running." and exit.
2. Send `SIGTERM` to the process group.
3. Remove `pids/bench.pid`.

Works across terminal sessions — the PID file is the source of truth.

---

## `bench build`

Builds JavaScript and CSS assets for all installed apps.

### Pre-conditions

- `bench init` has been run (apps are cloned, Node.js is installed, virtualenv exists).

### Steps

```
1.  Validate bench.toml
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
1.  Validate bench.toml
2.  Warn if processes are running
3.  For each app: git pull
4.  For each app: uv pip install -e
5.  For each site: bench migrate
```

#### Step 2 — Warn if processes are running

If `pids/bench.pid` exists and the process is alive, print a warning and ask the user to confirm before continuing. In non-interactive mode (`--yes` flag), skip the prompt and proceed.

#### Step 3 — git pull for each app

`App.update()` runs (for each app discovered in `apps/`):
```
git -C apps/<name> fetch origin
git -C apps/<name> merge --ff-only origin/<branch>
```

Fast-forward only. If a merge conflict would occur, print an error for that app and skip it (continue with remaining apps).

#### Step 4 — uv pip install -e for each app

`PythonEnvManager.install_app(app)` re-runs `uv pip install -e apps/<name>` to pick up any new Python dependencies.

#### Step 5 — bench migrate for each site

`Site.migrate()` runs (for each site discovered in `sites/`):
```
env/bin/bench --site <site.name> migrate
```

If migration fails on one site, print the error and continue with remaining sites. Exit with a non-zero code at the end if any migration failed.

---

## `bench update-config`

Regenerates all derived config files from `bench.toml` without running a full `bench init`. Use this after editing `bench.toml` to update ports, worker counts, or Redis settings.

**Files regenerated:**
- `config/redis.conf` (single-instance) or `config/redis_cache.conf`, `config/redis_queue.conf`, `config/redis_socketio.conf` (multi-instance)
- `config/Procfile`
- `sites/common_site_config.json`
- `config/nginx/*.conf` — only if `nginx.enabled = true`

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

The admin server includes a watchdog that sends `SIGTERM` to itself after the configured inactivity timeout (default: 3 minutes). Use `bench stop-admin` to stop it immediately.

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
bench admin                    # default port 8002
bench admin --port 9000        # custom port
bench admin --host 0.0.0.0     # expose to the network
```

See [docs/admin.md](admin.md) for the full interface specification.

---

## `bench setup nginx`

See [docs/production.md](production.md) for the full step-by-step.

**Summary:** Installs nginx if absent, generates per-site config files into `config/nginx/`, symlinks `include.conf` into `nginx.config_dir`, validates with `nginx -t`, and reloads nginx. Sites are discovered from the filesystem.

Pre-conditions: `nginx.enabled = true` in `bench.toml`, `bench init` has been run, process has `sudo` (Ubuntu) or Homebrew (macOS).

> **macOS note:** This command works on macOS with Homebrew nginx for local testing, but its primary use case is production deployment on Ubuntu/Linux servers. The `config_dir` default (`/etc/nginx/conf.d`) does not exist on macOS — set it to `/opt/homebrew/etc/nginx/servers/` (Apple Silicon) or `/usr/local/etc/nginx/servers/` (Intel) in `bench.toml`.

---

## `bench setup letsencrypt`

See [docs/production.md](production.md) for the full step-by-step.

**Summary:** Installs certbot if absent, ensures the webroot directory exists, runs `certbot certonly --webroot` for each site with `ssl = true` in `site_config.json` (with all domains as `-d` arguments), then regenerates nginx config with HTTPS blocks and reloads nginx.

Pre-conditions: `bench setup nginx` has run, nginx is serving port 80, DNS records for all SSL sites point to this server.

> **macOS note:** Let's Encrypt certificates require a publicly reachable server with real DNS records. This command is intended for Ubuntu/Linux production servers only. Do not run it on a local macOS development machine.

---

## `bench setup production`

See [docs/production.md](production.md) for the full step-by-step.

**Summary:** Writes `dns_multitenant: 1` to `sites/common_site_config.json`, then runs `bench setup nginx` and `bench setup letsencrypt` in sequence.

> **macOS note:** Production setup targets Ubuntu/Linux servers. On macOS, use `bench start` for development.

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
| `-b/--bench NAME` | Specify which bench to operate on (its name under `benches/`). Required when multiple benches exist and none is active. |
| `--verbose` | Print full tracebacks on error and all subprocess output. |
| `--yes` | Skip confirmation prompts (useful in CI). |
