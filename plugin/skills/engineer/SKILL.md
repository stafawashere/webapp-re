---
name: engineer
description: "Build a site's automation program, verify its commands live, render its OpenAPI spec and generate its Claude Code plugin with the /<slug>:<slug> skill and marketplace entry. Use when the user runs /webapp-re:engineer (alias develop) or asks to build, extend or rediscover commands of a site program."
argument-hint: "<site slug> [commands...]"
---

# webapp-re engineer

Plugin root: `${CLAUDE_PLUGIN_ROOT}`. Paths written `${CLAUDE_PLUGIN_ROOT}/...` here and in the reference files are under that directory. The arguments are: $ARGUMENTS

Target: the site given after the subcommand.

Third stage of the web automation pipeline. Reads `plan/plan.json` and `scope/scope.json` from the
site directory, and produces `program/`, `openapi/<slug>.openapi.yaml`, and the site plugin at
`<root>/plugin/` with its entry in the local marketplace. Nothing is written to `~/.claude/`
except through `claude plugin install`.

## Rules

- Everything in [the reverse stage](${CLAUDE_PLUGIN_ROOT}/skills/reverse/SKILL.md) under scope, consent and hard rules applies. Read
  them before the first live request.
- **Session adoption only.** The program reads cookie material the user copied from their own
  browser into `<root>/.env` (mode 600). It never automates a password login, never stores a
  password, and never accepts cookies on `argv`. If `.env` is missing, write `.env.example` with
  the cookie names from the scope and ask the user to fill it.
- **Writes need approval** in chat, per action, with a value the user chose, both during
  discovery and during verification.
- **Every endpoint literal in the program is backed** by a finding verified at least twice. The
  program carries a provenance gate that checks this.
- **Every live run is paced** and logged under `<root>/var/logs/` with counts, timings and
  statuses only.
- New code follows the user's style rules: 3-space indentation, double quotes, descriptive names,
  compound conditions decomposed into named variables, no narrating comments, no trailing blank
  lines. Python through `uv` only.

## Steps

1. **Load.** `kb.py path --site <target>`; read `plan/plan.json`, `knowledge/INDEX.md`, and
   `kb.py stats`. Read the scope through
   `${CLAUDE_PLUGIN_ROOT}/scripts/scope_query.py <root>/scope/scope.json` (index first, then `--id`
   for the endpoints a command needs), never whole, and grep `knowledge/endpoints/` for the
   endpoint ids instead of reading the folder. Run the plan checker
   (`${CLAUDE_PLUGIN_ROOT}/scripts/check_plan.py <root>`); if it fails, stop and
   suggest `/webapp-re:plan`. Pick the commands to build: the ones named in the arguments, or
   every command whose build step's dependencies are satisfiable.
2. **Close the open reverse-engineering steps**, in plan build order. For each dependency that is
   not verified twice, run the method in [the reverse stage](${CLAUDE_PLUGIN_ROOT}/skills/reverse/SKILL.md) for that goal: capture, identify,
   ablate, record, replay, verify, close. Load **js-reverse** when a required value is computed
   by client code, and read
   `${CLAUDE_PLUGIN_ROOT}/references/bundles-and-obfuscation.md` when the code is minified or obfuscated. Stay inside
   each step's request budget from the plan, and ask before exceeding it.
3. **Build the program** in `<root>/program/` following
   [references/program-architecture.md](${CLAUDE_PLUGIN_ROOT}/references/program-architecture.md): session, transport,
   pacer, classifier, typed models, one module per capability group, a command registry, the CLI,
   offline tests on recorded shapes, and the provenance gate.
4. **Run the offline gates**: `uv run pytest` and the provenance gate inside `program/`. Quote the
   output. Break one mapping on purpose, watch a test go red, restore it, so the tests are known to
   bite.
5. **Render OpenAPI** from verified findings with the mapping in
   `${CLAUDE_PLUGIN_ROOT}/references/openapi.md`, loading **web-api-reverse-engineering** for its discovery-notes
   vocabulary. Write `<root>/openapi/<slug>.openapi.yaml` and parse it to prove it loads.
6. **Generate the site plugin.** Write the main skill at `<root>/plugin/skills/<slug>/SKILL.md`
   from [references/central-skill-template.md](${CLAUDE_PLUGIN_ROOT}/references/central-skill-template.md),
   one row per command, each calling the program through the plugin's launcher. A site renderer
   such as `<root>/tools/engineer/render_skill.py` may write it. Sub-skills from the plan go to
   `<root>/plugin/skills/<group>/`, named by the rule in
   [references/plugin-layout.md](${CLAUDE_PLUGIN_ROOT}/references/plugin-layout.md). Then run
   `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/site_plugin.py scaffold --site <slug>`. It writes
   `plugin.json`, the launcher `scripts/<slug>`, the `help` entry, the `menu` entry and menu section
   when `<root>/menu/hints.json` exists, rewrites program calls to the launcher and slash commands to
   their namespaced form, and adds the site to the marketplace manifest. Then
   `site_plugin.py check --site <slug>` and `claude plugin validate <root>/plugin --strict` must
   both pass; quote them. With a menu, run `build_menu.py check --site <slug>` too and add hints for
   every new command it reports under Other, as in
   [the integrate-menu stage](${CLAUDE_PLUGIN_ROOT}/skills/integrate-menu/SKILL.md).
   On the site's first build, install it: when `claude plugin marketplace list` does not show
   `webapp-re-local` yet, `claude plugin marketplace add <marketplace root>` (the folder that holds
   the `.claude-plugin/marketplace.json` that `scaffold` printed), otherwise
   `claude plugin marketplace update webapp-re-local`; then
   `claude plugin install <slug>@webapp-re-local`. Later builds load in place, so a new session
   or `/reload-plugins` picks them up.
7. **Verify live**, command by command, with
   [references/live-verification.md](${CLAUDE_PLUGIN_ROOT}/references/live-verification.md). A command is reported as
   working only after it ran against the live site in this session and its output validated
   against its output schema. Reads run freely within the pacing budget; writes run only after the
   user approves that exact call.
8. **Write back.** Record every new finding, replay and pattern in the knowledge base, update the
   plan's readiness fields, and `kb.py close-run`.

## Reply

A table of commands with status (`verified live`, `built, not verified`, `blocked: reason`), the
live request count spent, the gate outputs quoted, the paths to the program, the spec and the
plugin, and the open work. Mention that `/<slug>:` lists the plugin's entries after
`/reload-plugins` or in the next session, and that `/<slug>:help` is the place to start.
