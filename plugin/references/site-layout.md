# Per-site layout

One directory per web app, shared by every stage of `webapp-re`
(reverse, scope, plan, engineer, optimize). Each stage reads what the previous one wrote from a fixed path, so none
of them has to be told where anything is.

## Root

`$WEBAPP_RE_HOME/<site-slug>/`, with `WEBAPP_RE_HOME` defaulting to `~/dev/webapp-re/apps`.

The slug is the registrable name without its public suffix: `app.example.com` and
`www.example.com` both become `example`, `bbc.co.uk` becomes `bbc`. The slug is also the
name of the site's plugin and of its main skill, so `/example:example`. Override with `--slug` when
two sites would collide or the user prefers another name.

```bash
uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py init --site https://app.example.com
uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py path --site example
```

`init` is idempotent and prints the root. On a new site it also scaffolds `plugin/` and adds the
site to the local marketplace, through `site_plugin.py scaffold`. `path` prints the root without
creating anything.

## Tree

| Path | Holds | Written by |
|---|---|---|
| `site.json` | slug, origins, created date, browser path in use | `kb.py init`, then by hand |
| `scope/scope.md` | Human-readable inventory of the app | `/webapp-re:scope` |
| `scope/scope.json` | The same inventory, machine-readable, schema in the scope skill | `/webapp-re:scope` |
| `plan/plan.md` | Commands, schemas, dependencies, open work, build order | `/webapp-re:plan` |
| `plan/plan.json` | The same plan, machine-readable | `/webapp-re:plan` |
| `knowledge/INDEX.md` | Generated roll-up. Never hand edit. | `kb.py index` |
| `knowledge/endpoints/<id>.md` | One request contract per goal | `kb.py record-finding`, `kb.py verify` |
| `knowledge/patterns/<id>.md` | Dead ends, noise, quirks, techniques | `kb.py record-pattern` |
| `knowledge/sessions.md` | Append-only ledger, one entry per closed run | `kb.py close-run` |
| `knowledge/CHANGELOG.md` | One line per knowledge mutation | every `kb.py` write |
| `toolkit/js/<id>.js` | Page scripts that worked, redacted output by construction | by hand |
| `openapi/<slug>.openapi.yaml` | OpenAPI 3.1 rendered from verified findings | `/webapp-re:engineer` |
| `program/` | The automation library and CLI, a uv project | `/webapp-re:engineer` |
| `plugin/` | The site's Claude Code plugin: `.claude-plugin/plugin.json`, `skills/<slug>/` the main skill, `skills/help/` and `skills/menu/` entries, `scripts/<slug>` the launcher. Layout in `plugin-layout.md` | `kb.py init`, `/webapp-re:engineer`, `site_plugin.py scaffold` |
| `menu/hints.json` | How the site menu groups and presents commands; format in `menu-hints.md` | `/webapp-re:integrate-menu` |
| `var/menu/` | The last built menu page, the inline widget when asked for, `build.json` with input fingerprints and the cached program help, and `server.json` with the page server's port. Rebuilt by `/<slug>:menu` when an input changed | `build_menu.py build` |
| `optimize/<run-id>/` | One audit and its fixes: snapshots, `baseline.json`, `findings.json`, `report.md`, then `before/`, `after.json` and `result.md` if fixes were applied. Format in `optimize-format.md` | `/webapp-re:optimize`, `optimize_run.py` |
| `var/runs/<run-id>/` | Run notes | `kb.py new-run` |
| `var/captures/` | Capture JSONL, bodies kept, credential values redacted at the writer | capture tools |
| `var/logs/` | JSONL event log | `kb.py` |
| `.env` | Cookie material copied by the user from their browser. Mode 600. | the user |

The site's plugin is inside this tree, next to the program it calls, and gitignored like other
generated files. Claude Code
finds it through the local marketplace `webapp-re-local`, whose manifest is
`~/dev/webapp-re/.claude-plugin/marketplace.json` (the parent of the default `WEBAPP_RE_HOME`, or
`$WEBAPP_RE_MARKETPLACE`). A site under a different `WEBAPP_RE_HOME` gets its marketplace in that
home's parent, because a marketplace entry cannot point outside its own root.

## Git posture

Every site workspace is its own git repository, rooted at `apps/<site-slug>/`. `kb.py init` runs
`git init` there if no `.git` exists and writes a `.gitignore` that keeps out `.env`, `var/`,
session files, `optimize/*/before/` (backups that copy `var/`), `.claude/`, the generated `plugin/`, virtualenvs and caches.
Nothing is committed or pushed automatically, and no remote is added.
