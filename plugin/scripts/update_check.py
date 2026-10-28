#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tell the user when a newer webapp-re is tagged on GitHub.

    uv run --script update_check.py check
    uv run --script update_check.py status

check is the SessionStart hook. It asks the GitHub tags API at most once a day, prints one
message when a newer version is out and nothing otherwise, and always exits 0.
status prints the installed and latest versions, the cache age and whether the check is off.
Set WEBAPP_RE_NO_UPDATE_CHECK=1 to turn the check off. Stdlib only.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kb import plugin_manifest

OPT_OUT_VARIABLE = "WEBAPP_RE_NO_UPDATE_CHECK"
CACHE_SECONDS = 24 * 60 * 60
FETCH_TIMEOUT_SECONDS = 2
TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
REPOSITORY_PATTERN = re.compile(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$")


def is_disabled():
   return os.environ.get(OPT_OUT_VARIABLE, "") not in ("", "0")


def cache_path():
   plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")

   if plugin_data:
      return Path(plugin_data) / "update-check.json"

   return Path.home() / ".cache" / "webapp-re" / "update-check.json"


def parse_version(text):
   match = VERSION_PATTERN.match(text or "")
   return tuple(int(part) for part in match.groups()) if match else None


def format_version(version):
   return ".".join(str(part) for part in version)


def github_repository(manifest):
   match = REPOSITORY_PATTERN.search(manifest.get("repository", "") or "")
   return "{0}/{1}".format(*match.groups()) if match else ""


def fetch_tags(repository):
   import urllib.request

   request = urllib.request.Request(
      "https://api.github.com/repos/{0}/tags?per_page=30".format(repository),
      headers={"Accept": "application/vnd.github+json", "User-Agent": "webapp-re-update-check"},
   )

   with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
      document = json.load(response)

   if not isinstance(document, list):
      raise ValueError("tags response is not a list")

   return [entry.get("name", "") for entry in document if isinstance(entry, dict)]


def highest_tag(tag_names):
   versions = []

   for name in tag_names:
      match = TAG_PATTERN.match(name or "")

      if match:
         versions.append(tuple(int(part) for part in match.groups()))

   return max(versions) if versions else None


def read_cache(path):
   try:
      cache = json.loads(path.read_text(encoding="utf-8"))
   except (OSError, ValueError):
      return {}

   return cache if isinstance(cache, dict) else {}


def write_cache(path, cache):
   try:
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(json.dumps(cache, indent=3) + "\n", encoding="utf-8")
   except OSError:
      pass


def is_fresh(cache, repository, now):
   checked_at = cache.get("checked_at")
   is_same_repository = cache.get("repository") == repository
   has_timestamp = isinstance(checked_at, (int, float))

   return is_same_repository and has_timestamp and 0 <= now - checked_at < CACHE_SECONDS


def latest_version(repository, now):
   path = cache_path()
   cache = read_cache(path)

   if is_fresh(cache, repository, now):
      return parse_version(cache.get("latest"))

   try:
      latest = highest_tag(fetch_tags(repository))
      cache = {"repository": repository, "checked_at": now, "latest": format_version(latest) if latest else None}
   except (OSError, ValueError) as error:
      latest = None
      cache = {"repository": repository, "checked_at": now, "latest": None, "error": "{0}: {1}".format(type(error).__name__, error)}

   write_cache(path, cache)
   return latest


def update_message(now=None):
   if is_disabled():
      return ""

   manifest = plugin_manifest()
   installed = parse_version(manifest.get("version", ""))
   repository = github_repository(manifest)

   if installed is None or not repository:
      return ""

   latest = latest_version(repository, time.time() if now is None else now)

   if latest is None or latest <= installed:
      return ""

   return "webapp-re {0} is out (you have {1}). Update with `claude plugin update webapp-re`.".format(
      format_version(latest), format_version(installed))


def command_check():
   try:
      message = update_message()
   except Exception:
      return 0

   if message:
      print(json.dumps({"systemMessage": message}))

   return 0


def command_status():
   manifest = plugin_manifest()
   path = cache_path()
   cache = read_cache(path)
   checked_at = cache.get("checked_at")
   cache_age = round(time.time() - checked_at) if isinstance(checked_at, (int, float)) else None

   print(json.dumps({
      "installed": manifest.get("version", ""),
      "latest": cache.get("latest"),
      "repository": github_repository(manifest),
      "cache": str(path),
      "cache_age_seconds": cache_age,
      "last_error": cache.get("error"),
      "disabled": is_disabled(),
   }, indent=3))

   return 0


def main(argv=None):
   parser = argparse.ArgumentParser(description="Check GitHub for a newer webapp-re")
   parser.add_argument("action", choices=["check", "status"])
   arguments = parser.parse_args(argv)

   if arguments.action == "check":
      return command_check()

   return command_status()


if __name__ == "__main__":
   sys.exit(main())
