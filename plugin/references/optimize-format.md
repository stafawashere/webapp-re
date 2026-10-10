# Optimize run format

Every `/webapp-re:optimize` run writes one directory, `<root>/optimize/<run-id>/`. The run id has
the `kb.py` format, `run-YYYY-MM-DD-HHMMSS`, and is created by
`${CLAUDE_PLUGIN_ROOT}/scripts/optimize_run.py new-run --root <root>`.

| File | Written in | Holds |
|---|---|---|
| `snapshot-before.json` | phase 1 | Path, size, mtime and sha256 of every file under the site root and the site's skill directories, taken before anything else runs |
| `baseline.json` | phase 1 | Offline gate results, timings and the live-read section |
| `findings.json` | phase 1, outcomes added in phase 2 | The verified findings, shape below |
| `report.md` | phase 1 | The same findings for a person, rendered by `optimize_run.py report` |
| `snapshot-apply.json` | phase 2 | Snapshot from just before any fix |
| `partitions.json` | phase 2 | The waves and partitions the apply workflow runs, from `optimize_run.py partition`, shape below |
| `before/` | phase 2 | Copies of every file a partition may edit and of the program's `tests/`, at their absolute paths |
| `after.json` | phase 2 | The same measurements as `baseline.json`, taken after the fixes |
| `result.md` | phase 2 | Before and after numbers and each finding's outcome, rendered by `optimize_run.py result` |

`optimize_run.py validate <run-dir>/findings.json` checks the shape below and prints one last
line, `findings.json: N findings (a confirmed, b plausible, c refuted); K problems`, exiting 1 when
K is not zero.

## findings.json

```json
{
   "format": 1,
   "site": "<slug>",
   "run_id": "run-2026-10-09-221500",
   "created": "2026-10-09T22:15:00",
   "targets": { "skills": ["<slug>"], "commands": [], "program": "<root>/program" },
   "live_budget": 20,
   "live_requests_spent": 0,
   "workflow": { "reviewers": 7, "reviewers_failed": 0, "duplicates_merged": 0, "omitted_by_cap": 0, "unverified": 0 },
   "findings": [
      {
         "id": "F01",
         "dimension": "speed",
         "target": "fetch-saved-items",
         "title": "Member details fetched one by one",
         "file": "~/dev/webapp-re/apps/<slug>/program/src/<package>/capabilities/saved_items.py",
         "line": 42,
         "anchor": "for member_id in member_ids:",
         "evidence": "What the reviewer read or ran, with numbers",
         "severity": "high",
         "verdict": "confirmed",
         "verify_note": "What the verifier checked",
         "proposed_fix": "What to change",
         "expected_effect": "12 requests become 1, about 33 s saved at the 3 s pacing gap",
         "needs_live_write": false,
         "files_touched": ["~/dev/webapp-re/apps/<slug>/program/src/<package>/capabilities/saved_items.py"]
      }
   ]
}
```

Field rules the validator enforces:

- `run_id` matches `run-YYYY-MM-DD-HHMMSS` and equals the name of the directory holding the file.
- `live_requests_spent` is not above `live_budget`.
- `id` is `F` plus two or more digits and unique. Ids are assigned in severity order.
- `dimension` is one of `speed`, `stability`, `scope`, `correctness`, `safety`, `skill-quality`,
  `other`. `severity` is one of `critical`, `high`, `medium`, `low`. `verdict` is one of
  `confirmed`, `plausible`, `refuted`.
- `target`, `title`, `evidence`, `verify_note`, `proposed_fix` and `expected_effect` are not empty.
- `file`, when not empty, exists, and `line`, when not null, is inside it. For a `confirmed` or
  `plausible` finding with an `anchor`, the anchor appears within five lines of `line`. This is
  what lets phase 2 tell whether a finding still holds. A finding that already carries an `outcome` is
  exempt, because a fix removes the code its anchor quoted.
- `outcome`, added in phase 2, is one of `fixed`, `skipped`, `no-change-needed`, and the last two
  carry an `outcome_reason`.

Refuted findings stay in the file so the report can say what was dropped and why. Phase 2 never
acts on them.

## partitions.json

```json
{
   "program_dir": "<root>/program",
   "size_cap": 5,
   "max_per_wave": 8,
   "waves": [
      {
         "wave": 1,
         "partitions": [
            { "id": "P1-pacing", "lane": "chain", "findings": ["F03", "F05", "F17"], "files": ["<root>/program/src/<package>/pacing.py", "<root>/plugin/skills/<slug>/SKILL.md"] },
            { "id": "P2-skill", "lane": "chain", "findings": ["F15", "F16"], "files": ["<root>/plugin/skills/<slug>/SKILL.md"] },
            { "id": "P3-plan", "lane": "parallel", "findings": ["F31"], "files": ["<root>/plan/plan.md"] }
         ]
      }
   ]
}
```

Paths are written absolute. What the partitioner guarantees:

- Every accepted id appears in exactly one partition, and no partition holds more than `size_cap`.
- Every partition that touches a file under `program_dir` has lane `chain`.
- A `parallel` partition shares no file with any other partition in any wave. A file outside the
  program that a chain partition touches, such as `SKILL.md` or `plan/plan.json`, therefore only
  ever appears in chain partitions.
- A wave holds at most `max_per_wave` partitions, which with the reviewer keeps the apply
  workflow under 10 agents. Chain order runs across waves: program partitions by their highest
  severity finding, then the chain partitions that touch only other files.
- The theme after the number is the stem of the file most of the partition's findings touch. It
  is a label, not a guarantee that the findings are related.

## baseline.json and after.json

Written by `optimize_run.py measure`, then extended by the main session with the live block.

```json
{
   "measured_at": "2026-10-09T22:15:30",
   "root": "<root>",
   "root_env": "<the program's root override variable, or null>",
   "metrics": [
      { "name": "tests", "value": 0, "unit": "exit code", "seconds": 1.4, "detail": "271 passed in 1.33s", "command": "..." },
      { "name": "cli --help wall time, median", "value": 159, "unit": "ms", "detail": "samples [159, 153, 164]" }
   ],
   "live": {
      "budget": 20,
      "spent": 0,
      "skipped_reason": "",
      "commands": [
         { "command": "fetch-saved-items", "exit_code": 0, "duration_ms": 4100, "requests": 2, "items": 12, "schema": "pass" }
      ]
   }
}
```

`measure` runs, without writing into the site tree: the program's tests
(`pytest -q -p no:cacheprovider` with `PYTHONDONTWRITEBYTECODE=1` through
`uv run --frozen --no-sync`), the provenance gate, `check_scope.py`, `check_plan.py`, the median
wall time of `<console> --help` and of the `help` command, and the import time of the CLI module.
CLI timings run with the program's root override pointed at a throwaway directory, so anything
the CLI writes lands there. The tests run against the real root, because they read the knowledge
base and the rendered spec. `result` matches metrics between the two files by `name`.

## report.md

Rendered from `findings.json` and `baseline.json`: targets, live reads spent against the budget,
counts by severity and by dimension, the baseline table, every kept finding with its evidence,
verify note, fix and expected effect, the refuted list, and the command that applies the run.

## result.md

Rendered from `findings.json` (with outcomes), `baseline.json` and `after.json`: a before and after
table per metric, then one row per kept finding with its outcome and reason. The main session
adds below it the gate outputs it quoted, the live checks run, the queued live writes and their
approvals, and the list of changed files from `optimize_run.py compare`.
