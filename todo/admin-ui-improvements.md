# Admin UI Improvements

Goal: make the admin feel like a real ops dashboard — closer to Frappe Cloud in density,
clarity, and capability — while keeping the no-framework, filesystem-first philosophy.

---

## 1. Design System

### 1.1 Color & visual refresh
Brand color is `#171717` (frappe-ui gray-900 — near-black). Already applied to tokens,
buttons, nav active state, and focus rings. Remaining work:

- Adopt frappe-ui's full neutral gray scale (done: 50–900 now match frappe-ui values,
  shifting away from Tailwind's blue-tinted grays to warm neutrals).
- Adopt frappe-ui shadow tokens (done: `--shadow-sm`, `--shadow`, `--shadow-md`).
- Add a consistent danger color token (`--red-600: #dc2626`) used by all destructive
  buttons; currently the "Kill" button uses ad-hoc gray-900 styling.
- Add `--color-success` / `--color-warning` aliases pointing at the existing chromatic
  tokens so badge and button danger colours come from a single source.

Reference: frappe-ui gray scale and shadow values are in
`frappe/frappe-ui/tailwind/tokens.js` and `tailwind/colors.json`.

### 1.2 Status badges
Standardise to a single `badge` component with these semantic variants driven by class:
`badge-success`, `badge-warning`, `badge-error`, `badge-neutral`, `badge-running` (pulsing dot).
Currently the colour logic is split across badge classes and inline styles.

### 1.3 Empty states
Every table needs a proper empty state: an icon, a heading, and a call-to-action button
where applicable (e.g. "No apps — Add App"). Currently just a colspan td with grey text.

### 1.4 Confirmation dialogs
All destructive actions (kill task, drop site, remove app) need a confirm step in the
existing Modal system — not browser `confirm()`. Reuse the modal with a short warning
message and red "Confirm" button.

### 1.5 Page titles
Set `<title>` per-page (`Sites — bench admin`, `Tasks — bench admin`) instead of the
static "bench admin" for every page.

---

## 2. Navigation & Layout

### 2.1 Breadcrumbs
Detail pages (site detail, task detail, log viewer, binlog detail) already have a
breadcrumb section. Standardise it into a `{% block breadcrumb %}` slot in `base.html`
rendered as `<nav class="breadcrumb">` so it's consistent across all pages.

### 2.2 Sidebar layout option
At wider viewports the current top-nav wastes vertical space. Consider a collapsible
left sidebar matching the Frappe Cloud layout: icon + label, collapses to icons-only
at narrow widths. Low priority — but design for it so CSS variables are in place.

### 2.3 Auto-refresh
Dashboard and Processes pages should auto-refresh every 10 s using a small JS snippet
(`setTimeout(() => location.reload(), 10_000)`) with a visible countdown indicator
so the user knows when the next refresh fires. Opt-out via a "Pause" button.

---

## 3. Dashboard

Current state: four stat cards + three read-only tables with no actions.

### 3.1 Stat cards — add deltas and links
Each stat card should link to its respective page and show a secondary line:
- Bench name → links to `/` (no change)
- Apps: "N apps, M cloned" — clickable to `/apps`
- Sites: "N sites, M online" — clickable to `/sites`
- Processes: "N running / M total" — clickable to `/processes`, amber/red if any stopped

### 3.2 Quick-action strip
A row of secondary buttons below the stat cards:
- "Init bench" (runs `bench init`)
- "Build assets" (enqueues `build` task)
- "Update bench-cli" (enqueues `update` task)
- "Reload supervisor" (enqueues `reload-supervisor` task)

These are currently only reachable via CLI.

### 3.3 Recent tasks widget
A 5-row recent tasks table at the bottom of the dashboard (subset of `/tasks`) showing
command, status badge, started, duration. No actions — just a summary with a "View all"
link.

---

## 4. Apps Page

### 4.1 Clone status column
Replace the "not cloned" text in the commit column with a proper badge (`badge-warning`
"not cloned") and show a "Clone now" button inline that enqueues a `get-app` task.

### 4.2 App actions dropdown
Each row needs a ⋯ actions menu (small button, positioned dropdown) with:
- **Pull** — enqueue `bench frappe update-apps <name>` (needs new task command)
- **Rebuild assets** — enqueue `build` task
- **Remove app** — confirmation modal → remove from bench.yml + uninstall from venv
  (needs `remove-app` task)

### 4.3 Add App modal — branch default hint
When the user leaves Branch blank, show a hint "will use repo default branch" (already
done in placeholder text) but also make the branch field show the actual default after
the repo URL is blurred (GitHub API call — optional, low priority).

---

## 5. Sites Page

### 5.1 Site list — richer status
Current status is just "exists" / "not created". Expand to:
- `running` — site_config.json exists and site responds to a HEAD /api/ping check
- `exists` — site_config.json exists but no ping check done (default, avoids latency)
- `not created` — no site_config.json

Show installed app count as pills rather than a comma-separated string.

### 5.2 Create Site modal — admin password field
Add an optional "Admin password" field (default: admin) so users can set it at creation
time rather than having to edit site_config.json afterwards.

### 5.3 Site detail — actions

**Missing actions to add:**

| Action | Backend |
|--------|---------|
| Delete site | new `drop-site` task (`bench frappe drop-site --force`) |
| Backup site | new `backup-site` task (`bench frappe backup`) |
| Enable/disable maintenance mode | new `set-maintenance-mode` task |
| Add domain | write `domains` list to bench.yml, regenerate nginx config |

Place these in a card titled "Danger zone" at the bottom of the page, styled with a
red left border, matching Frappe Cloud's pattern for destructive actions.

### 5.4 Site detail — installed apps as table
Replace the bulleted `<ul>` with a small table: App | Version | "Uninstall" button.
Uninstall enqueues `bench frappe uninstall-app`.

### 5.5 Site detail — edit site_config.json inline
Replace the raw JSON `<pre>` with an editable `<textarea>` + Save button. On save,
validate JSON client-side, then POST to a new `/sites/<name>/config` endpoint that
writes the file. Keep the password masking display but write back the original value
when saving (fetch the real password from disk, merge, save).

---

## 6. Processes Page

### 6.1 Start / stop / restart controls
Each row needs action buttons whose availability depends on status:
- Running → "Restart" + "Stop"
- Stopped → "Start"
- Unknown → disabled

For Honcho (foreground) this is harder — map to SIGTERM/SIGHUP on the PID. For
Supervisor, use `supervisorctl start/stop/restart <name>`. Route through a new
`/processes/<name>/action` endpoint.

### 6.2 Resource column
Add CPU% and RSS (MB) columns by reading `/proc/<pid>/stat` (Linux) or `ps -o %cpu,rss`
(macOS) per process. Only show if the process is running. These refresh on page
auto-refresh (see 2.3).

### 6.3 Log shortcut
"View log" link already exists but goes to the raw filename. Pre-populate it with the
correct log file per process definition so users don't have to hunt.

---

## 7. Logs Page

### 7.1 Search / filter
Add a `?search=<term>` query param. When set, filter lines server-side using
`grep -i <term>` on the log file. Show a search box above the output pre that
submits via GET.

### 7.2 Download button
Add a `<a href="/logs/<filename>/download">` route that streams the file with
`Content-Disposition: attachment`.

### 7.3 ANSI colour stripping
Frappe and bench processes emit ANSI escape codes that show as raw `\x1b[...m`
garbage in the pre block. Strip them server-side in LogReader before returning
lines.

### 7.4 Line count in list
Show file size already. Also show line count (cheap: `wc -l`) so users can judge
whether to tail 200 or 5000 lines.

---

## 8. Tasks Page

### 8.1 Re-run button
On task detail, add a "Re-run" button that POSTs the same command + args to
`/tasks/run`. Useful for retrying a failed `migrate` or `get-app`.

### 8.2 Status filter
On the task list, add `?status=running|success|failed` query param with a
tab/pill filter UI above the table (similar to Frappe Cloud's job list).

### 8.3 Download output
Add `/tasks/<id>/output/download` route that returns the raw `output.log` as
an attachment.

### 8.4 Auto-redirect on success
When a task finishes with exit code 0, auto-redirect to the originating page
after 2 s (pass a `?return=<url>` param from the form submissions that kick off
tasks). Show a "Redirecting to sites in 2s… (cancel)" banner.

---

## 9. Database Page

### 9.1 MariaDB status card
At the top of the database section, show a status card:
- Connection status (connected / error)
- MariaDB version
- Current binlog position
- Slow query log enabled (yes/no)

### 9.2 Purge binary logs
Add a "Purge logs before N days" form (input + button) that executes
`PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL N DAY)`.

### 9.3 Slow query threshold config
Show the current `long_query_time` value with an inline edit + save that updates
MariaDB's global variable at runtime.

---

## 10. New: Scheduler / Cron Page

Frappe has a scheduler that runs periodic jobs. Add a `/scheduler` page that:
- Shows scheduler status (enabled/disabled) via `bench frappe scheduler status`
- Button to enable/disable
- Table of recent scheduled jobs pulled from `__JobQueue` (if accessible)

---

## 11. New: Config Page

A read-only (initially) view of the parsed `bench.yml` split into sections:
- Bench settings (name, Python, process manager, ports)
- MariaDB config (host, port, admin user — password masked)
- Redis config (ports)
- Worker counts
- Nginx config

Each section has an "Edit" button that opens an inline form for that section's
scalar fields and POSTs to `/config/update` (similar to the existing `update-config`
CLI command). This replaces the need to hand-edit bench.yml for common settings.

---

## Priority Order

| Priority | Items |
|----------|-------|
| High | 1.4 confirmations, 3.3 recent tasks, 5.3 site danger zone, 7.3 ANSI strip, 8.1 re-run, 8.2 status filter |
| Medium | 2.3 auto-refresh, 3.2 quick actions, 5.2 admin password, 5.4 apps table, 6.1 process controls, 7.1 log search, 7.2 download |
| Low | 1.2 sidebar, 4.2 app actions, 5.5 inline config edit, 9.x database, 10 scheduler, 11 config page |
