---
name: optimize
description: "Audit a site's plugin, skills and program with a read-only multi-agent workflow, then apply the fixes the user accepts and rerun every gate. Use when the user runs /webapp-re:optimize or asks to optimize, audit, speed up or harden a site skill or plugin (\"optimize my <site> skill\")."
argument-hint: "<site slug> [skill or command names...] [--auto] | <site slug> --apply [run-id]"
---

# webapp-re optimize

Plugin root: `${CLAUDE_PLUGIN_ROOT}`. Paths written `${CLAUDE_PLUGIN_ROOT}/...` here and in the reference files are under that directory. The arguments are: $ARGUMENTS

Target: the site given after the subcommand, then optional skill or command names, then flags.

```
/webapp-re:optimize <site> [skill or command names...] [--auto]
/webapp-re:optimize <site> --apply [run-id] [finding ids...]
```

Fourth stage of the pipeline, run after `engineer` has produced a program and a `/<slug>:` plugin.
Its goal is to make the site's plugin, its skills and the program behind them faster, stronger and better in
every way that matters to the person using them. Phase 1 audits and changes nothing. Phase 2
applies the findings the user accepts. Formats of everything it writes are in
[references/optimize-format.md](${CLAUDE_PLUGIN_ROOT}/references/optimize-format.md). The mechanical parts are
`${CLAUDE_PLUGIN_ROOT}/scripts/optimize_run.py`; run every subcommand of it with `uv run --script`.

## Arguments

- `<site>` is a slug or URL, resolved with
  `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py path --site <site>`. Stop if the root
  has no `program/` and suggest `/webapp-re:engineer <slug>`.
- **No names**: the targets are the site's whole plugin, `<root>/plugin/`: its manifest, the main
  skill `skills/<slug>/`, every other skill under `skills/`, the launcher in `scripts/`, its
  marketplace entry, every command the skills name, and the program they call.
- **Names**: each is matched against the skill directory names, then against the command names
  in `plan/plan.json` and the program's registry. The targets are those skills or commands and
  the program code they reach. An unmatched name stops the stage with the list of valid names.
  Speed and stability live in the program, so the program is always in scope for the commands
  being optimized.
- **`--auto`**, or a plain-language instruction in the same invocation to carry on without
  stopping, runs phase 2 straight after phase 1 on the confirmed findings. Plausible findings are
  never applied without a person choosing them. Without it, phase 1 ends at the ask gate.
- **`--apply [run-id] [ids...]`** skips phase 1 and runs phase 2 on an existing run: the one named,
  or `optimize_run.py latest --root <root>`. With no ids it applies every confirmed and plausible
  finding of that run.

## Rules

- Running `/webapp-re:optimize` is the user's opt-in to the multi-agent workflows below. Each
  workflow stays under 10 agents.
- Load the **workflow-authoring** skill before running or changing either workflow script.
- Everything in [the reverse stage](${CLAUDE_PLUGIN_ROOT}/skills/reverse/SKILL.md) under scope, consent and hard rules applies, and
  everything in [the engineer stage](${CLAUDE_PLUGIN_ROOT}/skills/engineer/SKILL.md) under rules applies to phase 2.
- **Phase 1 writes nothing** outside `<root>/optimize/<run-id>/`: no request that changes the
  site, no edited file, no knowledge base mutation, no `kb.py new-run`. `optimize_run.py compare`
  proves it at the end of the phase.
- **Live requests are reads only**, made one at a time by the main session, never by a workflow
  agent, inside a budget printed before the run starts. The default budget is 20, and the user may
  set another in the invocation. Pacing as in
  [references/pacing-and-safety.md](${CLAUDE_PLUGIN_ROOT}/references/pacing-and-safety.md), which the program applies
  itself. Stop at the first 429, challenge, checkpoint or `SessionExpired`.
- Phase 2 keeps every rule of the engineer stage: session adoption only, every endpoint literal
  backed by a finding verified twice, and a write to the site only after the user approves that
  exact call in chat. Workflow agents cannot ask the user anything, so they make no requests to the
  site at all. A fix whose proof needs a live write is built and tested offline, and its live check
  is queued for the main session.
- Never loosen a test, gate, threshold, tolerance or fixture to make something pass. Load the
  **testing-discipline** skill before writing or changing a test or reporting a check, and prove
  each new test bites by breaking the fix, watching it fail, and restoring it.
- Never print, copy into a finding, or log a cookie, token or other secret value.

## Phase 1, audit

1. **Resolve.** Find the root, read `site.json`, `plan/plan.json`, `scope/scope.json`,
   `knowledge/INDEX.md`, the program's `README.md`, and every target `SKILL.md`. Work out the
   target skill directories and command names.
2. **Open the run and snapshot.**
   `optimize_run.py new-run --root <root>` prints the run directory. Then
   `optimize_run.py snapshot --out <run-dir>/snapshot-before.json --path <root>`; the plugin is inside the root.
3. **Print the budget** before any measurement, in one line: the live read budget, the pacing
   gap, and that the reads come one at a time from this session.
4. **Measure offline.** Look in the program's config for a root override environment variable.
   Then `optimize_run.py measure --root <root> --out <run-dir>/baseline.json --live-budget <n>`,
   adding `--root-env <variable>` when one exists. Quote its output.
5. **Live reads, only when both hold**: the program can run against a throwaway root (the root
   override exists), and the stored session will stay valid for at least 10 more minutes without
   a refresh (read the expiry from the program's `help` session block under the throwaway root, or
   from the session file's expiry claims, printing only the seconds left). A refresh rewrites the
   session file, which phase 1 may not do, and some identity providers rotate refresh tokens, so a
   refresh in a copy could leave the user's stored session invalid. When either fails, make no
   live request and write the reason into `baseline.json` as `live.skipped_reason`.
   When both hold: make a directory with `mktemp -d` outside the site tree, mode 700, copy into it
   the session file and `var/cache/` only, and point the root override at it. Run each targeted
   read command once with its smallest useful input, one at a time, through the program's live
   check script when it has one, or one CLI call per command. Count requests from the request log
   inside the throwaway root, and stop before the next command would pass the budget. Record each
   command's exit code, duration, request count, item count and schema result in
   `baseline.json` under `live.commands`, set `live.spent`, then delete the throwaway directory.
6. **Run the audit workflow** with the Workflow tool:
   `scriptPath` is `${CLAUDE_PLUGIN_ROOT}/assets/optimize-audit.js` (expanded to an absolute
   path), and `args` is an object with `site`, `root`, `program_dir`, `skill_dirs` (absolute),
   `skill_root` (`${CLAUDE_PLUGIN_ROOT}`, expanded), `targets` (`{ "skills": [...], "commands": [...] }`,
   an empty commands list meaning all), `baseline_path`, `audit_date` (today, `YYYY-MM-DD`),
   `findings_cap` (6), and `offline_prefix` (the exact command prefix agents may use,
   `PYTHONDONTWRITEBYTECODE=1 uv run --frozen --no-sync --project <program_dir>`, plus the note to
   pass `-p no:cacheprovider` to pytest). Never tell agents they may run the program's CLI, even
   under a throwaway root: an empty or mistyped override falls back to the real root, and on the
   first run against a real site one agent's `export T=$(mktemp -d) X=$T` left it empty and sent a token
   refresh and a read from the user's session. The script runs seven read-only reviewers, one per
   dimension (speed, stability, scope, correctness, safety, skill quality, and anything else that
   would make the skills better), merges exact duplicates, and sends every finding to two
   adversarial verifiers that try to refute it. Nine agents in all. It returns `findings`, already
   numbered and carrying their verdicts, and `stats`. If the script needs changing for a site,
   keep its shape: no agent writes a file or sends a request, every finding is verified by an
   agent that did not produce it, and the total stays under 10.
7. **Write `findings.json`** in `<run-dir>` from the workflow's return value, adding the top-level
   fields from the format reference and `stats` as `workflow`. Then
   `optimize_run.py validate <run-dir>/findings.json`. If a kept finding's anchor does not match,
   read the file at that line: correct the anchor when the defect is there, otherwise mark the
   finding `refuted` with that reason. Never edit a verdict upward. Rerun until it passes and keep
   its last line for the reply.
8. **Render** `optimize_run.py report --run-dir <run-dir>`.
9. **Prove nothing else changed.**
   `optimize_run.py compare --before <run-dir>/snapshot-before.json --allow <run-dir>`. The run
   directory's own files must appear as allowed changes, which shows the comparison sees new
   files, and nothing may appear outside it. If something does, name it in the reply as a breach
   of the phase 1 rule. When the program's request log changed, quote the lines added during the
   run (method, template, status, time; the log holds no values), find the agent that sent them
   from the workflow transcripts, add the count to `live_requests_spent`, and record the breach
   in a top-level `notes` list in `findings.json` so `report.md` carries it. `.DS_Store` changes
   are Finder metadata and are listed, not hidden.
10. **Summarise and ask.** Show counts by severity and by dimension, the top five kept findings
    (id, severity, target, title, expected effect), the live reads spent against the budget, the
    compare line, and the path to `report.md`. Unless `--auto` applies, ask with AskUserQuestion
    whether to go on to phase 2, with three options: apply all verified findings, choose a subset,
    or stop here. For a subset, list the kept ids with their titles and let the user name them.
    Stop means the run ends; mention `/webapp-re:optimize <slug> --apply <run-id>` for later.

## Phase 2, engineer the fixes

1. **Load the run.** The current run, or the one `--apply` named or `latest` found. Validate its
   `findings.json`. The accepted ids are those the user chose, all confirmed findings under
   `--auto`, or the ids passed to `--apply`.
2. **Revalidate.** `optimize_run.py revalidate <run-dir>/findings.json --ids <ids>`, then read
   each finding that still holds at its file and line and confirm the defect is still there.
   Findings that no longer hold get outcome `skipped` with reason "no longer holds" and are dropped
   from the work.
3. **Snapshot and back up.**
   `optimize_run.py snapshot --out <run-dir>/snapshot-apply.json` with the same paths as phase 1,
   and `optimize_run.py backup --dest <run-dir>/before` with a `--path` for every file in the
   accepted findings' `files_touched` and for the program's `tests/` directory.
4. **Partition.**
   `optimize_run.py partition <run-dir>/findings.json --ids <ids> > <run-dir>/partitions.json`.
   Findings that touch the program are clustered by the files they share, weighting a file by how
   rarely it appears, so a hub such as `transport.py` or `SKILL.md` does not pull everything into
   one partition. Each partition holds at most `--size` findings (5). These partitions get lane
   `chain`. They run one at a time, so they may share files. Findings that touch no program file
   are clustered the same way, and one of those partitions gets lane `parallel` only when none of
   its files appears in any other partition. Otherwise it joins the end of the chain, after the
   program partitions. Partitions are packed into waves of at most `--max` (8), chain partitions
   first in order, and smaller partitions are merged only when that saves a wave. Each wave is one
   run of the apply workflow, and waves run one after another. stderr shows one line per wave and
   a count line, and both go in the reply.
5. **Run the apply workflow** once per wave, in wave order, starting the next only after the
   previous one is settled (step 6). `scriptPath` is
   `${CLAUDE_PLUGIN_ROOT}/assets/optimize-apply.js`, and `args` holds `site`, `root`,
   `program_dir`, `skill_root`, `test_command` (the offline prefix plus `pytest -q -p no:cacheprovider`),
   `backup_dir` (`<run-dir>/before`), and `partitions`, that wave's partitions with their `id`,
   `lane`, `files`, and the full finding objects in place of the ids. Chain partitions run one at a
   time in the given order, because their test runs and deliberate breaks share one package and
   they may share skill or plan files. Parallel partitions run alongside them. The script refuses a
   wave of more than 8 partitions, and a parallel partition that shares a file with any other
   partition. One rules reviewer then diffs every changed file against its backup. At most nine
   agents per wave. It returns `results`, `needs_files`, `failed_partitions`, `changed` and
   `review`.
6. **Settle the workflow's output.** Every rule violation the reviewer reports is fixed in this
   session, or its file is restored from `before/` and the finding marked `skipped`. Findings
   skipped for `needs_files` are applied here, one at a time, by the same rules, or left skipped
   with that reason. Check each `bite_proof` names a red run and a green run.
7. **Rerun every gate.**
   `optimize_run.py measure --root <root> --out <run-dir>/after.json` with the same flags as phase 1,
   which runs the tests, the provenance gate, `check_scope.py`, `check_plan.py`,
   `site_plugin.py check` and `claude plugin validate --strict` on the plugin. A failing gate
   means the code is wrong; fix the code or restore it from `before/`. Quote each gate's last line.
   When the site has `menu/hints.json`, also run
   `${CLAUDE_PLUGIN_ROOT}/menu/build_menu.py check --site <slug>` and resolve any problem; a
   fix that renames or removes a command shows up there as a stale hint.
8. **Live checks.** For each changed read command, the read checks in
   [references/live-verification.md](${CLAUDE_PLUGIN_ROOT}/references/live-verification.md), within a printed budget,
   against the real root (phase 2 may let the program refresh its session). Open a knowledge base run
   with `kb.py new-run --goal "optimize <run-id> live checks"` first, run `kb.py verify` for the
   findings each passing command depends on, and `kb.py close-run` at the end. Repeat any live
   timing phase 1 recorded and add it to `after.json`. Then, for each queued live write, show the
   user the `--dry-run` output and ask for approval of that exact call; send only on a yes.
9. **Regenerate or patch the main skill** from
   [references/central-skill-template.md](${CLAUDE_PLUGIN_ROOT}/references/central-skill-template.md) wherever a
   command's inputs, outputs, readiness or wording changed, keeping command names stable, then run
   `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/site_plugin.py scaffold --site <slug>` and
   `site_plugin.py check --site <slug>`, and the template's checks.
10. **Record outcomes.** Set `outcome` and `outcome_reason` on every accepted finding in
    `findings.json`, validate it, render `optimize_run.py result --run-dir <run-dir> --after <run-dir>/after.json`,
    then append to `result.md` the quoted gate lines, the live checks, the write approvals, and the
    output of `optimize_run.py compare --before <run-dir>/snapshot-apply.json --allow <run-dir>`,
    which lists every file phase 2 changed.

## Reply

After phase 1: the summary from step 10 and the question. After phase 2: a table of findings with
outcome (`fixed`, `skipped: reason`, `no change needed`), the before and after numbers that moved,
each gate's quoted last line, live requests spent against the budget, the files changed, any write
still waiting for approval, and the path to `result.md`.
