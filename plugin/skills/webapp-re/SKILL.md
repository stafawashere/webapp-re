---
name: webapp-re
description: Reverse engineer any web app's private HTTP API from the user's signed-in browser and turn it into an automation program and a /<site> plugin. Stages: reverse finds and verifies the request behind one goal and records it in a per-site knowledge base; scope walks the site read-only and inventories pages, capabilities, endpoints, auth and caveats; plan designs commands, schemas and build order; engineer (alias develop) builds the program, verifies commands live and generates the site plugin; optimize audits a site's plugin and program, then applies accepted fixes; integrate-menu gives a site plugin a self-syncing menu; upgrade brings a site built by an older webapp-re up to the installed version in one unattended run. Use when the user runs /webapp-re, asks to find the endpoint behind a feature, document a hidden API, scope, map, plan, build or automate a web app, create a client, CLI, scraper, skill or plugin for a site, optimize, audit, speed up or harden a site skill ("optimize my <site> skill"), add a menu to a site skill, upgrade or re-engineer a site built by an older webapp-re, or when a site plugin delegates its method here.
argument-hint: "reverse|scope|plan|engineer|develop|optimize|integrate-menu|upgrade|help <site slug or url> [goal or command names] [--auto|--apply run-id]"
---

# webapp-re

Arguments: $ARGUMENTS

Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

## Route

Each stage is its own skill in this plugin, so `/webapp-re:<stage>` runs it directly. This
router takes the older form, `/webapp-re:webapp-re <stage> <target>`, and requests that name no
stage. Read the first word of the arguments as the stage and everything after it as the target.

| Stage | Skill file | What it does |
|---|---|---|
| `reverse` | `${CLAUDE_PLUGIN_ROOT}/skills/reverse/SKILL.md` | Finds and verifies the request behind one goal on one site, and records it in the site's knowledge base. The method every other stage uses. |
| `scope` (also `scope goals`) | `${CLAUDE_PLUGIN_ROOT}/skills/scope/SKILL.md` | Scopes out every goal: walks the site read-only and writes `scope/scope.md` and `scope/scope.json`. |
| `plan` | `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md` | Plans the program and the plugin: the command set, schemas, dependencies, build order. Writes `plan/plan.md` and `plan/plan.json`. No requests to the site. |
| `engineer` (also `develop`) | `${CLAUDE_PLUGIN_ROOT}/skills/engineer/SKILL.md` | Builds the automation program and the site plugin, and verifies every command live. |
| `optimize` | `${CLAUDE_PLUGIN_ROOT}/skills/optimize/SKILL.md` | Audits the site's plugin, skills and program with a read-only multi-agent workflow, writes `optimize/<run-id>/findings.json` and `report.md`, asks, then applies the accepted fixes and reruns every gate. |
| `integrate-menu` | `${CLAUDE_PLUGIN_ROOT}/skills/integrate-menu/SKILL.md` | Gives the site plugin a `menu` entry: an interactive page of every command, rebuilt from the program, plan and knowledge base on each call by the shared builder in `menu/`. No requests to the site. |
| `upgrade` | `${CLAUDE_PLUGIN_ROOT}/skills/upgrade/SKILL.md` | Audits a site against the installed webapp-re with `upgrade_check.py`, reruns only the stages that are out of date, applies confirmed optimize findings and stamps the version in `site.json`. Runs without asking. |
| `help` or nothing | this file | Print the help below and the sites that already exist. |

When the stage is `scope goals`, drop the word `goals` before reading the target. Read the
stage's skill file in full and follow it, with the target as its arguments. An unknown stage gets
the help text, not a guess. When this skill is loaded without a stage, for example by a request
to find one endpoint or by a site plugin, follow the reverse stage.

## Help

```
/webapp-re:reverse <site> <goal>             find and verify the request behind one goal
/webapp-re:scope <site or url>               scope out all goals on the site
/webapp-re:plan <site>                       plan the program and the site plugin
/webapp-re:engineer <site> [commands...]     build the program and the /<site>: plugin
/webapp-re:optimize <site> [names...] [--auto]
                                             audit the site's plugin and program, then fix what you accept
/webapp-re:optimize <site> --apply [run-id]  apply the findings of an earlier audit
/webapp-re:integrate-menu <site>             give /<site>:menu a self-syncing menu
/webapp-re:upgrade <site or all> [--dry-run]  bring a site built by an older webapp-re up to date
/webapp-re:webapp-re help                    this text
```

Each site lives in `$WEBAPP_RE_HOME/<slug>/`, by default `~/dev/webapp-re/apps/<slug>/`. With `help`,
list the directories there that hold a `site.json` and, for each, which of `scope/scope.json`,
`plan/plan.json`, `program/`, `plugin/`, `optimize/` and `menu/hints.json` exist, so the user can
see which stage comes next. `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/site_plugin.py status`
prints the plugin part of that.

## Layout of this plugin

| Path | Holds |
|---|---|
| `skills/` | The router, one skill per stage, and the two vendored skills `js-reverse` and `web-api-reverse-engineering` |
| `references/` | Method references (capture, ablation, failure classification, pacing, knowledge base, OpenAPI, bundles, provenance gate, site layout, plugin layout) and stage references (walk procedure, scope schema, command design, plan format, program architecture, central skill template, live verification, optimize format, menu hints) |
| `scripts/` | `kb.py` per-site knowledge base, `site_plugin.py` site plugin generator and marketplace writer, `shape.py` response shapes, `replay.py` out-of-browser replay of an exported request, `walk_summary.py` scope walk folding and resume state, `scope_query.py` sliced scope reads, `cdp_capture.py` CDP capture window, `check_scope.py` and `check_plan.py` stage checkers, `upgrade_check.py` the upgrade audit, fix and version stamp, `optimize_run.py` for optimize run ids, snapshots, measurements and findings validation |
| `assets/` | `scope-probe.js` and `scope-paginate.js`, the per-page scope probe and pagination check; `capture-hook.js`, the fetch and XHR page hook; `reverse-capture.js`, `reverse-ablate.js` and `reverse-export.js`, the reverse fast path (redacted candidates, one-call ablation, export for `replay.py`); `optimize-audit.js` and `optimize-apply.js`, the two optimize workflow scripts |
| `menu/` | The shared site menu: `menu.template.html` the widget, `build_menu.py` which collects a site's state, renders and caches the page and serves it on 127.0.0.1 for the built-in browser, `skill-section.md` the section installed into site skills, `standalone.template.html` the page wrapper; fallbacks in `references/menu-delivery.md` |

The plugin's repository keeps `docs/` and `tests/` one level up from the plugin. Site workspaces
live under `$WEBAPP_RE_HOME`, outside the plugin.
