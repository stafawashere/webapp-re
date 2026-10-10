# Architecture

The plugin has one skill per stage, a router skill, and two vendored skills. Every site you work
on gets a workspace with a fixed layout and, once it's built, a plugin of its own. Those site
plugins are listed in a local marketplace, `webapp-re-local`, that the pipeline writes next to
your workspaces.

| Skill or plugin | Path | Role | Loaded by |
|---|---|---|---|
| `webapp-re` plugin | [../plugin/](../plugin/skills/webapp-re/SKILL.md) | The router skill plus one skill per stage (six). `reverse` is the method (capture, identify, ablate, record, replay, verify, close) and every other stage uses it. Owns `kb.py`, `site_plugin.py`, the site and plugin layouts, the checkers and `optimize_run.py` | You, as `/webapp-re:<stage> <site>` or `/webapp-re <stage> <site>`; site-specific skills that delegate their method to it; any request to find one endpoint, which routes to `reverse` |
| `web-api-reverse-engineering` | [../plugin/skills/web-api-reverse-engineering/](../plugin/skills/web-api-reverse-engineering/SKILL.md) | Third-party. Discovery-notes vocabulary (auth, required headers, anti-bot, session, quirks) and OpenAPI 3.1 output | `scope` for vocabulary, `engineer` for the spec |
| `js-reverse` | [../plugin/skills/js-reverse/](../plugin/skills/js-reverse/SKILL.md) | Third-party, Chinese text. The Observe, Capture, Rebuild, Patch, DeepDive loop for values computed by client code | `reverse` step 4 and `engineer` step 2, only when a signature, nonce or encrypted field is found |

Obfuscated and bundled code is covered by
[references/bundles-and-obfuscation.md](../plugin/references/bundles-and-obfuscation.md)
rather than a separate skill.

## Data flow

```
/webapp-re:scope <url>
   kb.py init                         creates $WEBAPP_RE_HOME/<slug>/
   walk the site in your Chrome (read-only)
   writes scope/scope.json + scope/scope.md
   check_scope.py                     structure, cross-references, secret scan
   kb.py record-finding (hypothesis) per endpoint, record-pattern per noise source, close-run
         |
         v
/webapp-re:plan <slug>                no requests to the site
   reads scope/, knowledge/INDEX.md, any existing plan
   writes plan/plan.json + plan/plan.md
   check_plan.py                      every dependency in scope, schemas present, build order complete
         |
         v
/webapp-re:engineer <slug> [commands]
   check_plan.py again, then per build step:
      the reverse stage until each endpoint is verified twice
      (js-reverse when a value is computed client side)
   builds program/                    uv project: session, transport, pacer, classifier, models, CLI
   offline checks: pytest and the provenance gate, plus one deliberate break that must fail them
   renders openapi/<slug>.openapi.yaml
   generates <root>/plugin/: skills/<slug>/SKILL.md (help + one row per command),
   help and menu entries, scripts/<slug> launcher, marketplace entry (site_plugin.py scaffold)
   verifies every command live, and each write waits for your approval
         |
         v
/<slug>:help, /<slug>:<slug> <command>   calls program/ through plugin/scripts/<slug> (uv)
         |
         v
/webapp-re:optimize <slug> [names] [--auto]
   phase 1, read-only: snapshot, offline checks and timings, live reads only with a valid session
   audit: reviewer subagents, then verifiers that try to refute each finding
          -> optimize/<run-id>/findings.json, report.md
   a second snapshot shows nothing changed, then it asks which findings to apply
   phase 2, on the findings you accept: recheck, back up, split the edits by file
   apply: one fixer subagent per group of files, then a reviewer that diffs every change
   reruns every check and live read, writes result.md
```

Each stage reads what the previous one wrote from a fixed path, so you never pass files around
by hand. [site-layout.md](../plugin/references/site-layout.md) describes that tree.

## Stages

### Reverse

[skills/reverse/SKILL.md](../plugin/skills/reverse/SKILL.md) takes a site and a goal, something
you'd do on the site, and finds the one request behind it. It reads what the knowledge base
already has, finds the call, writes the request and any dead ends back, and closes the run with a
ledger entry. The cheapest sources come first (the knowledge base, the DOM, framework state,
cached bundles), before capturing traffic, replaying a request, or, last and only with your
approval, sending a write. Capture goes through Claude in Chrome with `capture-hook.js`, or with
`cdp_capture.py` against a separate Chromium. A finding starts as `hypothesis` and only
`kb.py verify` marks it `verified`. The later stages build on a finding once it has passed two
independent replays. Success and failure are read from the response body, not the status code.

### Scope

[skills/scope/SKILL.md](../plugin/skills/scope/SKILL.md) walks the whole site read-only, in a new
tab of your own Chrome through the Claude in Chrome extension. It goes breadth first over the
navigation, then into each section, as in
[walk-procedure.md](../plugin/references/walk-procedure.md). After each step it reads
`read_network_requests` and the page hook `capture-hook.js`, injected with `javascript_tool`,
which records fetch and XHR bodies. A control that would change something is recorded as a
capability and marked "not exercised", unless you approve pressing that exact one.

The output follows [scope-schema.json](../plugin/references/scope-schema.json). The walk is done
when every top-level navigation entry was opened, every list paginated once, every kind of detail
view opened once and every settings page read. Anything missed goes to `open_questions` with a
reason.

### Plan

[skills/plan/SKILL.md](../plugin/skills/plan/SKILL.md) turns the scope into commands, one per
thing a person would ask the site for, with a `help` command always included
([command-design.md](../plugin/references/command-design.md)). Commands are grouped into
sub-skills only when a group has its own setup or risk. Each command carries input and output JSON
Schema, the endpoints it depends on, pagination, failure classes, a confirmation rule if it
writes, and any reverse-engineering work still open with a request budget. The build order goes
session and transport first, then the read that proves auth, shared reads, pagination, writes,
and anything blocked on request signing last. The format is in
[plan-format.md](../plugin/references/plan-format.md). Command names stay the same across
re-plans, since people may already be typing them.

### Engineer

[skills/engineer/SKILL.md](../plugin/skills/engineer/SKILL.md) builds the program described in
[program-architecture.md](../plugin/references/program-architecture.md) and the site skill
described in [central-skill-template.md](../plugin/references/central-skill-template.md), and
checks it live as in [live-verification.md](../plugin/references/live-verification.md), under
these rules:

- The program uses the session from your browser. Cookies or tokens you copy go into
  `<root>/.env` with mode 600. It doesn't log in with a password and doesn't take cookies on the
  command line.
- Every endpoint in `program/` has to be backed by a finding verified at least twice, and a
  provenance gate inside the program checks that.
- A command counts as verified live only after it ran against the site in that session and its
  output matched its schema.
- Exit code 14 from a generated skill means `ContractBroken`. The site changed, and
  `/webapp-re:engineer <slug> <command>` rebuilds that command.

### Optimize

[skills/optimize/SKILL.md](../plugin/skills/optimize/SKILL.md) reviews one built site: its main
skill, sub-skills, commands and program, or only the ones you name. Phase 1 changes nothing and
takes a snapshot before and after to show it. [assets/optimize-audit.js](../plugin/assets/optimize-audit.js)
runs one reviewer each for speed, stability, scope, correctness, safety, skill quality and
anything else, then verifiers that try to refute every finding. None of them write files or send
requests. Live reads stay in your own session, inside a budget it prints first (20 by default).
Phase 2 runs [assets/optimize-apply.js](../plugin/assets/optimize-apply.js) on the findings you
accept. It splits the edits by file so two fixers never touch the same one, does program edits
one group at a time, and has a reviewer diff every change against a backup. Then it reruns every
check, asks before any live write, and records the before and after numbers. The formats are in
[optimize-format.md](../plugin/references/optimize-format.md).

## Scripts

| Script | Where | Does | Dependencies |
|---|---|---|---|
| `kb.py` | plugin/scripts | Per-site knowledge base: `init`, `path`, `stats`, `new-run`, `record-finding`, `verify`, `record-pattern`, `index`, `scan-secrets`, `close-run`. Won't record a finding directly as `verified`, only `verify` raises its status | stdlib |
| `shape.py` | plugin/scripts | JSON response to key names, types, counts and key coverage fractions, without printing any values | stdlib |
| `cdp_capture.py` | plugin/scripts | One capture window over CDP against an already-running Chromium. Opens its own tab at about:blank, enables Network, then navigates, so the cold load is inside the window. Redacts credential headers and token-like body fields at the writer. Closes only its own tab | `websockets>=12` |
| `capture-hook.js` | plugin/assets | Page hook that wraps fetch and XHR, keeps up to 200 records with bodies up to 65536 chars, exposes `window.__reCaptureDump({match})` | none |
| `check_scope.py` | plugin/scripts | Validates `scope.json`: structure, unique ids, cross-references, secret-looking values | stdlib |
| `check_plan.py` | plugin/scripts | Validates a plan against its scope: kebab-case names, schemas, confirmation rule on writes, dependencies exist, build order covers every command once | stdlib |
| `optimize_run.py` | plugin/scripts | Optimize runs: `new-run`, `latest`, `snapshot`, `compare`, `measure`, `validate`, `report`, `revalidate`, `partition`, `backup`, `result` | stdlib |
| `site_plugin.py` | plugin/scripts | Site plugins: `scaffold` writes `<root>/plugin/` (manifest, launcher, `help` and `menu` entries, normalized main skill) and the marketplace entry, `check` validates one site or all, `marketplace [--check]` writes or compares the manifest, `status` lists sites. `kb.py init` calls `scaffold` for a new site | stdlib |
| `optimize-audit.js`, `optimize-apply.js` | plugin/assets | The audit and apply scripts the optimize stage hands to Claude Code's Workflow tool, which runs several subagents from one script | none |

All run with `uv run --script <path>`. The fixtures they are checked against are described in
[../tests/README.md](../tests/README.md).

## Slugs

The slug is the registrable domain without its public suffix: `app.example.com` and
`www.example.com` become `example`, `bbc.co.uk` becomes `bbc`. `kb.py` carries a small built-in
list of two-part suffixes, which is not the full public suffix list, so `--slug` overrides it.
The slug names the workspace directory, the site plugin, its main skill and its slash commands.
