---
name: upgrade
description: "Bring a site built by an older webapp-re up to the installed version in one unattended run: audit the site against the current checkers, templates and method, rerun only the stages that are out of date, apply the confirmed optimize findings, and stamp the version. Use when the user runs /webapp-re:upgrade, or asks to upgrade, migrate, refresh or re-engineer a site plugin built by an earlier webapp-re."
argument-hint: "<site slug or all> [--dry-run] [--skip-tests]"
---

# webapp-re upgrade

Plugin root: `${CLAUDE_PLUGIN_ROOT}`. Paths written `${CLAUDE_PLUGIN_ROOT}/...` here and in the reference files are under that directory. The arguments are: $ARGUMENTS

```
/webapp-re:upgrade <site> [--dry-run] [--skip-tests]
/webapp-re:upgrade all [--dry-run]
```

Runs without stopping to ask. The audit decides which stages run, so a site that is already
current costs one script call. `--dry-run` prints the audit and the stages it would run, and
changes nothing.

## Rules

- Everything in [the reverse stage](${CLAUDE_PLUGIN_ROOT}/skills/reverse/SKILL.md) under scope,
  consent and hard rules still applies. Running unattended changes none of it.
- **No live writes.** A write command is rebuilt and tested offline, and keeps its previous
  status. It is listed in the reply as waiting for approval, not run.
- **Never sign in.** A login wall, an expired session (exit 10) or a challenge (exit 11) stops the
  live part of that site. The offline parts still finish, and the reply says what is left.
- **No questions.** Wherever a stage would ask, take its documented default: plan proceeds with
  sensible defaults, engineer stays inside each step's request budget and records the rest as open
  work instead of asking to exceed it, optimize runs with `--auto`, so only confirmed findings
  are applied.
- **Keep what works.** Command names, verified findings and statuses carry over. Extend the scope
  and the plan; never start them over.
- **Never loosen a gate.** A failing test is fixed in the program. The test is changed only when the
  current method says the test itself is wrong, and the reply names it.
- Run every program command through `<root>/plugin/scripts/<slug>` or with
  `UV_PROJECT_ENVIRONMENT=<root>/program/.venv`, never with a bare `uv run --project`, so a
  `UV_PROJECT_ENVIRONMENT` exported in the user's shell is not overwritten.

## Steps

1. **Audit.** `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/upgrade_check.py audit --site <target> --json <root>/var/upgrade/audit-before.json`
   (for `all`, write it next to the sites in `$WEBAPP_RE_HOME/upgrade-audit.json`). Each failing
   check names the stage that fixes it, and `stages` is the ordered list for that site. If every
   site is current, reply with the audit's last line and stop. With `--dry-run`, reply with the
   audit and stop.
2. **One site at a time** for anything that touches the browser or the site. With `all`, take
   the sites in the audit's order and run steps 3 to 9 for each one.
3. **fix.** `upgrade_check.py fix --site <slug>`: sets `browser_path` to `chrome-devtools` when it
   still names the extension, and reruns `site_plugin.py scaffold`, which brings the launcher,
   `help` and `menu` entries, `plugin.json` and the marketplace entry to the current generator.
4. **secrets.** When `kb.py scan-secrets` found values on disk, replace each value with its name and
   length (`len=42`), as in [references/knowledge-base.md](${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md),
   and rerun the scan until it reports 0.
5. **scope**, only when listed. Follow [the scope stage](${CLAUDE_PLUGIN_ROOT}/skills/scope/SKILL.md)
   with the existing `scope.json` as the base. The walk revisits only pages whose patterns are
   missing from it, then `check_scope.py` must pass.
6. **plan**, only when listed or when the scope changed. Follow
   [the plan stage](${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md), extending the existing plan with
   command names kept. `check_plan.py` must pass.
7. **engineer**, only when listed or when the plan changed. Follow
   [the engineer stage](${CLAUDE_PLUGIN_ROOT}/skills/engineer/SKILL.md), limited to what the audit
   named:
   - `program-tests` or `provenance` failing: read the failures, fix the program, rerun until
     both pass. Break one fixed mapping on purpose, watch the test go red, restore it.
   - `program` missing: build it from the plan, as engineer step 3 onward.
   - `skill-template` or `legacy-browser` failing: regenerate the main skill from
     [references/central-skill-template.md](${CLAUDE_PLUGIN_ROOT}/references/central-skill-template.md)
     through the site's renderer when it has one, keeping each command's status, then
     `site_plugin.py scaffold`.
   - `plugin-validate` failing: fix the plugin until `claude plugin validate <root>/plugin --strict`
     passes.
   Live-verify only the read commands whose code changed in this run, within the pacing budget.
   Leave every other status as it was.
8. **integrate-menu**, only when listed. Follow
   [the integrate-menu stage](${CLAUDE_PLUGIN_ROOT}/skills/integrate-menu/SKILL.md) to add hints for
   the commands `build_menu.py check` reports.
9. **optimize** runs whenever anything above ran or the site was built by another version:
   [the optimize stage](${CLAUDE_PLUGIN_ROOT}/skills/optimize/SKILL.md) with `--auto`. Its
   reviewers read the current references, so this is where method changes that no script can
   check get found and fixed.
10. **Close.** Rerun `upgrade_check.py audit --site <slug> --json <root>/var/upgrade/audit-after.json`.
    When the only failing check is `stamp`, run `upgrade_check.py stamp --site <slug>`, which
    refuses while anything else fails and otherwise writes `webapp_re_version` and `upgraded` into
    `site.json`. When something still fails, leave the site unstamped and say why.
11. **Write it down.** Append a dated entry to `<root>/RUN-LOG.md` (create it if missing): the
    version it came from and went to, each failing check and what fixed it, the live request count,
    and what is still open.

## Reply

Per site: the version it came from and the version now stamped (or why it is not stamped), a
before and after table of the audit checks, the stages that ran, the optimize run id with its
applied finding count, the live requests spent, write commands waiting for approval, and the
gate outputs quoted. Mention `/reload-plugins` so the regenerated plugin loads.
