# Architecture

The plugin has one skill per stage, a router skill, and two vendored skills. Every site you work
on gets a workspace with a fixed layout and, once it's built, a plugin of its own. Those site
plugins are listed in a local marketplace, `webapp-re-local`, that the pipeline writes next to
your workspaces.

| Skill or plugin | Path | Role | Loaded by |
|---|---|---|---|
| `webapp-re` plugin | [../plugin/](../plugin/skills/webapp-re/SKILL.md) | The router skill plus one skill per stage (seven). `reverse` is the method (capture, identify, ablate, record, replay, verify, close) and every other stage uses it. Owns `kb.py`, `site_plugin.py`, the site and plugin layouts, the checkers, `optimize_run.py` and `upgrade_check.py` | You, as `/webapp-re:<stage> <site>` or `/webapp-re <stage> <site>`; site-specific skills that delegate their method to it; any request to find one endpoint, which routes to `reverse` |
| `web-api-reverse-engineering` | [../plugin/skills/web-api-reverse-engineering/](../plugin/skills/web-api-reverse-engineering/SKILL.md) | Third-party. Discovery-notes vocabulary (auth, required headers, anti-bot, session, quirks) and OpenAPI 3.1 output | `scope` for vocabulary, `engineer` for the spec |
| `js-reverse` | [../plugin/skills/js-reverse/](../plugin/skills/js-reverse/SKILL.md) | Third-party, Chinese text. The Observe, Capture, Rebuild, Patch, DeepDive loop for values computed by client code | `reverse` step 4 and `engineer` step 2, only when a signature, nonce or encrypted field is found |

Obfuscated and bundled code is covered by
[references/bundles-and-obfuscation.md](../plugin/references/bundles-and-obfuscation.md)
rather than a separate skill.

## Data flow

```
/webapp-re:scope <url>
   kb.py init                         creates $WEBAPP_RE_HOME/<slug>/
   walk the site in your browser (read-only) through chrome-devtools
      one navigate_page with the timing hook, then one scope-probe.js call per page
      each probe saves its result under var/captures/<run-id>/
   walk_summary.py                    folds the probe files into a frontier, a noise list, a draft scope
   writes scope/scope.json + scope/scope.md
   check_scope.py                     structure, cross-references, secret scan
   kb.py record-finding (hypothesis) per endpoint, record-pattern per noise source, close-run
         |
         v
/webapp-re:plan <slug>                no requests to the site
   reads scope.json in slices through scope_query.py, scope.md, knowledge/INDEX.md, any existing plan
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
approval, sending a write. Capture goes through the chrome-devtools MCP server in your own
browser, or through `cdp_capture.py` against a separate Chromium when it needs the real wire
headers or a search through the page's scripts. Claude in Chrome with `capture-hook.js` is the
fallback, and only after you say so. A finding starts as `hypothesis` and only
`kb.py verify` marks it `verified`. The later stages build on a finding once it has passed two
independent replays. Success and failure are read from the response body, not the status code.

When the goal is a read the page fires after one click or keystroke, there's a faster path.
`capture-hook.js` goes into the page, the action runs, and `reverse-capture.js` ranks what was
sent, with anything that looks like a key or token shown as `REDACTED`. `reverse-ablate.js` then
drops each query parameter, header and body field one at a time in a single call to find what the
request needs, which is the first verify pass. `reverse-export.js` saves that minimal request to a
file, and `replay.py` sends it from outside the browser with a different input and deletes the
file, which is the second. Requests made during the page load, writes and signed requests still
go the long way.

### Scope

[skills/scope/SKILL.md](../plugin/skills/scope/SKILL.md) walks the whole site read-only, in a new
tab of your own browser through chrome-devtools. It goes breadth first over the navigation, then
into each section, as in [walk-procedure.md](../plugin/references/walk-procedure.md). The first
page load carries a small script that stops the site from clearing its resource-timing list, and
from then on each page is one call to `scope-probe.js`. The probe moves to the next page in the
queue without a full navigation, records the API calls, links, forms, cookie names and framework
it sees, and saves all of that to a file instead of sending it back. `scope-paginate.js` checks
one list's next page. `walk_summary.py` folds the files into the list of pages still to visit, the
noise to ignore and a draft `scope.json`, and an interrupted walk picks up from its `walk.json`.
Values never leave the page, only names, patterns and shapes. A control that would change
something is recorded as a capability and marked "not exercised", unless you approve pressing
that exact one.

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
re-plans, since people may already be typing them. A scope can run to a few hundred KB, so the
plan stage never reads `scope.json` whole: `scope_query.py` prints a one-line index, then opens
single items with `--id`, one section with `--section`, or finds ids with `--grep`. The engineer
stage reads it the same way.

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

### Upgrade

[skills/upgrade/SKILL.md](../plugin/skills/upgrade/SKILL.md).
It brings a site built
by an older webapp-re up to the installed one. `upgrade_check.py audit` runs the current checkers
against the site (scope, plan, provenance gate, program tests, `site_plugin.py check`,
`claude plugin validate --strict`, the central skill template, Claude in Chrome tool names left in
the plugin, the menu, `kb.py scan-secrets`) and maps each failure to the stage that fixes it, so
only those stages run. A site whose `site.json` names the installed version and passes every check
costs one script call. Anything that ran, or a version gap, also runs optimize with `--auto`, which
is where method changes no script checks get found. `upgrade_check.py stamp` writes
`webapp_re_version` into `site.json` and refuses while any other check fails. The stage never asks:
it takes each stage's documented default, sends no live write, and stops the live part of a site at
a login wall or challenge.

## Scripts

| Script | Where | Does | Dependencies |
|---|---|---|---|
| `kb.py` | plugin/scripts | Per-site knowledge base: `init`, `path`, `stats`, `new-run`, `record-finding`, `verify`, `record-pattern`, `index`, `scan-secrets`, `close-run`. Won't record a finding directly as `verified`, only `verify` raises its status. `KB_SITE` and `KB_SLUG` in the environment stand in for `--site` | stdlib |
| `shape.py` | plugin/scripts | JSON response to key names, types, counts and key coverage fractions, without printing any values. Takes the file as an argument or on stdin | stdlib |
| `walk_summary.py` | plugin/scripts | Folds a scope walk's probe files into one line per page and endpoint, the noise list and the pages left to visit, writes `walk.json`, and with `--draft-scope` a starting `scope.json` | stdlib |
| `scope_query.py` | plugin/scripts | Reads `scope.json` in pieces: an index, `--id`, `--section`, `--grep` | stdlib |
| `replay.py` | plugin/scripts | Sends a request saved by `reverse-export.js` from outside the browser. `--set` changes one input, `--consume` deletes the saved file afterwards because it holds live values. Prints the status, header names and response shape | stdlib |
| `cdp_capture.py` | plugin/scripts | One capture window over CDP against an already-running Chromium. Opens its own tab at about:blank, enables Network, then navigates, so the cold load is inside the window. Redacts credential headers and token-like body fields at the writer. Closes only its own tab | `websockets>=12` |
| `capture-hook.js` | plugin/assets | Page hook that wraps fetch and XHR, keeps up to 200 records with bodies up to 65536 chars, exposes `window.__reCaptureDump({match})`. Request header values stay in page memory so the ablation can resend them, and a dump never prints them | none |
| `scope-probe.js`, `scope-paginate.js` | plugin/assets | The scope walk's per-page probe and its pagination check, run through `evaluate_script` with the result saved to a file | none |
| `reverse-capture.js`, `reverse-ablate.js`, `reverse-export.js` | plugin/assets | The reverse fast path: rank the captured calls with secrets redacted, ablate the target in one call, and save the minimal request for `replay.py` | none |
| `check_scope.py` | plugin/scripts | Validates `scope.json`: structure, unique ids, cross-references, secret-looking values | stdlib |
| `check_plan.py` | plugin/scripts | Validates a plan against its scope: kebab-case names, schemas, confirmation rule on writes, dependencies exist, build order covers every command once | stdlib |
| `optimize_run.py` | plugin/scripts | Optimize runs: `new-run`, `latest`, `snapshot`, `compare`, `measure`, `validate`, `report`, `revalidate`, `partition`, `backup`, `result` | stdlib |
| `upgrade_check.py` | plugin/scripts | Upgrade audit of one site or all (`audit`), the mechanical fixes (`fix`: `browser_path`, `site_plugin.py scaffold`), and the version stamp (`stamp`, refused while a check fails). Runs each program with its own `.venv` so a shell-wide `UV_PROJECT_ENVIRONMENT` is never touched | stdlib |
| `site_plugin.py` | plugin/scripts | Site plugins: `scaffold` writes `<root>/plugin/` (manifest, launcher, `help` and `menu` entries, normalized main skill) and the marketplace entry, `check` validates one site or all, `marketplace [--check]` writes or compares the manifest, `status` lists sites. `kb.py init` calls `scaffold` for a new site | stdlib |
| `optimize-audit.js`, `optimize-apply.js` | plugin/assets | The audit and apply scripts the optimize stage hands to Claude Code's Workflow tool, which runs several subagents from one script | none |

All run with `uv run --script <path>`. The fixtures they are checked against are described in
[../tests/README.md](../tests/README.md).

## Slugs

The slug is the registrable domain without its public suffix: `app.example.com` and
`www.example.com` become `example`, `bbc.co.uk` becomes `bbc`. `kb.py` carries a small built-in
list of two-part suffixes, which is not the full public suffix list, so `--slug` overrides it.
The slug names the workspace directory, the site plugin, its main skill and its slash commands.
