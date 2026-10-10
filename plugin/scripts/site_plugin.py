#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Site plugins for webapp-re, and the private local marketplace that lists them.

    uv run --script site_plugin.py scaffold --site example [--from <old skill dir>]
    uv run --script site_plugin.py check --site example|all
    uv run --script site_plugin.py marketplace [--check]
    uv run --script site_plugin.py status

Each site's plugin lives in <root>/plugin/. The layout and the naming rule are in
references/plugin-layout.md. Sites resolve under $WEBAPP_RE_HOME (default ~/dev/webapp-re/apps)
and the marketplace sits in $WEBAPP_RE_MARKETPLACE (default the parent of that home). Stdlib only.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOME = "~/dev/webapp-re/apps"
MARKETPLACE_NAME = "webapp-re-local"
MARKETPLACE_DESCRIPTION = "Private local marketplace: the webapp-re pipeline and the site plugins it built. Lists private site workspaces, so never publish it."
DESCRIPTION_LIMIT = 1024
LEGACY_SKILLS_DIR = Path("~/.claude/skills").expanduser()
LEGACY_PATH_MARKER = ".claude/skills/"
PLUGIN_ROOT_VARIABLE = "${CLAUDE_PLUGIN_ROOT}"
STAGES = ("reverse", "scope", "plan", "engineer", "develop", "optimize", "integrate-menu")
SECTION_START = "<!-- webapp-re:menu -->"


def webapp_re_home():
   return Path(os.environ.get("WEBAPP_RE_HOME", DEFAULT_HOME)).expanduser().resolve()


def marketplace_root():
   configured = os.environ.get("WEBAPP_RE_MARKETPLACE")
   return Path(configured).expanduser().resolve() if configured else webapp_re_home().parent


def marketplace_file():
   return marketplace_root() / ".claude-plugin" / "marketplace.json"


def today_version():
   now = datetime.now()
   return f"{now.year}.{now.month}.{now.day}"


def read_json(path, fallback=None):
   if not path.is_file():
      return fallback

   return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, document):
   path.parent.mkdir(parents=True, exist_ok=True)
   path.write_text(json.dumps(document, indent=3, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_root(site):
   given_path = Path(site).expanduser()

   if (given_path / "site.json").is_file():
      return given_path.resolve()

   root = webapp_re_home() / site

   if not (root / "site.json").is_file():
      raise SystemExit(f"site_plugin: no site.json at {root}, run kb.py init first")

   return root


def site_roots(site):
   if site != "all":
      return [resolve_root(site)]

   return sorted(path.parent for path in webapp_re_home().glob("*/site.json"))


def site_slug(root):
   site = read_json(root / "site.json", {}) or {}
   return site.get("slug") or root.name


def site_host(root):
   site = read_json(root / "site.json", {}) or {}
   origins = site.get("origins") or []

   if not origins:
      return site_slug(root)

   return urlparse(origins[0]).hostname or site_slug(root)


def known_slugs():
   return sorted(site_slug(path.parent) for path in webapp_re_home().glob("*/site.json"))


def pipeline_author():
   manifest = read_json(PIPELINE_ROOT / ".claude-plugin" / "plugin.json", {}) or {}
   return manifest.get("author") or {"name": "webapp-re"}


def split_front_matter(text):
   match = re.match(r"\A\ufeff?---\n(.*?)\n---\n", text, re.DOTALL)

   if not match:
      return {}, text

   fields = {}

   for line in match.group(1).splitlines():
      key_value = re.match(r"^([A-Za-z][\w-]*):\s?(.*)$", line)

      if not key_value:
         continue

      value = key_value.group(2).strip()
      is_quoted = len(value) >= 2 and value[0] == value[-1] == "\""

      if is_quoted:
         value = value[1:-1].replace("\\\"", "\"")

      fields[key_value.group(1)] = value

   return fields, text[match.end():]


def quoted(value):
   return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""


def plugin_dir(root):
   return root / "plugin"


def main_skill_path(root, slug):
   return plugin_dir(root) / "skills" / slug / "SKILL.md"


def launcher_path(root, slug):
   return plugin_dir(root) / "scripts" / slug


def launcher_call(slug):
   return f"{PLUGIN_ROOT_VARIABLE}/scripts/{slug}"


def same_place(written_path, root):
   expanded = Path(written_path.replace("$HOME", str(Path.home()))).expanduser()
   return expanded.resolve() == root.resolve()


def program_uses_env_file(skill_text, root, slug):
   pattern = re.compile(r"uv run --project (\S+)/program " + re.escape(slug) + r" --env-file (\S+)/\.env\b")

   for match in pattern.finditer(skill_text):
      if same_place(match.group(1), root):
         return True

   return False


def replace_program_calls(skill_text, root, slug, uses_env_file):
   if uses_env_file:
      pattern = re.compile(r"uv run --project (\S+)/program " + re.escape(slug) + r" --env-file (\S+)/\.env(?=[\s`])")
   else:
      pattern = re.compile(r"uv run --project (\S+)/program " + re.escape(slug) + r"(?=[\s`])(?! --env-file)")

   def swap(match):
      env_matches = not uses_env_file or same_place(match.group(2), root)
      is_this_site = same_place(match.group(1), root) and env_matches
      return launcher_call(slug) if is_this_site else match.group(0)

   return pattern.sub(swap, skill_text)


def namespace_slash_commands(skill_text, slugs):
   stage_pattern = re.compile(r"(?<![\w./:-])/webapp-re (" + "|".join(STAGES) + r")\b")
   updated = stage_pattern.sub(lambda match: "/webapp-re:" + ("engineer" if match.group(1) == "develop" else match.group(1)), skill_text)
   updated = re.sub(r"(?<![\w./:-])/webapp-re(?![\w:/.-])", "/webapp-re:webapp-re", updated)

   for slug in slugs:
      bare_pattern = re.compile(r"(?<![\w./:-])/" + re.escape(slug) + r"(?![\w:/.-])")
      updated = bare_pattern.sub(f"/{slug}:{slug}", updated)

   return updated


def namespace_body(skill_text, slugs):
   front_matter = re.match(r"\A\ufeff?---\n.*?\n---\n", skill_text, re.DOTALL)

   if not front_matter:
      return namespace_slash_commands(skill_text, slugs)

   return front_matter.group(0) + namespace_slash_commands(skill_text[front_matter.end():], slugs)


def replace_legacy_paths(skill_text, slug):
   legacy_skill = re.compile(r"(?:~|\$HOME|/Users/[^/\s`]+)/\.claude/skills/" + re.escape(slug) + r"/")
   return legacy_skill.sub(f"{PLUGIN_ROOT_VARIABLE}/skills/{slug}/", skill_text)


def load_build_menu():
   module_spec = importlib.util.spec_from_file_location("build_menu", PIPELINE_ROOT / "menu" / "build_menu.py")
   module = importlib.util.module_from_spec(module_spec)
   module_spec.loader.exec_module(module)
   return module


def stub_skill(root, slug):
   host = site_host(root)
   plan = read_json(root / "plan" / "plan.json", {}) or {}
   rows = ["| `help` | read | local | Lists commands, inputs, outputs, readiness and session status |"]

   for command in plan.get("commands", []):
      kind = "write" if command.get("kind") == "write" else "read"
      purpose = str(command.get("purpose", "")).replace("|", "/").replace("\n", " ")
      rows.append(f"| `{command.get('name')}` | {kind} | blocked: not built | {purpose} |")

   description = f"Automate {host} for the user's own signed-in account through a local program; run help for the command list. Use when the user runs /{slug}:{slug}, or asks about their {host} account."
   table = "\n".join(rows)

   return f"""---
name: {slug}
description: {quoted(description)}
argument-hint: "<command> [options]"
---

# {slug}

Request: $ARGUMENTS

The program lives at `{root}/program/` and is called with

```bash
{launcher_call(slug)} <command> [options]
```

It paces itself and classifies failures. Do not call the site any other way, and do not add
retries around it. Nothing is built yet: `/webapp-re:engineer {slug}` builds the program and
rewrites this file from the template in the webapp-re plugin.

## Commands

| Command | Kind | Status | Does |
|---|---|---|---|
{table}

## Provenance

Scaffolded by the web automation pipeline on {datetime.now().strftime("%Y-%m-%d")} from `{root}/site.json`.
"""


def help_skill(slug, host):
   description = f"List the {host} program's commands with their kind and readiness, and the session status. Shortcut for /{slug}:{slug} help."

   return f"""---
name: help
description: {quoted(description)}
argument-hint: "[command name]"
disable-model-invocation: true
---

# {slug} help

Arguments: $ARGUMENTS

Run `{launcher_call(slug)} help` and show its result as a short table. When the arguments name a
command, run `{launcher_call(slug)} <command> --help` instead and show its flags. Every other
command, and the rules for writes and errors, are in `{PLUGIN_ROOT_VARIABLE}/skills/{slug}/SKILL.md`;
read it before running anything else.
"""


def menu_skill(slug, host, section_body):
   description = f"Open the interactive {host} command menu in the built-in browser. Shortcut for /{slug}:{slug} menu."
   body = section_body.split("\n", 1)[1].strip() if section_body.startswith("## Menu") else section_body

   return f"""---
name: menu
description: {quoted(description)}
argument-hint: "[inline]"
disable-model-invocation: true
---

# {slug} menu

Arguments: $ARGUMENTS. With `inline`, take the `menu inline` path below.

{body}
"""


def launcher_script(slug, uses_env_file):
   env_flag = " --env-file \"$site_root/.env\"" if uses_env_file else ""

   return f"""#!/bin/sh
plugin_dir=$(cd "$(dirname "$0")/.." && pwd)
site_root=$(dirname "$plugin_dir")

if [ ! -d "$site_root/program" ]; then
   site_root="${{WEBAPP_RE_HOME:-$HOME/dev/webapp-re/apps}}/{slug}"
fi

export UV_PROJECT_ENVIRONMENT="$site_root/program/.venv"
exec uv run --project "$site_root/program" {slug}{env_flag} "$@"
"""


def first_sentence(description):
   head = re.split(r"(?<=[.;])\s", description, maxsplit=1)[0]
   return head.rstrip(";.") or description


def scaffold(root, source_dir=None):
   slug = site_slug(root)
   host = site_host(root)
   plugin = plugin_dir(root)
   skill_path = main_skill_path(root, slug)
   source_dir = Path(source_dir).expanduser() if source_dir else None
   written = []

   if source_dir:
      if not (source_dir / "SKILL.md").is_file():
         raise SystemExit(f"site_plugin: no SKILL.md in {source_dir}")

      shutil.copytree(source_dir, skill_path.parent, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".DS_Store"))
      written.append(str(skill_path.parent))

   if not skill_path.is_file():
      skill_path.parent.mkdir(parents=True, exist_ok=True)
      skill_path.write_text(stub_skill(root, slug), encoding="utf-8")
      written.append(str(skill_path))

   original = skill_path.read_text(encoding="utf-8")
   uses_env_file = env_file_choice(original, root, slug)
   slugs = sorted(set(known_slugs()) | {slug})
   normalized = replace_program_calls(original, root, slug, uses_env_file)
   written += write_if_changed(skill_path, namespace_body(replace_legacy_paths(normalized, slug), slugs))

   for reference in sorted(skill_path.parent.rglob("*.md")):
      if reference == skill_path:
         continue

      text = reference.read_text(encoding="utf-8")
      written += write_if_changed(reference, namespace_slash_commands(replace_legacy_paths(text, slug), slugs))

   launcher = launcher_path(root, slug)
   launcher.parent.mkdir(parents=True, exist_ok=True)
   launcher_text = launcher_script(slug, uses_env_file)

   if not launcher.is_file() or launcher.read_text(encoding="utf-8") != launcher_text:
      launcher.write_text(launcher_text, encoding="utf-8")
      written.append(str(launcher))

   launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

   help_path = plugin / "skills" / "help" / "SKILL.md"
   written += write_if_changed(help_path, help_skill(slug, host))

   has_menu = (root / "menu" / "hints.json").is_file()
   menu_path = plugin / "skills" / "menu" / "SKILL.md"

   if has_menu:
      build_menu = load_build_menu()
      install_result = build_menu.install(root, skill_path)

      if install_result["problems"]:
         raise SystemExit(f"site_plugin: menu install for {slug}: {install_result['problems']}")

      if install_result["changed"]:
         written.append(str(skill_path))

      written += write_if_changed(menu_path, menu_skill(slug, host, build_menu.section_text(slug, root)))
   elif menu_path.is_file():
      shutil.rmtree(menu_path.parent)
      written.append(f"removed {menu_path.parent}")

   front, _ = split_front_matter(skill_path.read_text(encoding="utf-8"))
   manifest_path = plugin / ".claude-plugin" / "plugin.json"
   existing = read_json(manifest_path, {}) or {}
   manifest = {
      "name": slug,
      "version": existing.get("version") or today_version(),
      "description": first_sentence(front.get("description", f"Automate {host}")),
      "author": existing.get("author") or pipeline_author(),
      "keywords": ["webapp-re", slug],
   }

   if manifest != existing:
      write_json(manifest_path, manifest)
      written.append(str(manifest_path))

   marketplace_written = sync_marketplace()

   return {"site": slug, "plugin": str(plugin), "written": written, "marketplace": marketplace_written}


def env_file_choice(skill_text, root, slug):
   has_program_call = re.search(r"uv run --project \S+/program " + re.escape(slug) + r"\b", skill_text) is not None
   launcher = launcher_path(root, slug)

   if launcher.is_file():
      return "--env-file" in launcher.read_text(encoding="utf-8")

   if has_program_call:
      return program_uses_env_file(skill_text, root, slug)

   return True


def write_if_changed(path, text):
   if path.is_file() and path.read_text(encoding="utf-8") == text:
      return []

   path.parent.mkdir(parents=True, exist_ok=True)
   path.write_text(text, encoding="utf-8")
   return [str(path)]


def relative_source(path):
   relative = path.resolve().relative_to(marketplace_root())
   return "./" + relative.as_posix() if str(relative) != "." else "./"


def marketplace_entry(plugin_path):
   manifest = read_json(plugin_path / ".claude-plugin" / "plugin.json", {}) or {}

   return {
      "name": manifest.get("name", plugin_path.parent.name),
      "source": relative_source(plugin_path),
      "description": manifest.get("description", ""),
      "version": manifest.get("version", ""),
   }


def expected_marketplace():
   mroot = marketplace_root()
   plugins = []
   skipped = []
   candidates = [PIPELINE_ROOT] + [path.parent.parent for path in sorted(webapp_re_home().glob("*/plugin/.claude-plugin/plugin.json"))]

   for candidate in candidates:
      if not candidate.resolve().is_relative_to(mroot):
         skipped.append(str(candidate))
         continue

      plugins.append(marketplace_entry(candidate))

   document = {
      "name": MARKETPLACE_NAME,
      "description": MARKETPLACE_DESCRIPTION,
      "owner": pipeline_author(),
      "plugins": plugins,
   }

   return document, skipped


def sync_marketplace():
   document, skipped = expected_marketplace()
   path = marketplace_file()
   changed = read_json(path) != document

   if changed:
      write_json(path, document)

   return {"path": str(path), "changed": changed, "plugins": [entry["name"] for entry in document["plugins"]], "outside_root": skipped}


def check_site(root):
   slug = site_slug(root)
   plugin = plugin_dir(root)
   problems = []
   warnings = []
   manifest = read_json(plugin / ".claude-plugin" / "plugin.json")

   if manifest is None:
      return {"site": slug, "problems": [f"no plugin at {plugin}; run site_plugin.py scaffold --site {slug}"]}

   if manifest.get("name") != slug:
      problems.append(f"plugin.json name {manifest.get('name')!r} is not the slug {slug!r}")

   if not manifest.get("version"):
      problems.append("plugin.json has no version")

   skill_path = main_skill_path(root, slug)

   if not skill_path.is_file():
      problems.append(f"no main skill at {skill_path}")

   for skill_file in sorted((plugin / "skills").glob("*/SKILL.md")):
      front, _ = split_front_matter(skill_file.read_text(encoding="utf-8"))
      directory = skill_file.parent.name
      description = front.get("description", "")

      if front.get("name") != directory:
         problems.append(f"skills/{directory}: frontmatter name {front.get('name')!r} differs from its directory")

      if not description:
         problems.append(f"skills/{directory}: no description")

      if len(description) > DESCRIPTION_LIMIT:
         problems.append(f"skills/{directory}: description is {len(description)} characters, over {DESCRIPTION_LIMIT}")

   if not (plugin / "skills" / "help" / "SKILL.md").is_file():
      problems.append("no help entry skill")

   has_menu = (root / "menu" / "hints.json").is_file()
   has_menu_entry = (plugin / "skills" / "menu" / "SKILL.md").is_file()

   if has_menu and not has_menu_entry:
      problems.append("menu/hints.json exists but there is no menu entry skill")

   if has_menu and skill_path.is_file() and SECTION_START not in skill_path.read_text(encoding="utf-8"):
      problems.append("menu/hints.json exists but the main skill has no menu section")

   launcher = launcher_path(root, slug)
   launcher_is_executable = launcher.is_file() and os.access(launcher, os.X_OK)

   if not launcher_is_executable:
      problems.append(f"launcher {launcher} is missing or not executable")

   for plugin_file in sorted(plugin.rglob("*")):
      if not plugin_file.is_file():
         continue

      text = plugin_file.read_text(encoding="utf-8", errors="replace")

      if LEGACY_PATH_MARKER in text:
         problems.append(f"{plugin_file.relative_to(root)} still names {LEGACY_PATH_MARKER}")

   marketplace = read_json(marketplace_file(), {}) or {}
   entries = {entry.get("name"): entry for entry in marketplace.get("plugins", [])}
   plugin_is_reachable = plugin.resolve().is_relative_to(marketplace_root())

   if not plugin_is_reachable:
      problems.append(f"plugin is outside the marketplace root {marketplace_root()}")
   elif slug not in entries:
      problems.append(f"no {slug} entry in {marketplace_file()}")
   elif entries[slug].get("source") != relative_source(plugin):
      problems.append(f"marketplace source {entries[slug].get('source')!r} is not {relative_source(plugin)!r}")

   legacy = LEGACY_SKILLS_DIR / slug

   if legacy.exists():
      warnings.append(f"legacy skill still at {legacy}")

   return {"site": slug, "problems": problems, "warnings": warnings}


def compact(fields):
   kept = {key: value for key, value in fields.items() if value not in (None, [], "")}
   return json.dumps(kept, ensure_ascii=False, separators=(",", ":"))


def main(argv=None):
   parser = argparse.ArgumentParser(description="Site plugins and the local marketplace for webapp-re.")
   actions = parser.add_subparsers(dest="action", required=True)
   scaffold_parser = actions.add_parser("scaffold", help="Write or refresh <root>/plugin/ and its marketplace entry")
   scaffold_parser.add_argument("--site", required=True, help="Site slug under WEBAPP_RE_HOME or a site root")
   scaffold_parser.add_argument("--from", dest="source_dir", help="Copy an existing skill directory in as the main skill first")
   check_parser = actions.add_parser("check", help="Check one site's plugin, or all")
   check_parser.add_argument("--site", required=True)
   marketplace_parser = actions.add_parser("marketplace", help="Write the marketplace manifest, or compare it with --check")
   marketplace_parser.add_argument("--check", action="store_true")
   actions.add_parser("status", help="One line per site: plugin, marketplace entry, legacy skill")
   arguments = parser.parse_args(argv)

   if arguments.action == "scaffold":
      print(compact(scaffold(resolve_root(arguments.site), arguments.source_dir)))
      return 0

   if arguments.action == "check":
      any_problems = False

      for root in site_roots(arguments.site):
         result = check_site(root)
         print(compact(result))
         any_problems = any_problems or bool(result["problems"])

      return 1 if any_problems else 0

   if arguments.action == "marketplace":
      expected, skipped = expected_marketplace()

      if arguments.check:
         current = read_json(marketplace_file())
         is_current = current == expected
         print(compact({"path": str(marketplace_file()), "current": is_current, "outside_root": skipped}))
         return 0 if is_current else 1

      print(compact(sync_marketplace()))
      return 0

   marketplace = read_json(marketplace_file(), {}) or {}
   listed = {entry.get("name") for entry in marketplace.get("plugins", [])}

   for root in site_roots("all"):
      slug = site_slug(root)
      has_plugin = (plugin_dir(root) / ".claude-plugin" / "plugin.json").is_file()
      print(compact({"site": slug, "plugin": has_plugin, "listed": slug in listed, "legacy_skill": (LEGACY_SKILLS_DIR / slug).exists()}))

   return 0


if __name__ == "__main__":
   sys.exit(main())
