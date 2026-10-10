#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Mechanical parts of /webapp-re:optimize.

    uv run --script optimize_run.py new-run --root ~/dev/webapp-re/apps/<slug>
    uv run --script optimize_run.py latest --root ~/dev/webapp-re/apps/<slug>
    uv run --script optimize_run.py snapshot --out <run-dir>/snapshot-before.json --path <root>
    uv run --script optimize_run.py compare --before <run-dir>/snapshot-before.json --allow <run-dir>
    uv run --script optimize_run.py measure --root <root> --out <run-dir>/baseline.json --root-env <NAME>
    uv run --script optimize_run.py validate <run-dir>/findings.json
    uv run --script optimize_run.py report --run-dir <run-dir>
    uv run --script optimize_run.py revalidate <run-dir>/findings.json
    uv run --script optimize_run.py partition <run-dir>/findings.json --ids F01,F02 [--size 5] [--max 8] > <run-dir>/partitions.json
    uv run --script optimize_run.py backup --dest <run-dir>/before --path <file or directory>
    uv run --script optimize_run.py result --run-dir <run-dir> --after <run-dir>/after.json

The findings.json format is documented in references/optimize-format.md. Stdlib only.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import Counter
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
RUN_ID_PATTERN = re.compile(r"run-\d{4}-\d{2}-\d{2}-\d{6}")
FINDING_ID_PATTERN = re.compile(r"F\d{2,}")
DIMENSIONS = ("speed", "stability", "scope", "correctness", "safety", "skill-quality", "other")
SEVERITIES = ("critical", "high", "medium", "low")
VERDICTS = ("confirmed", "plausible", "refuted")
OUTCOMES = ("fixed", "skipped", "no-change-needed")
KEPT_VERDICTS = ("confirmed", "plausible")
FINDING_FIELDS = {
   "id": str,
   "dimension": str,
   "target": str,
   "title": str,
   "file": str,
   "line": (int, type(None)),
   "anchor": str,
   "evidence": str,
   "severity": str,
   "verdict": str,
   "verify_note": str,
   "proposed_fix": str,
   "expected_effect": str,
   "needs_live_write": bool,
   "files_touched": list,
}
TOP_LEVEL_FIELDS = {
   "format": int,
   "site": str,
   "run_id": str,
   "created": str,
   "targets": dict,
   "live_budget": int,
   "live_requests_spent": int,
   "findings": list,
}
SEVERITY_RANK = {name: rank for rank, name in enumerate(SEVERITIES)}


def stamp():
   return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def expand(path_text):
   return Path(os.path.expanduser(path_text)).resolve()


def read_json(path):
   with open(path, encoding="utf-8") as handle:
      return json.load(handle)


def write_json(path, value):
   Path(path).parent.mkdir(parents=True, exist_ok=True)

   with open(path, "w", encoding="utf-8") as handle:
      json.dump(value, handle, indent=3)
      handle.write("\n")


def command_new_run(args):
   root = expand(args.root)
   has_site = (root / "site.json").exists()

   if not has_site:
      sys.exit("optimize: no site.json at {0}".format(root))

   run_dir = root / "optimize" / "run-{0}".format(stamp())
   run_dir.mkdir(parents=True, exist_ok=False)
   print(run_dir)


def runs_with_findings(root):
   optimize_dir = root / "optimize"

   if not optimize_dir.is_dir():
      return []

   candidates = [entry for entry in optimize_dir.iterdir() if RUN_ID_PATTERN.fullmatch(entry.name)]

   return sorted(entry for entry in candidates if (entry / "findings.json").exists())


def command_latest(args):
   runs = runs_with_findings(expand(args.root))

   if not runs:
      sys.exit("optimize: no run with findings.json under {0}/optimize".format(expand(args.root)))

   print(runs[-1])


def file_digest(path):
   digest = hashlib.sha256()

   with open(path, "rb") as handle:
      for block in iter(lambda: handle.read(1 << 20), b""):
         digest.update(block)

   return digest.hexdigest()


def take_snapshot(paths):
   files = {}

   for base in paths:
      for directory, _, names in os.walk(base):
         for name in names:
            file_path = os.path.join(directory, name)
            is_regular = os.path.isfile(file_path) and not os.path.islink(file_path)

            if not is_regular:
               continue

            details = os.stat(file_path)
            files[file_path] = {"size": details.st_size, "mtime_ns": details.st_mtime_ns, "sha256": file_digest(file_path)}

   return files


def command_snapshot(args):
   paths = [str(expand(path)) for path in args.path]
   snapshot = {"created": datetime.now().isoformat(timespec="seconds"), "paths": paths, "files": take_snapshot(paths)}
   write_json(args.out, snapshot)
   print("snapshot: {0} files under {1} paths -> {2}".format(len(snapshot["files"]), len(paths), args.out))


def command_compare(args):
   before = read_json(args.before)
   after_files = read_json(args.after)["files"] if args.after else take_snapshot(before["paths"])
   before_files = before["files"]
   allowed_prefixes = [str(expand(prefix)) + os.sep for prefix in args.allow or []]
   changes = []

   for file_path in sorted(set(before_files) | set(after_files)):
      old = before_files.get(file_path)
      new = after_files.get(file_path)

      if old is None:
         kind = "added"
      elif new is None:
         kind = "removed"
      elif old["sha256"] != new["sha256"]:
         kind = "content changed"
      elif old["mtime_ns"] != new["mtime_ns"]:
         kind = "timestamp changed"
      else:
         continue

      is_allowed = any(file_path.startswith(prefix) for prefix in allowed_prefixes)
      changes.append((file_path, kind, is_allowed))

   for file_path, kind, is_allowed in changes:
      print("{0}: {1}{2}".format(file_path, kind, " (allowed)" if is_allowed else ""))

   outside = [change for change in changes if not change[2]]
   inside = [change for change in changes if change[2]]
   print("compare: {0} files before, {1} after; {2} changed outside allowed paths, {3} inside".format(
      len(before_files), len(after_files), len(outside), len(inside)))
   sys.exit(1 if outside else 0)


def console_and_package(program_dir):
   with open(program_dir / "pyproject.toml", "rb") as handle:
      project = tomllib.load(handle).get("project", {})

   scripts = project.get("scripts", {})

   if not scripts:
      return None, None

   console_name, target = next(iter(scripts.items()))
   module_path = target.split(":")[0]

   return console_name, module_path


def run_timed(command, cwd, env):
   started = time.monotonic()
   completed = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
   elapsed_ms = int((time.monotonic() - started) * 1000)

   return completed, elapsed_ms


def last_line(text):
   lines = [line for line in text.strip().splitlines() if line.strip()]

   return lines[-1] if lines else ""


def gate_metric(name, command, cwd, env):
   completed, elapsed_ms = run_timed(command, cwd, env)
   summary = last_line(completed.stdout) or last_line(completed.stderr)

   return {"name": name, "value": completed.returncode, "unit": "exit code", "seconds": round(elapsed_ms / 1000, 2),
           "detail": summary, "command": " ".join(command)}


def median_ms(command, cwd, env, repeat):
   samples = []

   for _ in range(repeat):
      completed, elapsed_ms = run_timed(command, cwd, env)

      if completed.returncode != 0:
         return None, last_line(completed.stderr)

      samples.append(elapsed_ms)

   return int(statistics.median(samples)), "samples {0}".format(samples)


def import_cumulative_ms(stderr_text, module_path):
   for line in stderr_text.splitlines():
      parts = [part.strip() for part in line.split("|")]
      is_module_line = len(parts) == 3 and parts[2] == module_path

      if is_module_line:
         return round(int(parts[1]) / 1000, 1)

   return None


def command_measure(args):
   root = expand(args.root)
   program_dir = root / "program"
   uv_project = ["uv", "run", "--frozen", "--no-sync", "--project", str(program_dir)]
   env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", UV_PROJECT_ENVIRONMENT=str(program_dir / ".venv"))
   sandbox = tempfile.mkdtemp(prefix="optimize-root-")
   cli_env = dict(env)
   metrics = []

   if args.root_env:
      cli_env[args.root_env] = sandbox

   try:
      if program_dir.is_dir():
         metrics.append(gate_metric("tests", uv_project + ["pytest", "-q", "-p", "no:cacheprovider"], program_dir, env))
         passed = re.search(r"(\d+) passed", metrics[-1]["detail"])
         metrics.append({"name": "tests passed", "value": int(passed.group(1)) if passed else None, "unit": "tests"})
         metrics.append({"name": "tests wall time", "value": metrics[-2]["seconds"], "unit": "s"})

         has_provenance_gate = (program_dir / "scripts" / "check_provenance.py").exists()
         if has_provenance_gate:
            metrics.append(gate_metric("provenance gate", uv_project + ["python", "scripts/check_provenance.py"], program_dir, env))

         console_name, module_path = console_and_package(program_dir)

         if console_name:
            startup, detail = median_ms(uv_project + [console_name, "--help"], program_dir, cli_env, args.repeat)
            metrics.append({"name": "cli --help wall time, median", "value": startup, "unit": "ms", "detail": detail})

            if args.root_env:
               help_ms, detail = median_ms(uv_project + [console_name, "help"], program_dir, cli_env, args.repeat)
               metrics.append({"name": "cli help command wall time, median", "value": help_ms, "unit": "ms", "detail": detail})

            completed, _ = run_timed(uv_project + ["python", "-X", "importtime", "-c", "import " + module_path], program_dir, cli_env)
            metrics.append({"name": "import time of " + module_path, "value": import_cumulative_ms(completed.stderr, module_path), "unit": "ms"})

      scope_file = root / "scope" / "scope.json"
      if scope_file.exists():
         metrics.append(gate_metric("check_scope", ["uv", "run", "--script", str(SKILL_ROOT / "scripts" / "check_scope.py"), str(scope_file)], root, env))

      plan_file = root / "plan" / "plan.json"
      if plan_file.exists():
         metrics.append(gate_metric("check_plan", ["uv", "run", "--script", str(SKILL_ROOT / "scripts" / "check_plan.py"), str(root)], root, env))

      plugin_dir = root / "plugin"
      if plugin_dir.is_dir():
         metrics.append(gate_metric("site plugin check", ["uv", "run", "--script", str(SKILL_ROOT / "scripts" / "site_plugin.py"), "check", "--site", str(root)], root, env))

         if shutil.which("claude"):
            metrics.append(gate_metric("claude plugin validate", ["claude", "plugin", "validate", str(plugin_dir), "--strict"], root, env))
   finally:
      shutil.rmtree(sandbox, ignore_errors=True)

   result = {"measured_at": datetime.now().isoformat(timespec="seconds"), "root": str(root),
             "root_env": args.root_env, "metrics": metrics, "live": {"budget": args.live_budget, "spent": 0, "commands": []}}

   if args.out:
      write_json(args.out, result)

   for metric in metrics:
      print("{0}: {1} {2}{3}".format(metric["name"], metric["value"], metric["unit"], "  " + metric["detail"] if metric.get("detail") else ""))

   print("measure: {0} metrics{1}".format(len(metrics), " -> " + args.out if args.out else ""))


def anchor_found(file_path, line, anchor):
   if not anchor:
      return True

   try:
      lines = Path(file_path).read_text(encoding="utf-8", errors="replace").splitlines()
   except OSError:
      return False

   if line is None:
      return anchor in "\n".join(lines)

   window = "\n".join(lines[max(0, line - 6):line + 5])

   return anchor in window


def finding_problems(finding, position):
   problems = []
   label = finding.get("id", "#{0}".format(position))

   for field, expected in FINDING_FIELDS.items():
      if field not in finding:
         problems.append("{0}: missing {1}".format(label, field))
         continue

      has_wrong_type = not isinstance(finding[field], expected) or (expected is not bool and isinstance(finding[field], bool))
      if has_wrong_type:
         problems.append("{0}: {1} has the wrong type".format(label, field))

   if problems:
      return problems

   enum_checks = (("dimension", DIMENSIONS), ("severity", SEVERITIES), ("verdict", VERDICTS))
   for field, allowed in enum_checks:
      if finding[field] not in allowed:
         problems.append("{0}: {1} {2!r} not one of {3}".format(label, field, finding[field], ", ".join(allowed)))

   if not FINDING_ID_PATTERN.fullmatch(finding["id"]):
      problems.append("{0}: id must look like F01".format(label))

   empty_text_fields = [field for field in ("target", "title", "evidence", "verify_note", "proposed_fix", "expected_effect") if not finding[field].strip()]
   problems += ["{0}: {1} is empty".format(label, field) for field in empty_text_fields]

   has_file = bool(finding["file"].strip())
   file_path = expand(finding["file"]) if has_file else None
   file_missing = has_file and not file_path.exists()
   line_out_of_range = has_file and not file_missing and finding["line"] is not None and (finding["line"] < 1 or finding["line"] > len(file_path.read_text(encoding="utf-8", errors="replace").splitlines()))

   if file_missing:
      problems.append("{0}: file {1} does not exist".format(label, finding["file"]))

   if line_out_of_range:
      problems.append("{0}: line {1} is outside {2}".format(label, finding["line"], finding["file"]))

   not_yet_applied = "outcome" not in finding
   anchor_should_hold = has_file and not file_missing and finding["verdict"] in KEPT_VERDICTS and not_yet_applied
   if anchor_should_hold and not anchor_found(file_path, finding["line"], finding["anchor"]):
      problems.append("{0}: anchor not found near {1}:{2}".format(label, finding["file"], finding["line"]))

   if "outcome" in finding:
      outcome_invalid = finding["outcome"] not in OUTCOMES
      reason_missing = finding["outcome"] in ("skipped", "no-change-needed") and not str(finding.get("outcome_reason", "")).strip()

      if outcome_invalid:
         problems.append("{0}: outcome {1!r} not one of {2}".format(label, finding["outcome"], ", ".join(OUTCOMES)))

      if reason_missing:
         problems.append("{0}: outcome {1} needs an outcome_reason".format(label, finding["outcome"]))

   return problems


def validate_document(path):
   document = read_json(path)
   problems = []

   for field, expected in TOP_LEVEL_FIELDS.items():
      if not isinstance(document.get(field), expected):
         problems.append("top level: {0} missing or wrong type".format(field))

   if problems:
      return document, problems

   run_dir_name = Path(path).resolve().parent.name
   run_id_mismatch = document["run_id"] != run_dir_name
   overspent = document["live_requests_spent"] > document["live_budget"]

   if not RUN_ID_PATTERN.fullmatch(document["run_id"]):
      problems.append("top level: run_id {0!r} is not run-YYYY-MM-DD-HHMMSS".format(document["run_id"]))

   if run_id_mismatch:
      problems.append("top level: run_id {0} does not match its directory {1}".format(document["run_id"], run_dir_name))

   if overspent:
      problems.append("top level: live_requests_spent {0} exceeds live_budget {1}".format(document["live_requests_spent"], document["live_budget"]))

   identifiers = Counter(finding.get("id") for finding in document["findings"] if isinstance(finding, dict))
   problems += ["duplicate id {0}".format(identifier) for identifier, count in identifiers.items() if count > 1]

   for position, finding in enumerate(document["findings"], start=1):
      if not isinstance(finding, dict):
         problems.append("#{0}: not an object".format(position))
         continue

      problems += finding_problems(finding, position)

   return document, problems


def command_validate(args):
   document, problems = validate_document(args.findings)

   for problem in problems:
      print(problem)

   findings = document.get("findings", []) if isinstance(document.get("findings"), list) else []
   verdicts = Counter(finding.get("verdict") for finding in findings if isinstance(finding, dict))
   print("findings.json: {0} findings ({1} confirmed, {2} plausible, {3} refuted); {4} problems".format(
      len(findings), verdicts["confirmed"], verdicts["plausible"], verdicts["refuted"], len(problems)))
   sys.exit(1 if problems else 0)


def kept(findings):
   ranked = [finding for finding in findings if finding["verdict"] in KEPT_VERDICTS]

   return sorted(ranked, key=lambda finding: (SEVERITY_RANK[finding["severity"]], finding["verdict"] != "confirmed", finding["id"]))


def location(finding):
   if not finding["file"]:
      return "no file"

   return "{0}:{1}".format(finding["file"], finding["line"]) if finding["line"] else finding["file"]


def metrics_table(metrics):
   lines = ["| Metric | Value | Unit | Detail |", "|---|---|---|---|"]

   for metric in metrics:
      detail = str(metric.get("detail", "")).replace("|", "/")
      lines.append("| {0} | {1} | {2} | {3} |".format(metric["name"], metric["value"], metric["unit"], detail))

   return lines


def command_report(args):
   run_dir = expand(args.run_dir)
   document, problems = validate_document(run_dir / "findings.json")

   if problems:
      sys.exit("optimize: findings.json has {0} problems, run validate".format(len(problems)))

   baseline_path = run_dir / "baseline.json"
   baseline = read_json(baseline_path) if baseline_path.exists() else {"metrics": []}
   findings = document["findings"]
   kept_findings = kept(findings)
   refuted = [finding for finding in findings if finding["verdict"] == "refuted"]
   severity_counts = Counter(finding["severity"] for finding in kept_findings)
   dimension_counts = Counter(finding["dimension"] for finding in kept_findings)
   live_write_count = sum(1 for finding in kept_findings if finding["needs_live_write"])

   lines = [
      "# Optimize audit, {0}, {1}".format(document["site"], document["run_id"]), "",
      "Targets: skills {0}; commands {1}; program {2}.".format(
         ", ".join(document["targets"].get("skills", [])) or "none",
         ", ".join(document["targets"].get("commands", [])) or "all",
         document["targets"].get("program", "none")),
      "Live reads: {0} spent of a budget of {1}.".format(document["live_requests_spent"], document["live_budget"]),
      "", "## Counts", "",
      "{0} findings kept after the verify pass ({1} confirmed, {2} plausible), {3} refuted and dropped.".format(
         len(kept_findings), sum(1 for finding in kept_findings if finding["verdict"] == "confirmed"),
         sum(1 for finding in kept_findings if finding["verdict"] == "plausible"), len(refuted)),
      "", "| Severity | Count |", "|---|---|",
   ]
   lines += ["| {0} | {1} |".format(severity, severity_counts[severity]) for severity in SEVERITIES]
   lines += ["", "| Dimension | Count |", "|---|---|"]
   lines += ["| {0} | {1} |".format(dimension, dimension_counts[dimension]) for dimension in DIMENSIONS]
   lines += ["", "{0} of the kept findings need a live write to verify their fix.".format(live_write_count)]

   workflow = document.get("workflow")
   if workflow:
      lines += ["", "Workflow: {0} reviewers ({1} failed), {2} exact duplicates merged, {3} findings left out by the per-reviewer cap, {4} without a verdict.".format(
         workflow.get("reviewers"), workflow.get("reviewers_failed"), workflow.get("duplicates_merged"), workflow.get("omitted_by_cap"), workflow.get("unverified"))]
   for note in document.get("notes", []):
      lines += ["", "Note: {0}".format(note)]

   lines += ["", "## Baseline", ""] + metrics_table(baseline.get("metrics", []))

   live = baseline.get("live", {})
   if live.get("skipped_reason"):
      lines += ["", "Live reads skipped: {0}".format(live["skipped_reason"])]

   lines += ["", "## Findings", ""]

   for finding in kept_findings:
      lines += [
         "### {0} {1}".format(finding["id"], finding["title"]), "",
         "{0}, {1}, {2}. Target `{3}`, at `{4}`.".format(finding["severity"], finding["dimension"], finding["verdict"], finding["target"], location(finding)), "",
         "Evidence: {0}".format(finding["evidence"]), "",
         "Verify pass: {0}".format(finding["verify_note"]), "",
         "Fix: {0}".format(finding["proposed_fix"]), "",
         "Expected effect: {0}{1}".format(finding["expected_effect"], " Needs a live write to verify." if finding["needs_live_write"] else ""), "",
      ]

   if refuted:
      lines += ["## Refuted by the verify pass", ""]
      lines += ["- {0} {1}: {2}".format(finding["id"], finding["title"], finding["verify_note"]) for finding in refuted]
      lines.append("")

   lines += ["## Next", "", "`/webapp-re:optimize {0} --apply {1}` applies the kept findings.".format(document["site"], document["run_id"])]

   report_path = run_dir / "report.md"
   report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
   print(report_path)


def command_revalidate(args):
   document, problems = validate_document(args.findings)
   structural = [problem for problem in problems if "anchor not found" not in problem and "does not exist" not in problem and "is outside" not in problem]

   if structural:
      sys.exit("optimize: findings.json has structural problems, run validate")

   wanted = set(args.ids.split(",")) if args.ids else None
   held = []
   gone = []

   for finding in kept(document["findings"]):
      is_unwanted = wanted is not None and finding["id"] not in wanted
      if is_unwanted:
         continue

      has_file = bool(finding["file"])
      file_present = has_file and expand(finding["file"]).exists()
      still_holds = not has_file or (file_present and anchor_found(expand(finding["file"]), finding["line"], finding["anchor"]))
      (held if still_holds else gone).append(finding["id"])
      print("{0}: {1}".format(finding["id"], "holds" if still_holds else "anchor gone, drop or re-audit"))

   print("revalidate: {0} hold, {1} gone".format(len(held), len(gone)))


def finding_files(finding):
   listed = [path for path in finding["files_touched"] if path.strip()]
   paths = listed or [finding["file"]]

   return {str(expand(path)) for path in paths if path.strip()}


def cluster_by_shared_files(finding_ids, files_by_id, size_cap):
   document_frequency = Counter(path for finding_id in finding_ids for path in files_by_id[finding_id])
   affinity = {}

   for first in finding_ids:
      for second in finding_ids:
         shared = files_by_id[first] & files_by_id[second]
         affinity[first, second] = sum(1 / document_frequency[path] for path in shared)

   clusters = [[finding_id] for finding_id in finding_ids]

   while True:
      best_pair = None
      best_score = 0

      for first_index, first in enumerate(clusters):
         for second_index in range(first_index + 1, len(clusters)):
            second = clusters[second_index]
            fits = len(first) + len(second) <= size_cap
            if not fits:
               continue

            pair_count = len(first) * len(second)
            score = sum(affinity[left, right] for left in first for right in second) / pair_count
            if score > best_score:
               best_pair = (first_index, second_index)
               best_score = score

      if best_pair is None:
         return clusters

      first_index, second_index = best_pair
      clusters[first_index] = sorted(clusters[first_index] + clusters[second_index])
      del clusters[second_index]


def merge_smallest_until(clusters, size_cap, should_continue):
   while should_continue():
      by_size = sorted(clusters, key=lambda cluster: (len(cluster), cluster))
      pairs = [(first, second) for index, first in enumerate(by_size) for second in by_size[index + 1:] if len(first) + len(second) <= size_cap]

      if not pairs:
         return

      first, second = min(pairs, key=lambda pair: len(pair[0]) + len(pair[1]))
      clusters.remove(first)
      clusters.remove(second)
      clusters.append(sorted(first + second))


def cluster_theme(cluster, files_by_id):
   counts = Counter(path for finding_id in cluster for path in files_by_id[finding_id])
   source_counts = {path: count for path, count in counts.items() if not Path(path).name.startswith("test_")} or counts
   top_path = min(source_counts, key=lambda path: (-source_counts[path], path))
   stem = Path(top_path).stem.lower()

   return re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "misc"


def command_partition(args):
   document, problems = validate_document(args.findings)

   if problems:
      sys.exit("optimize: findings.json has {0} problems, run validate".format(len(problems)))

   has_bad_bounds = args.size < 1 or args.max < 1
   if has_bad_bounds:
      sys.exit("optimize: --size and --max must be at least 1")

   program_text = args.program or document["targets"].get("program", "")
   if not program_text:
      sys.exit("optimize: findings.json has no targets.program, pass --program")

   program_dir = expand(program_text)
   wanted = set(args.ids.split(","))
   chosen = [finding for finding in document["findings"] if finding["id"] in wanted]
   unknown = wanted - {finding["id"] for finding in chosen}

   if unknown:
      sys.exit("optimize: unknown ids {0}".format(", ".join(sorted(unknown))))

   files_by_id = {finding["id"]: finding_files(finding) for finding in chosen}
   program_ids = sorted(finding_id for finding_id, files in files_by_id.items() if any(Path(path).is_relative_to(program_dir) for path in files))
   other_ids = sorted(set(files_by_id) - set(program_ids))
   program_clusters = cluster_by_shared_files(program_ids, files_by_id, args.size)
   other_clusters = cluster_by_shared_files(other_ids, files_by_id, args.size)

   def ceiling_division(numerator, denominator):
      return -(-numerator // denominator)

   def waves_needed(partition_count):
      return ceiling_division(partition_count, args.max)

   fewest_partitions = ceiling_division(len(program_ids), args.size) + ceiling_division(len(other_ids), args.size)
   fewest_waves = waves_needed(fewest_partitions)

   def merging_saves_a_wave():
      return waves_needed(len(program_clusters) + len(other_clusters)) > fewest_waves

   merge_smallest_until(program_clusters, args.size, merging_saves_a_wave)
   merge_smallest_until(other_clusters, args.size, merging_saves_a_wave)

   def cluster_files(cluster):
      return set().union(*(files_by_id[finding_id] for finding_id in cluster))

   all_clusters = program_clusters + other_clusters
   chain = sorted(program_clusters, key=min)
   parallel = []

   for cluster in sorted(other_clusters, key=min):
      own_files = cluster_files(cluster)
      shares_a_file = any(own_files & cluster_files(other) for other in all_clusters if other is not cluster)
      (chain if shares_a_file else parallel).append(cluster)

   waves = [chain[start:start + args.max] for start in range(0, len(chain), args.max)]
   lanes = [["chain"] * len(wave) for wave in waves]

   for cluster in parallel:
      open_waves = [index for index, wave in enumerate(waves) if len(wave) < args.max]

      if not open_waves:
         waves.append([])
         lanes.append([])
         open_waves = [len(waves) - 1]

      waves[open_waves[0]].append(cluster)
      lanes[open_waves[0]].append("parallel")

   output_waves = []
   number = 0

   for wave_index, wave in enumerate(waves):
      partitions = []

      for cluster, lane in zip(wave, lanes[wave_index]):
         number += 1
         theme = cluster_theme(cluster, files_by_id)
         partitions.append({"id": "P{0}-{1}".format(number, theme), "lane": lane, "findings": cluster, "files": sorted(cluster_files(cluster))})

      output_waves.append({"wave": wave_index + 1, "partitions": partitions})

   print(json.dumps({"program_dir": str(program_dir), "size_cap": args.size, "max_per_wave": args.max, "waves": output_waves}, indent=3))

   for wave in output_waves:
      descriptions = ["{0} {1} [{2}]".format(partition["id"], partition["lane"], ",".join(partition["findings"])) for partition in wave["partitions"]]
      print("wave {0}: {1}".format(wave["wave"], "; ".join(descriptions)), file=sys.stderr)

   partition_count = sum(len(wave["partitions"]) for wave in output_waves)
   print("partition: {0} findings ({1} program), {2} partitions in {3} waves".format(len(chosen), len(program_ids), partition_count, len(output_waves)), file=sys.stderr)


def command_backup(args):
   destination = expand(args.dest)
   copied = 0

   for source_text in args.path:
      source = expand(source_text)
      sources = [Path(directory) / name for directory, _, names in os.walk(source) for name in names] if source.is_dir() else [source]

      for file_path in sources:
         is_copyable = file_path.is_file() and not file_path.is_symlink()
         if not is_copyable:
            continue

         target = destination / str(file_path).lstrip(os.sep)
         target.parent.mkdir(parents=True, exist_ok=True)
         shutil.copy2(file_path, target)
         copied += 1

   print("backup: {0} files -> {1}".format(copied, destination))


def command_result(args):
   run_dir = expand(args.run_dir)
   document, problems = validate_document(run_dir / "findings.json")

   if problems:
      sys.exit("optimize: findings.json has {0} problems, run validate".format(len(problems)))

   baseline = read_json(run_dir / "baseline.json")
   after = read_json(args.after)
   after_by_name = {metric["name"]: metric for metric in after["metrics"]}
   lines = ["# Optimize result, {0}, {1}".format(document["site"], document["run_id"]), "", "## Before and after", "",
            "| Metric | Before | After | Unit |", "|---|---|---|---|"]

   for metric in baseline["metrics"]:
      after_metric = after_by_name.get(metric["name"], {})
      lines.append("| {0} | {1} | {2} | {3} |".format(metric["name"], metric["value"], after_metric.get("value", "not measured"), metric["unit"]))

   lines += ["", "## Findings", "", "| Id | Severity | Title | Outcome | Reason |", "|---|---|---|---|---|"]

   for finding in kept(document["findings"]):
      outcome = finding.get("outcome", "not attempted")
      reason = str(finding.get("outcome_reason", "")).replace("|", "/")
      lines.append("| {0} | {1} | {2} | {3} | {4} |".format(finding["id"], finding["severity"], finding["title"], outcome, reason))

   result_path = run_dir / "result.md"
   result_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
   print(result_path)


def build_parser():
   parser = argparse.ArgumentParser(description="Mechanical parts of /webapp-re:optimize")
   commands = parser.add_subparsers(dest="command", required=True)

   new_run = commands.add_parser("new-run")
   new_run.add_argument("--root", required=True)
   new_run.set_defaults(handler=command_new_run)

   latest = commands.add_parser("latest")
   latest.add_argument("--root", required=True)
   latest.set_defaults(handler=command_latest)

   snapshot = commands.add_parser("snapshot")
   snapshot.add_argument("--out", required=True)
   snapshot.add_argument("--path", action="append", required=True)
   snapshot.set_defaults(handler=command_snapshot)

   compare = commands.add_parser("compare")
   compare.add_argument("--before", required=True)
   compare.add_argument("--after", help="a second snapshot; without it the same paths are snapshotted now")
   compare.add_argument("--allow", action="append", help="a directory whose changes are expected")
   compare.set_defaults(handler=command_compare)

   measure = commands.add_parser("measure")
   measure.add_argument("--root", required=True)
   measure.add_argument("--out")
   measure.add_argument("--root-env", help="the program's root override variable, pointed at a throwaway directory")
   measure.add_argument("--repeat", type=int, default=5)
   measure.add_argument("--live-budget", type=int, default=20)
   measure.set_defaults(handler=command_measure)

   validate = commands.add_parser("validate")
   validate.add_argument("findings")
   validate.set_defaults(handler=command_validate)

   report = commands.add_parser("report")
   report.add_argument("--run-dir", required=True)
   report.set_defaults(handler=command_report)

   revalidate = commands.add_parser("revalidate")
   revalidate.add_argument("findings")
   revalidate.add_argument("--ids")
   revalidate.set_defaults(handler=command_revalidate)

   partition = commands.add_parser("partition")
   partition.add_argument("findings")
   partition.add_argument("--ids", required=True)
   partition.add_argument("--max", type=int, default=8, help="partitions per wave; each wave is one apply workflow run")
   partition.add_argument("--size", type=int, default=5, help="findings per partition")
   partition.add_argument("--program", help="the program directory, when findings.json has no targets.program")
   partition.set_defaults(handler=command_partition)

   backup = commands.add_parser("backup")
   backup.add_argument("--dest", required=True)
   backup.add_argument("--path", action="append", required=True)
   backup.set_defaults(handler=command_backup)

   result = commands.add_parser("result")
   result.add_argument("--run-dir", required=True)
   result.add_argument("--after", required=True)
   result.set_defaults(handler=command_result)

   return parser


def main():
   args = build_parser().parse_args()
   args.handler(args)


if __name__ == "__main__":
   main()
