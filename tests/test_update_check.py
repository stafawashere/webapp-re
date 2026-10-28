#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Checks for plugin/scripts/update_check.py with the GitHub fetch stubbed out.

    uv run --script tests/test_update_check.py
"""

import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

module_spec = importlib.util.spec_from_file_location("update_check", REPO / "plugin" / "scripts" / "update_check.py")
update_check = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(update_check)

REPOSITORY_URL = "https://github.com/stafawashere/webapp-re"
NOW = 1_800_000_000
DAY = 24 * 60 * 60


class UpdateCheckTests(unittest.TestCase):
   def setUp(self):
      self.data_dir = tempfile.TemporaryDirectory()
      self.saved_environment = {name: os.environ.get(name) for name in ("CLAUDE_PLUGIN_DATA", "WEBAPP_RE_NO_UPDATE_CHECK")}
      os.environ["CLAUDE_PLUGIN_DATA"] = self.data_dir.name
      os.environ.pop("WEBAPP_RE_NO_UPDATE_CHECK", None)

      self.saved_fetch = update_check.fetch_tags
      self.saved_manifest = update_check.plugin_manifest
      self.fetch_calls = 0
      self.tags = []
      self.installed = "2.1.0"
      update_check.fetch_tags = self.fake_fetch
      update_check.plugin_manifest = lambda: {"version": self.installed, "repository": REPOSITORY_URL}

   def tearDown(self):
      update_check.fetch_tags = self.saved_fetch
      update_check.plugin_manifest = self.saved_manifest

      for name, value in self.saved_environment.items():
         if value is None:
            os.environ.pop(name, None)
         else:
            os.environ[name] = value

      self.data_dir.cleanup()

   def fake_fetch(self, repository):
      self.fetch_calls += 1
      self.assertEqual(repository, "stafawashere/webapp-re")

      if isinstance(self.tags, Exception):
         raise self.tags

      return self.tags

   @property
   def cache_file(self):
      return Path(self.data_dir.name) / "update-check.json"

   def write_cache(self, checked_at, latest):
      self.cache_file.write_text(json.dumps({"repository": "stafawashere/webapp-re", "checked_at": checked_at, "latest": latest}), encoding="utf-8")

   def run_check(self):
      output = io.StringIO()

      with redirect_stdout(output):
         exit_code = update_check.command_check()

      return exit_code, output.getvalue()

   def test_newer_tag_prints_the_alert(self):
      self.tags = ["v2.1.0", "v2.2.0", "v2.0.0"]

      exit_code, output = self.run_check()

      self.assertEqual(exit_code, 0)
      message = json.loads(output)["systemMessage"]
      self.assertEqual(message, "webapp-re 2.2.0 is out (you have 2.1.0). Update with `claude plugin update webapp-re`.")

   def test_equal_or_older_tag_prints_nothing(self):
      self.tags = ["v2.1.0", "v2.0.0"]
      self.assertEqual(update_check.update_message(now=NOW), "")

      self.cache_file.unlink()
      self.installed = "2.3.0"
      self.assertEqual(update_check.update_message(now=NOW), "")

   def test_two_digit_minor_beats_single_digit(self):
      self.tags = ["v2.9.0", "v2.10.0"]
      self.installed = "2.9.0"

      self.assertEqual(update_check.highest_tag(self.tags), (2, 10, 0))
      self.assertIn("webapp-re 2.10.0 is out", update_check.update_message(now=NOW))

   def test_non_semver_tags_are_ignored(self):
      self.tags = ["v9.9.9-beta", "latest", "v3.0", "release-4.0.0", "5.0.0", "v2.1.0"]

      self.assertEqual(update_check.update_message(now=NOW), "")

   def test_fresh_cache_skips_the_fetch(self):
      self.write_cache(NOW - 60, "2.2.0")
      self.tags = ["v9.0.0"]

      message = update_check.update_message(now=NOW)

      self.assertEqual(self.fetch_calls, 0)
      self.assertIn("webapp-re 2.2.0 is out", message)

   def test_stale_cache_refetches(self):
      self.write_cache(NOW - DAY - 60, "2.1.0")
      self.tags = ["v2.3.0"]

      message = update_check.update_message(now=NOW)

      self.assertEqual(self.fetch_calls, 1)
      self.assertIn("webapp-re 2.3.0 is out", message)
      self.assertEqual(json.loads(self.cache_file.read_text(encoding="utf-8"))["checked_at"], NOW)

   def test_fetch_failure_is_silent_and_recorded(self):
      for failure in (urllib.error.URLError("offline"), ValueError("bad json")):
         with self.subTest(failure=type(failure).__name__):
            self.cache_file.unlink(missing_ok=True)
            self.tags = failure
            started = time.time()

            exit_code, output = self.run_check()

            self.assertEqual(exit_code, 0)
            self.assertEqual(output, "")
            cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            self.assertGreaterEqual(cache["checked_at"], started)
            self.assertIn(type(failure).__name__, cache["error"])

      calls_before_retry = self.fetch_calls
      self.run_check()
      self.assertEqual(self.fetch_calls, calls_before_retry)

   def test_opt_out_skips_everything(self):
      os.environ["WEBAPP_RE_NO_UPDATE_CHECK"] = "1"
      self.tags = ["v9.0.0"]

      exit_code, output = self.run_check()

      self.assertEqual((exit_code, output, self.fetch_calls), (0, "", 0))
      self.assertFalse(self.cache_file.exists())


if __name__ == "__main__":
   unittest.main()
