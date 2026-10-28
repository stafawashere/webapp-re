#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Checks for plugin/scripts/upgrade_check.py on throwaway site workspaces.

    uv run --script tests/test_upgrade_check.py
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

module_spec = importlib.util.spec_from_file_location("upgrade_check", REPO / "plugin" / "scripts" / "upgrade_check.py")
upgrade_check = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(upgrade_check)

GOOD_SKILL = """---
name: demo
description: Automate Demo.
---

# demo

## Commands

| Command | Kind | Status | Does |
|---|---|---|---|
| `help` | read | local | Lists commands |
| `list-items` | read | verified live | Lists items |
| `add-item` | write | built, not verified | Adds an item |

## Writes

`add-item` changes account state.

## Errors

| Exit | Class | What to tell the user |
|---|---|---|
| 10 | SessionExpired | x |
| 11 | ChallengeRequired | x |
| 12 | RateLimited | x |
| 13 | ApiError | x |
| 14 | ContractBroken | x |
| 15 | NotPermitted | x |
| 16 | TransportError | x |

## Provenance

Built from plan.json.
"""

PLAN = {"commands": [{"name": "help"}, {"name": "list-items"}, {"name": "add-item"}]}


def make_site(home, site_fields=None, skill_text=None):
   root = Path(home) / "demo"
   root.mkdir(parents=True)
   (root / "site.json").write_text(json.dumps({"slug": "demo", **(site_fields or {})}), encoding="utf-8")
   (root / "plan").mkdir()
   (root / "plan" / "plan.json").write_text(json.dumps(PLAN), encoding="utf-8")

   if skill_text is not None:
      skill_dir = root / "plugin" / "skills" / "demo"
      skill_dir.mkdir(parents=True)
      (skill_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")

   return root


class SkillTemplateTests(unittest.TestCase):
   def test_skill_that_follows_the_template_passes(self):
      with tempfile.TemporaryDirectory() as home:
         root = make_site(home, skill_text=GOOD_SKILL)
         result = upgrade_check.check_skill_template(root, "demo")

      self.assertTrue(result["ok"], result["detail"])

   def test_missing_exit_codes_send_the_site_to_engineer(self):
      skill_text = GOOD_SKILL.replace("| 16 | TransportError | x |\n", "")

      with tempfile.TemporaryDirectory() as home:
         root = make_site(home, skill_text=skill_text)
         result = upgrade_check.check_skill_template(root, "demo")

      self.assertFalse(result["ok"])
      self.assertEqual(result["action"], "engineer")
      self.assertIn("16", result["detail"])

   def test_status_outside_the_vocabulary_is_named(self):
      skill_text = GOOD_SKILL.replace("| verified live |", "| verified |")

      with tempfile.TemporaryDirectory() as home:
         root = make_site(home, skill_text=skill_text)
         result = upgrade_check.check_skill_template(root, "demo")

      self.assertFalse(result["ok"])
      self.assertIn("list-items", result["detail"])

   def test_row_that_is_not_in_the_plan_is_named(self):
      skill_text = GOOD_SKILL.replace("| `add-item` |", "| `drop-item` |")

      with tempfile.TemporaryDirectory() as home:
         root = make_site(home, skill_text=skill_text)
         result = upgrade_check.check_skill_template(root, "demo")

      self.assertFalse(result["ok"])
      self.assertIn("drop-item", result["detail"])


class AuditAndStampTests(unittest.TestCase):
   def setUp(self):
      self.workspace = tempfile.TemporaryDirectory()
      self.home = Path(self.workspace.name) / "apps"
      self.home.mkdir()
      self.previous_environment = dict(os.environ)
      os.environ["WEBAPP_RE_HOME"] = str(self.home)
      os.environ["WEBAPP_RE_MARKETPLACE"] = self.workspace.name

   def tearDown(self):
      os.environ.clear()
      os.environ.update(self.previous_environment)
      self.workspace.cleanup()

   def test_bare_site_runs_the_stages_in_pipeline_order(self):
      root = make_site(self.home, skill_text=GOOD_SKILL)
      report = upgrade_check.audit_site(root, skip_tests=True)
      stages = report["stages"]

      self.assertFalse(report["current"])
      self.assertEqual(stages, sorted(stages, key=upgrade_check.STAGE_ORDER.index))
      self.assertLess(stages.index("scope"), stages.index("engineer"))
      self.assertEqual(stages[-2:], ["optimize", "stamp"])

   def test_stamp_refuses_while_another_check_fails(self):
      root = make_site(self.home, skill_text=GOOD_SKILL)
      before = (root / "site.json").read_text(encoding="utf-8")

      with self.assertRaises(SystemExit) as raised:
         upgrade_check.stamp_site(root, skip_tests=True)

      self.assertIn("still failing", str(raised.exception))
      self.assertEqual((root / "site.json").read_text(encoding="utf-8"), before)

   def test_fix_moves_a_legacy_browser_path_to_chrome_devtools(self):
      root = make_site(self.home, {"browser_path": "claude-in-chrome"}, skill_text=GOOD_SKILL)
      upgrade_check.fix_site(root)
      site = json.loads((root / "site.json").read_text(encoding="utf-8"))

      self.assertEqual(site["browser_path"], "chrome-devtools")

   def test_program_runs_never_inherit_the_shell_project_environment(self):
      os.environ["UV_PROJECT_ENVIRONMENT"] = "/somewhere/else"
      os.environ["VIRTUAL_ENV"] = "/somewhere/else/.venv"
      environment = upgrade_check.program_environment(Path("/sites/demo/program"))

      self.assertEqual(environment["UV_PROJECT_ENVIRONMENT"], "/sites/demo/program/.venv")
      self.assertNotIn("VIRTUAL_ENV", environment)


if __name__ == "__main__":
   unittest.main()
