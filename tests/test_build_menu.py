#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Checks for plugin/menu/build_menu.py against tests/fixtures/menu-site.

    uv run --script tests/test_build_menu.py
"""

import contextlib
import http.client
import importlib.util
import io
import json
import shutil
import socket
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "menu-site"
HELP_JSON = FIXTURE / "help.json"
SKILL_MD = FIXTURE / "skill" / "SKILL.md"

module_spec = importlib.util.spec_from_file_location("build_menu", REPO / "plugin" / "menu" / "build_menu.py")
build_menu = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(build_menu)


def collect_fixture():
   return build_menu.collect(FIXTURE, HELP_JSON, SKILL_MD)


def command_named(data, name):
   return next(entry for entry in data["commands"] if entry["n"] == name)


class StatusTests(unittest.TestCase):
   def test_status_comes_from_skill_table_not_plan_readiness(self):
      data, _, _ = collect_fixture()
      statuses = {entry["n"]: entry["s"] for entry in data["commands"]}

      self.assertEqual(statuses["help"], "local")
      self.assertEqual(statuses["list-items"], "verified")
      self.assertEqual(statuses["get-item"], "unverified")
      self.assertEqual(statuses["old-planned"], "planned")
      self.assertEqual(data["counts"]["ready"], 4)


class SchemaShapeTests(unittest.TestCase):
   def test_schemas_as_a_command_list_and_help_inputs_as_flags(self):
      with tempfile.TemporaryDirectory() as scratch:
         site = Path(scratch) / "site"
         shutil.copytree(FIXTURE, site)
         help_payload = json.loads((site / "help.json").read_text())

         for command in help_payload["commands"]:
            if command["name"] in ("list-items", "help"):
               command["inputs"] = ["--limit"]

         (site / "help.json").write_text(json.dumps(help_payload))
         schema_dir = site / "program" / "src" / "fixture_client"
         schema_dir.mkdir(parents=True, exist_ok=True)
         listed_schema = {"name": "list-items", "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "description": "Stop after this many items"}, "only_in_schema_list": {"type": "boolean"}}, "required": ["limit"]}}
         (schema_dir / "schemas.json").write_text(json.dumps({"site": "fixture", "commands": [listed_schema]}))

         data, _, problems = build_menu.collect(site, site / "help.json", site / "skill" / "SKILL.md")

      list_items = command_named(data, "list-items")
      field_names = [field["k"] for field in list_items["f"]]

      self.assertEqual(problems, [])
      self.assertIn("limit", field_names)
      self.assertIn("only_in_schema_list", field_names)


class SyncTests(unittest.TestCase):
   def test_hints_for_removed_commands_and_fields_are_reported(self):
      _, warnings, problems = collect_fixture()
      joined = "\n".join(warnings)

      self.assertEqual(problems, [])
      self.assertIn("hint for removed-command, which no longer exists", joined)
      self.assertIn("group main lists removed-command, which no longer exists", joined)
      self.assertIn("get-item field gone_field, which the command no longer takes", joined)

   def test_new_command_without_hints_shows_under_other_with_schema_inputs(self):
      data, warnings, _ = collect_fixture()
      brand_new = command_named(data, "brand-new")
      fields = {field["k"]: field for field in brand_new["f"]}

      self.assertEqual(brand_new["g"], "other")
      self.assertIn("other", [group["key"] for group in data["groups"]])
      self.assertIn("no group for brand-new", "\n".join(warnings))
      self.assertEqual(fields["color"]["t"], "select")
      self.assertEqual(fields["color"]["o"], [["", "red (default)"], ["blue", "blue"]])
      self.assertEqual(fields["loud"]["t"], "toggle")
      self.assertTrue(fields["name"].get("r"))

   def test_datalist_hint_reads_the_source_file_in_rank_order(self):
      data, _, _ = collect_fixture()
      id_field = next(field for field in command_named(data, "save-item")["f"] if field["k"] == "id")

      self.assertEqual(id_field["t"], "datalist")
      self.assertEqual(data["lists"]["items"], [["beta", "Beta item"], ["alpha", "Alpha item"], ["gamma", "Gamma item"]])


class SafetyTests(unittest.TestCase):
   def test_confirmation_flag_is_never_offered(self):
      data, _, _ = collect_fixture()
      save_fields = [field["k"] for field in command_named(data, "save-item")["f"]]
      planned_inputs = command_named(data, "old-planned")["ins"]

      self.assertIn("dry_run", save_fields)
      self.assertNotIn("yes", save_fields)
      self.assertEqual(planned_inputs, ["--target required"])

   def test_markup_in_data_cannot_close_the_script_early(self):
      data, _, _ = collect_fixture()
      widget = build_menu.render_widget(data)
      template = build_menu.TEMPLATE_PATH.read_text(encoding="utf-8")

      self.assertEqual(widget.count("</script>"), template.count("</script>"))
      self.assertNotIn("<!-- x", widget)


class OutputTests(unittest.TestCase):
   def test_parts_rejoin_to_the_widget_and_respect_the_limit(self):
      data, _, _ = collect_fixture()
      widget = build_menu.render_widget(data)
      parts = build_menu.split_parts(widget, limit=500)

      self.assertGreater(len(parts), 3)
      self.assertEqual("".join(parts), widget)
      self.assertTrue(all(len(part) <= 500 for part in parts))


class InstallTests(unittest.TestCase):
   def setUp(self):
      self.temp_dir = Path(tempfile.mkdtemp())
      self.skill_path = self.temp_dir / "SKILL.md"
      shutil.copy(SKILL_MD, self.skill_path)

   def tearDown(self):
      shutil.rmtree(self.temp_dir)

   def test_install_twice_leaves_one_section_and_one_menu_entry(self):
      first = build_menu.install(FIXTURE, self.skill_path)
      second = build_menu.install(FIXTURE, self.skill_path)
      text = self.skill_path.read_text(encoding="utf-8")

      self.assertTrue(first["changed"])
      self.assertFalse(second["changed"])
      self.assertEqual(text.count(build_menu.SECTION_START), 1)
      self.assertEqual(text.count("Commands: help, menu, list-items"), 1)
      self.assertLess(text.index(build_menu.SECTION_START), text.index("## Errors"))
      self.assertIn("build_menu.py build --site menusite", text)

   def test_install_refuses_a_description_over_the_limit(self):
      original = self.skill_path.read_text(encoding="utf-8")
      padded = original.replace("Use when the user runs /menusite.", "Use when " + "x" * 1000 + ".")
      self.skill_path.write_text(padded, encoding="utf-8")

      result = build_menu.install(FIXTURE, self.skill_path)

      self.assertTrue(result["problems"])
      self.assertFalse(result["changed"])
      self.assertEqual(self.skill_path.read_text(encoding="utf-8"), padded)


def page_data(page_path):
   page = Path(page_path).read_text(encoding="utf-8")
   start_tag = '<script type="application/json" id="menu-data">'
   start = page.index(start_tag) + len(start_tag)
   return json.loads(page[start:page.index("</script>", start)])


def without_sync_field(data):
   return {key: value for key, value in data.items() if key != build_menu.SYNC_FIELD}


class SiteCopyTestCase(unittest.TestCase):
   def setUp(self):
      self.temp_dir = Path(tempfile.mkdtemp())
      self.root = self.temp_dir / "menu-site"
      shutil.copytree(FIXTURE, self.root)
      self.help_json = self.root / "help.json"
      self.skill_md = self.root / "skill" / "SKILL.md"

   def tearDown(self):
      shutil.rmtree(self.temp_dir)

   def build(self, mode="page", force=False):
      return build_menu.build(self.root, mode, self.help_json, self.skill_md, force)

   def edit_json(self, path, change):
      loaded = json.loads(path.read_text(encoding="utf-8"))
      change(loaded)
      path.write_text(json.dumps(loaded, indent=3), encoding="utf-8")


class CacheTests(SiteCopyTestCase):
   def test_unchanged_inputs_reuse_the_page_byte_for_byte_without_running_help(self):
      first = self.build()
      first_page = Path(first["files"][0]).read_bytes()
      second = self.build()

      self.assertFalse(first["reused"])
      self.assertTrue(first["help_ran"])
      self.assertTrue(second["reused"])
      self.assertFalse(second["help_ran"])
      self.assertEqual(Path(second["files"][0]).read_bytes(), first_page)

   def test_a_hint_change_rebuilds_but_reuses_the_cached_help(self):
      self.build()
      self.edit_json(self.root / "menu" / "hints.json", lambda hints: hints["commands"]["get-item"].update(summary="Fetch one item"))
      rebuilt = self.build()

      self.assertFalse(rebuilt["reused"])
      self.assertFalse(rebuilt["help_ran"])

   def test_a_program_change_reruns_help(self):
      self.build()
      self.edit_json(self.help_json, lambda help_data: help_data["commands"][0].update(purpose="List every command"))
      rebuilt = self.build()

      self.assertTrue(rebuilt["help_ran"])
      self.assertEqual(page_data(rebuilt["files"][0])["commands"][0]["d"], "List every command")

   def test_old_format_parts_are_removed(self):
      out_dir = self.root / "var" / "menu"
      out_dir.mkdir(parents=True)
      (out_dir / "menu.part-1.html").write_text("old", encoding="utf-8")
      (out_dir / "menu.widget.html").write_text("old", encoding="utf-8")
      self.build()

      self.assertEqual(sorted(path.name for path in out_dir.glob("menu.*")), ["menu.page.html"])


class LiveSyncTests(SiteCopyTestCase):
   def commands(self):
      return {entry["n"]: entry for entry in page_data(self.build()["files"][0])["commands"]}

   def test_each_kind_of_change_shows_up_in_the_next_build(self):
      self.assertIn("removed-command", json.loads((self.root / "menu" / "hints.json").read_text(encoding="utf-8"))["commands"])
      before = self.commands()

      def add_command(help_data):
         help_data["commands"].append({"name": "added-later", "purpose": "Added by another session", "kind": "read", "built": True, "inputs": {}})

      self.edit_json(self.help_json, add_command)
      self.assertIn("added-later", self.commands())

      skill_text = self.skill_md.read_text(encoding="utf-8")
      self.skill_md.write_text(skill_text.replace("| `list-items` | read | verified live |", "| `list-items` | read | blocked (site changed) |"), encoding="utf-8")
      self.assertEqual(before["list-items"]["s"], "verified")
      self.assertEqual(self.commands()["list-items"]["s"], "blocked")

      self.edit_json(self.root / "menu" / "hints.json", lambda hints: hints["commands"]["get-item"].update(summary="Fetch one item by id"))
      self.assertEqual(self.commands()["get-item"]["d"], "Fetch one item by id")

      def remove_command(help_data):
         help_data["commands"] = [entry for entry in help_data["commands"] if entry["name"] != "brand-new"]

      self.assertIn("brand-new", before)
      self.edit_json(self.help_json, remove_command)
      self.assertNotIn("brand-new", self.commands())


class DeterminismTests(SiteCopyTestCase):
   def test_forced_rebuilds_differ_only_in_the_sync_field(self):
      first_path = Path(self.build(force=True)["files"][0])
      first_page = first_path.read_text(encoding="utf-8")
      first_data = page_data(first_path)
      second_path = Path(self.build(force=True)["files"][0])
      second_data = page_data(second_path)
      normalized_second = second_path.read_text(encoding="utf-8").replace(json.dumps(second_data[build_menu.SYNC_FIELD]), json.dumps(first_data[build_menu.SYNC_FIELD]))

      self.assertEqual(without_sync_field(first_data), without_sync_field(second_data))
      self.assertEqual(normalized_second, first_page)


class ContractTests(unittest.TestCase):
   def test_fixture_data_meets_the_contract(self):
      data, _, _ = collect_fixture()

      self.assertEqual(data["v"], build_menu.CONTRACT)
      self.assertEqual(build_menu.validate_data(data), [])

   def test_contract_breaks_are_reported(self):
      data, _, _ = collect_fixture()
      data["v"] = 1
      data["commands"][0]["s"] = "mystery"
      data["commands"][1]["g"] = "nowhere"
      data["commands"][2].pop("f", None)
      data["commands"][2].pop("ins", None)
      data["global"] = [{"k": "yes", "l": "Yes", "t": "toggle"}]
      joined = "\n".join(build_menu.validate_data(data))

      self.assertIn("menu data is version 1", joined)
      self.assertIn("status mystery", joined)
      self.assertIn("group nowhere", joined)
      self.assertIn(f"{data['commands'][2]['n']}: a", joined)
      self.assertIn("offers --yes", joined)

   def test_the_template_declares_the_contract(self):
      self.assertIn(build_menu.CONTRACT_MARKER, build_menu.TEMPLATE_PATH.read_text(encoding="utf-8"))


class CompactOutputTests(SiteCopyTestCase):
   def test_build_prints_one_json_line_with_only_what_the_next_step_needs(self):
      printed = io.StringIO()

      with contextlib.redirect_stdout(printed):
         exit_code = build_menu.main(["build", "--site", str(self.root), "--help-json", str(self.help_json), "--skill-md", str(self.skill_md), "--file"])

      lines = printed.getvalue().splitlines()
      line = json.loads(lines[0])

      self.assertEqual(exit_code, 0)
      self.assertEqual(len(lines), 1)
      self.assertLessEqual(set(line), {"open", "counts", "warnings"})
      self.assertTrue(line["open"].startswith("file://") and line["open"].endswith("/menu.page.html"))
      self.assertTrue(line["counts"].startswith("4 ready"))

   def test_installed_section_stays_under_ten_lines(self):
      section_lines = build_menu.SECTION_PATH.read_text(encoding="utf-8").strip().splitlines()

      self.assertLess(len(section_lines), 10)


class ServerTests(SiteCopyTestCase):
   def fetch(self, port, path):
      connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
      connection.request("GET", path)
      body = connection.getresponse().read().decode("utf-8")
      connection.close()
      return body

   def test_server_serves_the_page_as_it_is_now_and_answers_its_token(self):
      page_path = Path(self.build()["files"][0])
      listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      listener.bind(("127.0.0.1", 0))
      listener.listen(4)
      port = listener.getsockname()[1]
      server_thread = threading.Thread(target=build_menu.serve, args=(page_path, listener.detach(), "token-1", 1), daemon=True)
      server_thread.start()

      first_body = self.fetch(port, "/menusite?v=1")
      page_path.write_text("rebuilt page", encoding="utf-8")
      second_body = self.fetch(port, "/menusite?v=2")
      token = self.fetch(port, "/__menu")
      server_thread.join(timeout=10)

      self.assertIn('id="menu-data"', first_body)
      self.assertEqual(second_body, "rebuilt page")
      self.assertEqual(token, "token-1")
      self.assertFalse(server_thread.is_alive())


if __name__ == "__main__":
   unittest.main()
