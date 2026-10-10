---
name: integrate-menu
description: "Give a site plugin a self-syncing menu: an interactive page of every command rebuilt from the program, plan and knowledge base, plus a /<slug>:menu entry. Use when the user runs /webapp-re:integrate-menu or asks to add a menu to a site skill."
argument-hint: "<site slug>"
---

# webapp-re integrate-menu

Plugin root: `${CLAUDE_PLUGIN_ROOT}`. Paths written `${CLAUDE_PLUGIN_ROOT}/...` here and in the reference files are under that directory. The arguments are: $ARGUMENTS

Target: the site given after the subcommand.

Gives a site plugin the `menu` command and the `/<slug>:menu` entry, so `/<slug>:menu` shows every command as an interactive
page in the Claude app's built-in browser: status, inputs as dropdowns and toggles, cost,
endpoints, what is missing for unbuilt commands, and a Copy button for the configured command.
Makes no requests to the site.

## How it stays in sync

Nothing about the commands is frozen into the skill. Each `/<slug>:menu` call runs the shared
builder, which fingerprints these sources (size and modification time of each file) and rebuilds
whenever any of them changed:

| Source | Gives |
|---|---|
| the program's `help` (offline, 0 requests) | which commands exist and are built, kinds, inputs |
| `program/src/*/schemas.json` | required inputs, enums, defaults, output fields |
| `plan/plan.json` | unbuilt commands, open steps, request cost, confirmation text, endpoint ids |
| `knowledge/endpoints/*.md` | which endpoints are verified |
| the status column of `<root>/plugin/skills/<slug>/SKILL.md` | `verified live`, `local`, `built, not verified`, `blocked` |
| `<root>/menu/hints.json` | groups, labels, dropdown options, pickers, option lists read from site caches |

The program's `help` output is cached against a fingerprint of the program's source tree, so
the subprocess runs only after the program changed. When no source changed, the builder reuses
the last page. A command added later appears under Other with inputs derived from its schema. A
removed command disappears, and any hint still naming it is reported as a warning. A changed
input schema flows through on the next call. The design and the code live once, in
`${CLAUDE_PLUGIN_ROOT}/menu/` (the repo's `plugin/menu/`), and the builder and the
template are fingerprinted too, so a change there reaches every site that has the menu. Each
build also rewrites the site skill's `## Menu` section when `skill-section.md` changed.

| File | Holds |
|---|---|
| `menu/menu.template.html` | The widget: markup, styles and script, with one `__MENU_DATA__` slot and the data contract version it reads |
| `menu/build_menu.py` | `build`, `check` and `install`; collects the state, renders the page, caches it and serves it on 127.0.0.1 |
| `menu/skill-section.md` | The `## Menu` section `install` writes into a site skill, under 10 lines because it loads with every `/<slug>:<slug>` call |
| `menu/standalone.template.html` | The page wrapper around the widget, with light and dark tokens |
| `${CLAUDE_PLUGIN_ROOT}/references/menu-delivery.md` | The inline mode and the fallbacks, read only when the built-in browser is missing or the user asks for `menu inline` |

The builder writes `var/menu/menu.page.html`, `var/menu/build.json` (fingerprints and the cached
help) and `var/menu/server.json` (the page server's port). `--inline` writes `menu.inline.html`,
or numbered `menu.inline-N.html` parts when it is over 24,000 characters.

## Steps

1. **Find the site.** `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py path --site <target>`.
   The site needs its plugin's main skill, `<root>/plugin/skills/<slug>/SKILL.md`, and, for
   runnable commands, a program with `help`. If the skill is missing, stop and suggest
   `/webapp-re:engineer <target>`.
2. **Read the state.** Run
   `uv run --script ${CLAUDE_PLUGIN_ROOT}/menu/build_menu.py check --site <slug>` with no
   hints file yet, or with the existing one. It prints one line of JSON with the counts, the page
   size, warnings and problems. `problems` includes any break of the data contract between the
   builder and the template.
3. **Write or refresh `<root>/menu/hints.json`** with
   [references/menu-hints.md](${CLAUDE_PLUGIN_ROOT}/references/menu-hints.md). Group every command the way a user
   thinks about the site. Give each runnable input the control a person would want: a select for
   a known set of values, a datalist for a big set read from a site cache, a picker pointing at
   the list command that yields an id, a toggle for a flag. Take every option value from the
   schema, the plan, the knowledge base or a cache file; never invent one. Leave a field as text
   with a hint when its values were never recorded. Keep existing hints for commands that still
   exist and drop the ones the checker reports as stale.
4. **Check.** Rerun `check` until `problems` is empty and every warning is understood. A warning
   about a missing cache file is fine when the cache is filled by a command the user has not run
   yet; say so.
5. **Install.** `uv run --script ${CLAUDE_PLUGIN_ROOT}/menu/build_menu.py install --site <slug>`
   writes the `## Menu` section between `<!-- webapp-re:menu -->` markers, before `## Errors`, and
   adds `menu` to the description's command list. It is idempotent, and it refuses to write when
   the description would pass 1024 characters; shorten the description by hand then. Then run
   `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/site_plugin.py scaffold --site <slug>`, which
   writes the plugin's `skills/menu/SKILL.md` entry, and `site_plugin.py check --site <slug>`.
6. **Show it.** Follow the new `## Menu` section of the site skill once, so the user sees the
   menu in this session. `install --site all` refreshes the section in every site skill that
   already has one; `check --site all` checks every site.

## Reply

The counts, the path of the hints file, the warnings, and a note that `/<slug>:menu` works in
every later session and always reflects the current program, plan and knowledge base. A load
costs the same few hundred characters of context whatever the menu's size, because the page
never passes through the model; only `menu inline` costs tokens in proportion to the widget,
which `build --inline` reports as `chars`.
