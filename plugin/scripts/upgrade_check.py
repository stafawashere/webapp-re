#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Audit a site workspace against the installed webapp-re, and bring the mechanical parts up to date.
    uv run --script upgrade_check.py audit --site <slug, root or all> [--json OUT] [--skip-tests]
    uv run --script upgrade_check.py fix --site <slug or root>
    uv run --script upgrade_check.py stamp --site <slug or root>
audit exits 0 when the site is current, 1 when something is out of date, 2 on bad arguments.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
DEFAULT_HOME = "~/dev/webapp-re/apps"
STAGE_ORDER = ["fix", "secrets", "scope", "plan", "engineer", "integrate-menu", "optimize", "stamp"]
TEMPLATE_SECTIONS = ["## Commands", "## Errors", "## Provenance"]
TEMPLATE_EXIT_CODES = ["10", "11", "12", "13", "14", "15", "16"]
STATUS_PREFIXES = ("verified live", "local", "built, not verified", "blocked")
LEGACY_BROWSER_MARKERS = ["mcp__claude-in-chrome", "read_network_requests", "javascript_tool", "tabs_context_mcp"]
TEST_TIMEOUT_SECONDS = 600
COMMAND_ROW = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def current_version():
   manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
   return manifest.get("version", "")


def webapp_re_home():
   return Path(os.environ.get("WEBAPP_RE_HOME", DEFAULT_HOME)).expanduser()


def read_json(path, fallback=None):
   try:
      return json.loads(Path(path).read_text(encoding="utf-8"))
   except (OSError, ValueError):
      return fallback


def write_json(path, document):
   Path(path).write_text(json.dumps(document, indent=3, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_roots(site):
   if site == "all":
      return sorted(path.parent for path in webapp_re_home().glob("*/site.json"))

   given_path = Path(site).expanduser()

   if (given_path / "site.json").is_file():
      return [given_path.resolve()]

   root = webapp_re_home() / site

   if not (root / "site.json").is_file():
      raise SystemExit(f"upgrade_check: no site.json for {site!r} under {webapp_re_home()}")

   return [root]


def program_environment(program):
   environment = dict(os.environ)
   environment.pop("VIRTUAL_ENV", None)
   environment["UV_PROJECT_ENVIRONMENT"] = str(program / ".venv")
   return environment


def run(argv, cwd=None, timeout=300, environment=None):
   try:
      completed = subprocess.run(argv, cwd=cwd, env=environment, capture_output=True, text=True, timeout=timeout)
   except subprocess.TimeoutExpired:
      return 124, f"timed out after {timeout} s"
   except FileNotFoundError as error:
      return 127, str(error)

   output = (completed.stderr + "\n" + completed.stdout).strip()
   return completed.returncode, output


def last_line(text):
   lines = [line for line in text.splitlines() if line.strip()]
   return lines[-1][:300] if lines else ""


def plugin_script(name):
   return [sys.executable, str(SCRIPTS / name)]


def item(check_id, ok, detail, action="none"):
   return {"id": check_id, "ok": ok, "detail": detail, "action": "none" if ok else action}


def check_stamp(site, version):
   stamped = site.get("webapp_re_version", "")
   is_current = stamped == version
   detail = f"built with {stamped or 'an unstamped version'}, installed is {version}"
   return item("stamp", is_current, detail, "stamp")


def check_browser_path(site):
   browser_path = site.get("browser_path", "")
   is_legacy = browser_path == "claude-in-chrome"
   return item("browser-path", not is_legacy, f"browser_path is {browser_path or 'unset'}", "fix")


def check_scope(root):
   scope_file = root / "scope" / "scope.json"

   if not scope_file.is_file():
      return item("scope", False, "no scope/scope.json", "scope")

   code, output = run(plugin_script("check_scope.py") + [str(scope_file)])
   return item("scope", code == 0, last_line(output), "scope")


def check_plan(root):
   if not (root / "plan" / "plan.json").is_file():
      return item("plan", False, "no plan/plan.json", "plan")

   code, output = run(plugin_script("check_plan.py") + [str(root)])
   return item("plan", code == 0, last_line(output), "plan")


def check_program(root, skip_tests):
   program = root / "program"

   if not (program / "pyproject.toml").is_file():
      return [item("program", False, "no program/pyproject.toml", "engineer")]

   results = []
   environment = program_environment(program)
   provenance_gate = program / "scripts" / "check_provenance.py"

   if provenance_gate.is_file():
      code, output = run(["uv", "run", "python", "scripts/check_provenance.py"], cwd=program, environment=environment)
      results.append(item("provenance", code == 0, last_line(output), "engineer"))
   else:
      results.append(item("provenance", False, "no program/scripts/check_provenance.py", "engineer"))

   if skip_tests:
      results.append(item("program-tests", True, "skipped"))
      return results

   code, output = run(["uv", "run", "pytest", "-q"], cwd=program, timeout=TEST_TIMEOUT_SECONDS, environment=environment)
   results.append(item("program-tests", code == 0, last_line(output), "engineer"))
   return results


def check_site_plugin(root):
   code, output = run(plugin_script("site_plugin.py") + ["check", "--site", str(root)])
   results = [item("site-plugin", code == 0, last_line(output), "fix")]
   claude_binary = shutil.which("claude")

   if claude_binary is None:
      results.append(item("plugin-validate", True, "skipped, no claude on PATH"))
      return results

   code, output = run([claude_binary, "plugin", "validate", str(root / "plugin"), "--strict"])
   results.append(item("plugin-validate", code == 0, last_line(output), "engineer"))
   return results


def plan_command_names(root):
   plan = read_json(root / "plan" / "plan.json", {}) or {}
   return {command.get("name") for command in plan.get("commands", []) if command.get("name")}


def check_skill_template(root, slug):
   skill_path = root / "plugin" / "skills" / slug / "SKILL.md"

   if not skill_path.is_file():
      return item("skill-template", False, f"no main skill at plugin/skills/{slug}/SKILL.md", "engineer")

   text = skill_path.read_text(encoding="utf-8")
   problems = [f"missing {section}" for section in TEMPLATE_SECTIONS if f"\n{section}" not in text]
   errors_block = text.split("## Errors", 1)[1] if "## Errors" in text else ""
   missing_exits = [code for code in TEMPLATE_EXIT_CODES if f"| {code} |" not in errors_block]

   if missing_exits:
      problems.append(f"errors table lacks exits {', '.join(missing_exits)}")

   planned = plan_command_names(root)
   rows = [COMMAND_ROW.match(line) for line in text.splitlines()]
   rows = [row for row in rows if row and row.group(2).strip() in ("read", "write")]
   unplanned = sorted(row.group(1) for row in rows if planned and row.group(1) not in planned)
   bad_status = sorted(row.group(1) for row in rows if not row.group(3).strip().startswith(STATUS_PREFIXES))

   if unplanned:
      problems.append(f"table rows not in the plan: {', '.join(unplanned[:8])}")

   if bad_status:
      problems.append(f"status outside the template vocabulary: {', '.join(bad_status[:8])}")

   has_writes = any(row.group(2).strip() == "write" for row in rows)
   lacks_writes_section = has_writes and "\n## Writes" not in text

   if lacks_writes_section:
      problems.append("write commands but no ## Writes section")

   detail = "; ".join(problems) if problems else f"{len(rows)} command rows match the template"
   return item("skill-template", not problems, detail, "engineer")


def check_legacy_browser(root):
   hits = []

   for folder in (root / "plugin", root / "program" / "src"):
      if not folder.is_dir():
         continue

      for path in sorted(folder.rglob("*")):
         is_text_file = path.is_file() and path.suffix in (".md", ".py", ".json", ".js")

         if not is_text_file:
            continue

         text = path.read_text(encoding="utf-8", errors="replace")

         for marker in LEGACY_BROWSER_MARKERS:
            if marker in text:
               hits.append(f"{path.relative_to(root)} names {marker}")

   detail = "; ".join(hits[:5]) if hits else "no Claude in Chrome tool names"
   return item("legacy-browser", not hits, detail, "engineer")


def check_menu(root):
   if not (root / "menu" / "hints.json").is_file():
      return item("menu", True, "no menu")

   code, output = run([sys.executable, str(PLUGIN_ROOT / "menu" / "build_menu.py"), "check", "--site", str(root)])
   return item("menu", code == 0, last_line(output), "integrate-menu")


def check_secrets(root):
   code, output = run(plugin_script("kb.py") + ["scan-secrets", "--root", str(root)])
   return item("secrets", code == 0, last_line(output), "secrets")


def audit_site(root, skip_tests=False):
   site = read_json(root / "site.json", {}) or {}
   slug = site.get("slug") or root.name
   version = current_version()
   items = [check_stamp(site, version), check_browser_path(site), check_scope(root), check_plan(root)]
   items += check_program(root, skip_tests)
   items += check_site_plugin(root)
   items += [check_skill_template(root, slug), check_legacy_browser(root), check_menu(root), check_secrets(root)]

   failing_actions = {entry["action"] for entry in items if not entry["ok"]}
   needs_rebuild = bool(failing_actions - {"stamp", "fix", "secrets"})
   version_gap = "stamp" in failing_actions

   if needs_rebuild or version_gap:
      failing_actions.add("optimize")

   if failing_actions:
      failing_actions.add("stamp")

   stages = [stage for stage in STAGE_ORDER if stage in failing_actions]
   return {"site": slug, "root": str(root), "version": version, "current": not stages, "stages": stages, "items": items}


def fix_site(root):
   site_file = root / "site.json"
   site = read_json(site_file, {}) or {}
   done = []

   if site.get("browser_path") == "claude-in-chrome":
      site["browser_path"] = "chrome-devtools"
      write_json(site_file, site)
      done.append("browser_path set to chrome-devtools")

   code, output = run(plugin_script("site_plugin.py") + ["scaffold", "--site", str(root)])
   done.append(f"site_plugin scaffold exit {code}: {last_line(output)}")
   return {"site": site.get("slug") or root.name, "done": done}


def stamp_site(root, skip_tests):
   report = audit_site(root, skip_tests=skip_tests)
   blocking = [entry["id"] for entry in report["items"] if not entry["ok"] and entry["action"] != "stamp"]

   if blocking:
      raise SystemExit(f"upgrade_check: not stamping {report['site']}, still failing: {', '.join(blocking)}")

   site_file = root / "site.json"
   site = read_json(site_file, {}) or {}
   site["webapp_re_version"] = report["version"]
   site["upgraded"] = date.today().isoformat()
   write_json(site_file, site)
   return {"site": report["site"], "stamped": report["version"]}


def print_report(report):
   state = "current" if report["current"] else "outdated, stages: " + " ".join(report["stages"])
   print(f"{report['site']}: {state}")

   for entry in report["items"]:
      mark = "ok  " if entry["ok"] else "FAIL"
      action = "" if entry["ok"] else f"  -> {entry['action']}"
      print(f"   {mark} {entry['id']}: {entry['detail']}{action}")


def main(argv=None):
   parser = argparse.ArgumentParser(description="Audit and upgrade a webapp-re site workspace")
   actions = parser.add_subparsers(dest="action", required=True)

   for action in ("audit", "fix", "stamp"):
      subparser = actions.add_parser(action)
      subparser.add_argument("--site", required=True, help="slug, site root, or all (audit only)")
      subparser.add_argument("--skip-tests", action="store_true", help="skip the program's pytest run")

      if action == "audit":
         subparser.add_argument("--json", help="also write the full report here")

   arguments = parser.parse_args(argv)
   roots = resolve_roots(arguments.site)
   is_many = len(roots) > 1

   if is_many and arguments.action != "audit":
      parser.error(f"{arguments.action} takes one site")

   if arguments.action == "fix":
      print(json.dumps(fix_site(roots[0]), ensure_ascii=False))
      return 0

   if arguments.action == "stamp":
      print(json.dumps(stamp_site(roots[0], arguments.skip_tests), ensure_ascii=False))
      return 0

   with ThreadPoolExecutor(max_workers=min(4, len(roots))) as pool:
      reports = list(pool.map(lambda root: audit_site(root, arguments.skip_tests), roots))

   for report in reports:
      print_report(report)

   if arguments.json:
      document = reports if is_many else reports[0]
      write_json(arguments.json, document)

   outdated = [report["site"] for report in reports if not report["current"]]
   print(f"upgrade: {len(reports)} sites, {len(outdated)} outdated, installed webapp-re {current_version()}")
   return 1 if outdated else 0


if __name__ == "__main__":
   sys.exit(main())
