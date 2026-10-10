# Site plugin layout

Every site the pipeline builds is a Claude Code plugin inside its own workspace, at
`<root>/plugin/`, next to the program it calls. The workspace `.gitignore` keeps `plugin/` out of
git. `site_plugin.py scaffold` writes it; `site_plugin.py check` and
`claude plugin validate <root>/plugin --strict` check it. Scaffold regenerates everything except
the main skill's body, which comes from the engineer stage or the site's own renderer, so a site
without a renderer has no other copy of that file.

```
<root>/plugin/
   .claude-plugin/plugin.json     name = <slug>, version, description, author, keywords
   skills/<slug>/SKILL.md         the main skill, from central-skill-template.md
   skills/<slug>/references/      detail the main skill loads on demand
   skills/help/SKILL.md           entry: the program's help
   skills/menu/SKILL.md           entry: the site menu, only when <root>/menu/hints.json exists
   skills/<group>/SKILL.md        a sub-skill from the plan, when there is one
   scripts/<slug>                 launcher: uv run --project <root>/program <slug> [--env-file <root>/.env]
```

## Naming rule

- The plugin is named after the slug. Plugin skills are invoked as `/<plugin>:<skill>`, so
  typing `/<slug>:` lists every entry of the site and nothing else.
- The main skill is also named after the slug, so it runs as `/<slug>:<slug>`. It keeps the whole
  trigger description, so every request the old `/<slug>` skill answered still routes to it.
  Measured on Claude Code 2.1.296: a bare `/<slug> <args>` still runs a skill whose name equals
  its plugin, although only the namespaced form is listed.
- Entry skills are named by what they do, in one word, and set `disable-model-invocation: true`
  so only the main skill triggers on its own: `help` and, with a menu, `menu`.
- A sub-skill is named `<group>` (not `<slug>-<group>`), so it runs as `/<slug>:<group>`.
- No skill name repeats across the main skill and the entries, and no name contains `:`.
- The pipeline follows the same rule: the plugin `webapp-re` has the router `webapp-re` and one
  skill per stage, so `/webapp-re:` lists `reverse`, `scope`, `plan`, `engineer`, `optimize` and
  `integrate-menu`. `develop` stays an alias the router accepts.

## Paths

- A skill names files in its own plugin through `${CLAUDE_PLUGIN_ROOT}`, which Claude Code
  substitutes in skill bodies. A site plugin calls its program only through
  `${CLAUDE_PLUGIN_ROOT}/scripts/<slug>`.
- The variable is not set in the shell Claude runs commands in, and in a site plugin it names
  that site's plugin, not the pipeline. A site skill names the pipeline's shared files, such as
  `menu/build_menu.py`, by the absolute path `build_menu.py` writes into the menu section.
- Nothing names `~/.claude/skills/`. `site_plugin.py check` fails on any file in the plugin
  that does.
- Slash commands in skill bodies are written namespaced: `/<other slug>:<other slug>` and
  `/webapp-re:<stage>`. Frontmatter descriptions may keep the bare `/<slug>` the user types.

## Marketplace

The local marketplace `webapp-re-local` lists the pipeline and every site plugin. Its manifest is
`.claude-plugin/marketplace.json` in the parent of `WEBAPP_RE_HOME` (override with
`WEBAPP_RE_MARKETPLACE`), because a marketplace source must be a `./` path inside the
marketplace's own root, with no `..` and no symlink. `site_plugin.py scaffold` rewrites it;
`site_plugin.py marketplace --check` compares it. It names private sites, so it is never part of a
public repository.

Plugins from a local directory marketplace load in place, so an edit takes effect at the next
session or after `/reload-plugins`. The marketplace is added once, the first time a site is
built (`claude plugin marketplace add` with the parent of `WEBAPP_RE_HOME`, or
`WEBAPP_RE_MARKETPLACE`). A new site is installed once:

```bash
claude plugin marketplace update webapp-re-local
claude plugin install <slug>@webapp-re-local
```
