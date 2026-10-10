#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build the interactive command menu of a webapp-re site skill from the site's current state.

    uv run --script build_menu.py build --site <slug or root> [--inline | --file] [--force]
    uv run --script build_menu.py check --site <slug, root or all>
    uv run --script build_menu.py install --site <slug, root or all>

Every build fingerprints the program's source tree, the plan, the knowledge base, the site skill,
the menu hints, their option sources and these shared files. When nothing changed it reuses the
last page, and the program's help runs again only after the program changed, so the menu always
shows what exists now. The page is served on 127.0.0.1 for the browser pane. Nothing is sent to
the site. On success build prints one line of JSON: what to open, the counts, and any warnings.
"""

import argparse
import hashlib
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

MENU_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = MENU_DIR / "menu.template.html"
PAGE_TEMPLATE_PATH = MENU_DIR / "standalone.template.html"
SECTION_PATH = MENU_DIR / "skill-section.md"

CONTRACT = 2
CONTRACT_MARKER = f"const CONTRACT = {CONTRACT};"
SYNC_FIELD = "generated"
DATA_KEYS = ("v", "site", SYNC_FIELD, "counts", "groups", "global", "lists", "opts", "commands")
STATUSES = {"local", "verified", "unverified", "blocked", "planned"}
RUNNABLE_STATUSES = {"local", "verified"}

PAGE_NAME = "menu.page.html"
INLINE_NAME = "menu.inline.html"
INLINE_PART_PATTERN = "menu.inline-*.html"
CACHE_NAME = "build.json"
SERVER_NAME = "server.json"
OLD_OUTPUT_PATTERNS = ("menu.widget.html", "menu.part-*.html")
SERVER_IDLE_SECONDS = 900
INLINE_LIST_CAP = 25
INLINE_DROPPED_KEYS = ("ret", "ep", "note", "steps", "st")
INLINE_CLIPPED_KEYS = {"safety": 120, "cost": 60, "d": 120}
PROGRAM_SKIPPED_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}
PROGRAM_SKIPPED_FILES = {".DS_Store"}

DATA_PLACEHOLDER = "__MENU_DATA__"
PART_LIMIT = 24000
DESCRIPTION_LIMIT = 1024
SECTION_START = "<!-- webapp-re:menu -->"
SECTION_END = "<!-- /webapp-re:menu -->"

CONTROLS = {"select", "toggle", "text", "number", "date", "datalist"}
FIELD_HINT_KEYS = {"control", "label", "hint", "placeholder", "options", "options_from", "any_label", "list", "pick", "when", "required", "warn"}
COMMAND_HINT_KEYS = {"summary", "note", "cost", "spends", "fields"}
NEVER_OFFERED = {"yes"}
LIMIT_OPTIONS = [["", "All"], ["5", "5"], ["10", "10"], ["25", "25"], ["50", "50"], ["100", "100"]]
OTHER_GROUP = {"key": "other", "title": "Other", "icon": "ti-dots"}
PAGING_FIELDS = {"total_count", "count", "page", "page_size", "total_pages", "has_next_page", "next_cursor", "cursor"}
NOT_READY = {"planned", "unverified", "blocked"}


class MenuError(Exception):
   pass


def webapp_re_home():
   return Path(os.environ.get("WEBAPP_RE_HOME", "~/dev/webapp-re/apps")).expanduser()


def home_relative(path):
   resolved = Path(path).resolve()
   home = Path.home()

   if resolved.is_relative_to(home):
      return "~/" + str(resolved.relative_to(home))

   return str(resolved)


def default_skill_path(root, slug):
   return root / "plugin" / "skills" / slug / "SKILL.md"


def read_json(path, fallback=None):
   if not path or not Path(path).is_file():
      return fallback

   with open(path, encoding="utf-8") as handle:
      return json.load(handle)


def resolve_root(site_argument):
   given_path = Path(site_argument).expanduser()

   if (given_path / "site.json").is_file():
      return given_path.resolve()

   slug_root = webapp_re_home() / site_argument

   if (slug_root / "site.json").is_file():
      return slug_root

   raise MenuError(f"No site.json for {site_argument} under {webapp_re_home()}.")


def clip(text, limit):
   flattened = " ".join(str(text or "").split())

   if len(flattened) <= limit:
      return flattened

   return flattened[: limit - 3].rstrip() + "..."


def humanize(name):
   return name.replace("_", " ").replace("-", " ").capitalize()


def flag(name):
   return "--" + name.replace("_", "-")


def type_names(property_schema):
   declared = property_schema.get("type")

   if isinstance(declared, list):
      return set(declared)

   return {declared} if declared else set()


def run_program_help(root, program_command, help_json_path):
   if help_json_path:
      return read_json(Path(help_json_path).expanduser()), None

   program_dir = root / "program"

   if not (program_dir / "pyproject.toml").is_file():
      return None, "no program yet, so the menu shows the plan only"

   program_env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(program_dir / ".venv"))

   try:
      completed = subprocess.run(
         ["uv", "run", "--quiet", "--project", str(program_dir), program_command, "help"],
         capture_output=True,
         text=True,
         timeout=180,
         env=program_env,
      )
   except (OSError, subprocess.TimeoutExpired) as error:
      return None, f"program help did not run: {error}"

   if completed.returncode != 0:
      last_line = (completed.stderr.strip().splitlines() or ["no stderr"])[-1]
      return None, f"program help exited {completed.returncode}: {clip(last_line, 200)}"

   try:
      return json.loads(completed.stdout), None
   except json.JSONDecodeError:
      return None, "program help did not print JSON"


def load_schemas(root):
   for schema_path in sorted((root / "program" / "src").glob("*/schemas.json")):
      loaded = read_json(schema_path, {})
      listed_commands = loaded.get("commands") if isinstance(loaded, dict) else None
      is_command_list = isinstance(listed_commands, list)

      if is_command_list:
         return {entry["name"]: entry for entry in listed_commands if isinstance(entry, dict) and entry.get("name")}

      if isinstance(loaded, dict):
         return loaded

   return {}


def split_row(line):
   stripped = line.strip()

   if not stripped.startswith("|"):
      return []

   return [cell.strip() for cell in stripped.strip("|").split("|")]


def parse_status_table(skill_text):
   statuses = {}
   lines = skill_text.splitlines()

   for index, line in enumerate(lines):
      header = [cell.lower() for cell in split_row(line)]
      is_command_table = bool(header) and header[0] == "command" and "status" in header

      if not is_command_table:
         continue

      status_column = header.index("status")

      for row in lines[index + 2:]:
         cells = split_row(row)

         if not cells:
            break

         name = cells[0].strip("`")
         has_status_cell = len(cells) > status_column

         if name and has_status_cell:
            statuses[name] = cells[status_column]

   return statuses


def classify_status(is_built, status_text, readiness):
   if not is_built:
      return "planned"

   text = (status_text or readiness or "").strip().lower()

   if text.startswith("blocked"):
      return "blocked"

   if text.startswith("local"):
      return "local"

   if text.startswith("verified live"):
      return "verified"

   return "unverified"


def status_detail(status_text):
   plain = (status_text or "").strip()
   is_plain_label = plain.lower() in {"", "verified live", "local", "planned"}

   if is_plain_label:
      return ""

   return clip(plain.replace("`", ""), 240)


def endpoint_states(root):
   states = {}

   for finding_path in sorted((root / "knowledge" / "endpoints").glob("*.md")):
      lines = finding_path.read_text(encoding="utf-8").splitlines()
      has_frontmatter = bool(lines) and lines[0].strip() == "---"

      if not has_frontmatter:
         continue

      finding = {}

      for line in lines[1:]:
         if line.strip() == "---":
            break

         key, separator, value = line.partition(":")

         if separator:
            finding[key.strip()] = value.strip()

      finding_id = finding.get("id") or finding_path.stem
      states[finding_id] = finding.get("status", "")

   return states


def nested_properties(property_schema):
   if not isinstance(property_schema, dict):
      return {}

   item_schema = property_schema.get("items") if isinstance(property_schema.get("items"), dict) else {}

   return property_schema.get("properties") or item_schema.get("properties") or {}


def output_fields(output_schema):
   if not isinstance(output_schema, dict):
      return []

   properties = output_schema.get("properties") or {}
   containers = [key for key, value in properties.items() if nested_properties(value)]
   siblings = [key for key in properties if key not in containers]
   has_single_payload = len(containers) == 1 and all(key in PAGING_FIELDS for key in siblings)

   if has_single_payload:
      return (list(nested_properties(properties[containers[0]])) + siblings)[:10]

   return list(properties)[:10]


def derive_field(name, property_schema, is_required):
   types = type_names(property_schema)
   description = property_schema.get("description") or ""
   enum_values = [value for value in property_schema.get("enum", []) if value is not None]
   default_value = property_schema.get("default")
   field = {"k": name, "l": humanize(name)}

   if is_required:
      field["r"] = True

   is_number = "integer" in types or "number" in types
   is_limit = name == "limit" and is_number
   looks_like_date = "iso date" in description.lower() or name.endswith(("_date", "_after", "_before"))

   if "boolean" in types:
      field["t"] = "toggle"
   elif enum_values:
      empty_label = "Choose" if is_required else (f"{default_value} (default)" if default_value is not None else "Default")
      choices = [[str(value), str(value)] for value in enum_values if value != default_value or is_required]
      field["t"] = "select"
      field["o"] = [["", empty_label]] + choices
   elif is_limit:
      field["t"] = "select"
      field["o"] = "limit"
   elif is_number:
      field["t"] = "number"
   elif looks_like_date:
      field["t"] = "date"
   else:
      field["t"] = "text"

   if description:
      field["h"] = clip(description, 160)

   return field


def dotted_values(record, dotted_path):
   current = [record]

   for key in dotted_path.split("."):
      next_values = []

      for value in current:
         if isinstance(value, dict) and key in value:
            next_values.append(value[key])

      current = []

      for value in next_values:
         if isinstance(value, list):
            current.extend(value)
         else:
            current.append(value)

   return [value for value in current if isinstance(value, (str, int, float)) and value != ""]


def first_rows(root, source):
   candidates = source if isinstance(source, list) else [source]

   for candidate in candidates:
      rows = read_json(root / candidate, None) if candidate else None

      if isinstance(rows, list):
         return rows

   return None


def load_option_sources(root, hints, warnings):
   sources = {}

   for name, spec in (hints.get("option_sources") or {}).items():
      rows = first_rows(root, spec.get("source"))

      if rows is None:
         warnings.append(f"option source {name}: {spec.get('source')} is missing or not a list, so its select is empty")
         sources[name] = []
         continue

      labels = spec.get("labels") or {}
      found = sorted({str(value) for row in rows for value in dotted_values(row, spec.get("path", ""))})
      sources[name] = [[value, labels.get(value, value)] for value in found]

   return sources


def load_datalists(root, hints, warnings):
   lists = {}

   for name, spec in (hints.get("datalists") or {}).items():
      rows = first_rows(root, spec.get("source"))

      if rows is None:
         warnings.append(f"datalist {name}: {spec.get('source')} is missing or not a list, so it offers nothing")
         lists[name] = []
         continue

      value_key = spec.get("value", "id")
      label_key = spec.get("label", value_key)
      required_key = spec.get("require")
      sort_key = spec.get("sort")
      limit = spec.get("limit") or len(rows)
      records = [row for row in rows if isinstance(row, dict) and row.get(value_key)]
      kept = [row for row in records if not required_key or row.get(required_key) is not None]

      if sort_key:
         kept.sort(key=lambda row: (row.get(sort_key) is None, row.get(sort_key) if isinstance(row.get(sort_key), (int, float)) else str(row.get(sort_key))))

      chosen = kept[:limit]
      chosen_values = {row[value_key] for row in chosen}
      wanted_extras = spec.get("include") or []
      by_value = {row[value_key]: row for row in records}

      for extra_value in wanted_extras:
         is_new = extra_value in by_value and extra_value not in chosen_values

         if is_new:
            chosen.append(by_value[extra_value])
            chosen_values.add(extra_value)

      lists[name] = [[str(row[value_key]), clip(row.get(label_key) or row[value_key], 80)] for row in chosen]

   return lists


def apply_field_hint(field, hint, option_sources, lists, where, warnings, problems):
   unknown_keys = set(hint) - FIELD_HINT_KEYS

   if unknown_keys:
      warnings.append(f"{where}: unknown hint keys {sorted(unknown_keys)} ignored")

   control = hint.get("control")

   if control is not None and control not in CONTROLS:
      problems.append(f"{where}: control {control} is not one of {sorted(CONTROLS)}")
   elif control:
      field["t"] = control

   if "label" in hint:
      field["l"] = hint["label"]

   if "hint" in hint:
      field["h"] = hint["hint"]

   if "placeholder" in hint:
      field["ph"] = hint["placeholder"]

   if "pick" in hint:
      field["pick"] = hint["pick"]

   if "warn" in hint:
      field["warn"] = bool(hint["warn"])

   if "required" in hint:
      field["r"] = bool(hint["required"])

   if "when" in hint:
      is_pair = isinstance(hint["when"], list) and len(hint["when"]) == 2

      if is_pair:
         field["when"] = hint["when"]
      else:
         problems.append(f"{where}: when must be [field, value]")

   if "options" in hint:
      field["o"] = [[str(value), str(label)] for value, label in hint["options"]]

   if "options_from" in hint:
      source_name = hint["options_from"]
      source_options = option_sources.get(source_name)

      if source_options is None:
         problems.append(f"{where}: options_from {source_name} is not declared in option_sources")
         source_options = []

      leading = [] if field.get("r") else [["", hint.get("any_label", "Any")]]
      field["o"] = leading + source_options

      if not control:
         field["t"] = "select"

   if "list" in hint:
      field["list"] = hint["list"]

      if not control:
         field["t"] = "datalist"

      if hint["list"] not in lists:
         warnings.append(f"{where}: datalist {hint['list']} is not declared, so it offers nothing")

   is_select_without_options = field.get("t") == "select" and not field.get("o")

   if is_select_without_options:
      problems.append(f"{where}: a select needs options or options_from")

   if field.get("t") != "select":
      field.pop("o", None)

   return field


def input_schema_for(schema_entry, help_entry, plan_entry):
   candidates = [
      schema_entry.get("input_schema"),
      help_entry.get("input_schema"),
      {"properties": help_entry.get("inputs")} if isinstance(help_entry.get("inputs"), dict) else None,
      plan_entry.get("input_schema"),
   ]
   candidates = [candidate for candidate in candidates if isinstance(candidate, dict)]
   properties = next((candidate["properties"] for candidate in candidates if candidate.get("properties")), {})
   required = next((candidate["required"] for candidate in candidates if candidate.get("required")), [])

   return {"properties": properties, "required": [name for name in required if name in properties]}


def output_schema_for(schema_entry, help_entry, plan_entry):
   for candidate in (schema_entry.get("output_schema"), help_entry.get("output_schema"), plan_entry.get("output_schema")):
      if isinstance(candidate, dict):
         return candidate

   return {}


def cost_text(plan_entry):
   requests = plan_entry.get("requests")

   if not isinstance(requests, int):
      return ""

   if requests == 0:
      base = "0 requests, runs offline"
   else:
      base = f"{requests} request" + ("" if requests == 1 else "s")

   pagination = (plan_entry.get("pagination") or "").strip()
   says_no_paging = pagination.lower().startswith("none")

   if says_no_paging:
      detail = pagination[len("none"):].strip(" ;:,()")
   else:
      detail = pagination

   return base + (" · " + clip(detail, 120) if detail else "")


def command_endpoints(plan_entry, kb_states):
   endpoints = []

   for dependency in plan_entry.get("depends_on") or []:
      endpoint_id = dependency.get("endpoint") if isinstance(dependency, dict) else dependency

      if not endpoint_id:
         continue

      known_state = kb_states.get(endpoint_id) or (dependency.get("state") if isinstance(dependency, dict) else "")
      endpoints.append([endpoint_id, known_state == "verified"])

   return endpoints


def collect(root, help_json_path=None, skill_md_path=None, program_help=None):
   warnings = []
   problems = []
   site = read_json(root / "site.json", {}) or {}
   slug = site.get("slug") or root.name
   hints_path = root / "menu" / "hints.json"

   try:
      hints = read_json(hints_path, {}) or {}
   except json.JSONDecodeError as error:
      problems.append(f"menu/hints.json does not parse: {error}")
      hints = {}

   if not hints_path.is_file():
      warnings.append("no menu/hints.json, so every command is shown under Other with inputs taken from its schema")

   plan = read_json(root / "plan" / "plan.json", {}) or {}
   plan_by_name = {entry.get("name"): entry for entry in plan.get("commands", []) if entry.get("name")}
   schemas = load_schemas(root)

   if program_help is None:
      program_help = run_program_help(root, hints.get("program_command", slug), help_json_path)

   help_data, help_problem = program_help

   if help_problem:
      warnings.append(help_problem)

   help_entries = (help_data or {}).get("commands", [])
   help_by_name = {entry.get("name"): entry for entry in help_entries if entry.get("name")}

   skill_path = Path(skill_md_path).expanduser() if skill_md_path else default_skill_path(root, slug)
   skill_text = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
   status_texts = parse_status_table(skill_text)

   if not skill_text:
      warnings.append(f"no skill at {skill_path}, so statuses come from the program's readiness")

   kb_states = endpoint_states(root)
   option_sources = load_option_sources(root, hints, warnings)
   built_names = [name for name, entry in help_by_name.items() if entry.get("built", True) is not False]
   option_sources["@commands"] = [[name, name] for name in built_names]
   lists = load_datalists(root, hints, warnings)

   ordered_names = list(help_by_name) + [name for name in plan_by_name if name not in help_by_name]
   command_hints = hints.get("commands") or {}
   group_specs = hints.get("groups") or []
   group_of = {}
   position_of = {}

   for group in group_specs:
      for position, name in enumerate(group.get("commands") or []):
         group_of.setdefault(name, group.get("key"))
         position_of.setdefault(name, position)

   for stale_name in sorted(set(command_hints) - set(ordered_names)):
      warnings.append(f"hint for {stale_name}, which no longer exists; remove it from menu/hints.json")

   for group in group_specs:
      for stale_name in sorted(set(group.get("commands") or []) - set(ordered_names)):
         warnings.append(f"group {group.get('key')} lists {stale_name}, which no longer exists")

   ungrouped = [name for name in ordered_names if name not in group_of]

   if ungrouped and group_specs:
      warnings.append(f"no group for {', '.join(ungrouped)}; shown under Other")

   global_fields = []

   for global_hint in hints.get("global_fields") or []:
      field_name = global_hint.get("name")

      if not field_name:
         problems.append("a global field has no name")
         continue

      field = {"k": field_name, "l": humanize(field_name), "t": "text"}
      field_spec = {key: value for key, value in global_hint.items() if key != "name"}
      global_fields.append(apply_field_hint(field, field_spec, option_sources, lists, f"global field {field_name}", warnings, problems))

   commands = []

   for help_index, name in enumerate(ordered_names):
      help_entry = help_by_name.get(name, {})
      plan_entry = plan_by_name.get(name, {})
      schema_entry = schemas.get(name, {}) if isinstance(schemas.get(name), dict) else {}
      hint = command_hints.get(name, {})
      unknown_hint_keys = set(hint) - COMMAND_HINT_KEYS

      if unknown_hint_keys:
         warnings.append(f"hint for {name}: unknown keys {sorted(unknown_hint_keys)} ignored")

      is_built = bool(help_entry) and help_entry.get("built", True) is not False
      status_text = status_texts.get(name, "")
      status = classify_status(is_built, status_text, help_entry.get("readiness"))
      kind = help_entry.get("kind") or schema_entry.get("kind") or plan_entry.get("kind") or "read"
      input_schema = input_schema_for(schema_entry, help_entry, plan_entry)
      properties = input_schema.get("properties") or {}
      required_names = set(input_schema.get("required") or [])
      field_hints = hint.get("fields") or {}

      for stale_field in sorted(set(field_hints) - set(properties)):
         warnings.append(f"hint for {name} field {stale_field}, which the command no longer takes")

      confirmation = plan_entry.get("confirmation") or ""
      spends = bool(hint.get("spends")) or bool(re.search(r"\bspend", confirmation, re.IGNORECASE))
      purpose = hint.get("summary") or help_entry.get("purpose") or schema_entry.get("purpose") or plan_entry.get("purpose") or ""

      entry = {
         "n": name,
         "g": group_of.get(name, OTHER_GROUP["key"]),
         "k": kind,
         "s": status,
         "d": clip(purpose, 220),
      }

      detail = status_detail(status_text)

      if detail:
         entry["st"] = detail

      returned = output_fields(output_schema_for(schema_entry, help_entry, plan_entry))

      if returned:
         entry["ret"] = returned

      cost = hint.get("cost") or cost_text(plan_entry)

      if cost:
         entry["cost"] = cost

      note = hint.get("note") or plan_entry.get("notes") or ""

      if note:
         entry["note"] = clip(note, 300)

      endpoints = command_endpoints(plan_entry, kb_states)

      if endpoints:
         entry["ep"] = endpoints

      if spends:
         entry["spends"] = True

      is_runnable = status in {"local", "verified"}

      if is_runnable:
         fields = []

         for field_name, property_schema in properties.items():
            if field_name in NEVER_OFFERED:
               continue

            field = derive_field(field_name, property_schema if isinstance(property_schema, dict) else {}, field_name in required_names)

            if field_name in field_hints:
               field = apply_field_hint(field, field_hints[field_name], option_sources, lists, f"{name} field {field_name}", warnings, problems)

            fields.append(field)

         entry["f"] = fields
      else:
         entry["ins"] = [flag(field_name) + (" required" if field_name in required_names else "") for field_name in properties if field_name not in NEVER_OFFERED]

      if status in NOT_READY:
         steps = [clip(step.get("step") if isinstance(step, dict) else step, 200) for step in plan_entry.get("open_steps") or []]
         steps = [step for step in steps if step]

         if steps:
            entry["steps"] = steps[:6]

      is_write = kind == "write"

      if is_write and confirmation:
         entry["safety"] = clip(confirmation, 300)

      sort_position = position_of.get(name, 10000 + help_index)
      commands.append((sort_position, entry))

   commands = [entry for _, entry in sorted(commands, key=lambda pair: pair[0])]
   groups = [{"key": group.get("key"), "title": group.get("title") or humanize(group.get("key", "")), "icon": group.get("icon") or "ti-folder"} for group in group_specs]

   if any(entry["g"] == OTHER_GROUP["key"] for entry in commands):
      groups.append(dict(OTHER_GROUP))

   counts = {
      "ready": sum(1 for entry in commands if entry["s"] in {"local", "verified"}),
      "verified": sum(1 for entry in commands if entry["s"] == "verified"),
      "unverified": sum(1 for entry in commands if entry["s"] == "unverified"),
      "blocked": sum(1 for entry in commands if entry["s"] == "blocked"),
      "planned": sum(1 for entry in commands if entry["s"] == "planned"),
      "endpoints": len(kb_states),
      "endpoints_verified": sum(1 for state in kb_states.values() if state == "verified"),
   }

   origins = site.get("origins") or []
   default_subtitle = ", ".join(origin.split("//")[-1].rstrip("/") for origin in origins)

   data = {
      "v": CONTRACT,
      "site": {
         "slug": slug,
         "subtitle": hints.get("subtitle") or default_subtitle,
         "footnote": hints.get("footnote") or "",
         "icon": hints.get("icon") or "ti-world",
         "accent": hints.get("accent") or "blue",
      },
      SYNC_FIELD: datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z").strip(),
      "counts": counts,
      "groups": groups,
      "global": global_fields,
      "lists": lists,
      "opts": {"limit": LIMIT_OPTIONS},
      "commands": commands,
   }

   if not commands:
      problems.append("no commands found in the program help or the plan")

   return data, warnings, problems


def dump_compact(value):
   return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def data_json(data):
   """Encode the menu data with one command, and at most 25 list options, per line.

   Short lines let the built widget be split into parts at line breaks, where an added newline
   is harmless JSON whitespace.
   """
   top_level = []

   for key, value in data.items():
      if key == "commands":
         body = "[\n" + ",\n".join(dump_compact(command) for command in value) + "\n]"
      elif key == "lists":
         list_bodies = []

         for name, options in value.items():
            chunks = [",".join(dump_compact(option) for option in options[start:start + 25]) for start in range(0, len(options), 25)]
            list_bodies.append(dump_compact(name) + ":[\n" + ",\n".join(chunks) + "\n]")

         body = "{\n" + ",\n".join(list_bodies) + "\n}"
      else:
         body = dump_compact(value)

      top_level.append(dump_compact(key) + ":" + body)

   encoded = "{\n" + ",\n".join(top_level) + "\n}"
   return encoded.replace("</", "<\\/").replace("<!--", "<\\u0021--")


def render_widget(data):
   template = TEMPLATE_PATH.read_text(encoding="utf-8")

   if template.count(DATA_PLACEHOLDER) != 1:
      raise MenuError(f"{TEMPLATE_PATH} must contain {DATA_PLACEHOLDER} exactly once.")

   compact_lines = [line.strip() for line in template.splitlines() if line.strip()]
   return "\n".join(compact_lines).replace(DATA_PLACEHOLDER, data_json(data)) + "\n"


def split_parts(widget, limit=PART_LIMIT):
   parts = []
   current = ""

   for line in widget.splitlines(keepends=True):
      while len(line) > limit:
         if current:
            parts.append(current)
            current = ""

         parts.append(line[:limit])
         line = line[limit:]

      would_overflow = len(current) + len(line) > limit

      if would_overflow:
         parts.append(current)
         current = ""

      current += line

   if current:
      parts.append(current)

   return parts


def render_page(widget, slug):
   page = PAGE_TEMPLATE_PATH.read_text(encoding="utf-8")
   return page.replace("__TITLE__", f"{slug} menu").replace("__WIDGET__", widget)


def inline_data(data):
   lite = json.loads(json.dumps(data))
   lite["lite"] = True
   lite["lists"] = {name: options[:INLINE_LIST_CAP] for name, options in lite["lists"].items()}

   for command in lite["commands"]:
      for key in INLINE_DROPPED_KEYS:
         command.pop(key, None)

      for key, limit in INLINE_CLIPPED_KEYS.items():
         if key in command:
            command[key] = clip(command[key], limit)

   return lite


def minify_widget(widget):
   style_start = widget.find("<style>")
   style_end = widget.find("</style>")
   has_style = style_start != -1 and style_end > style_start

   if not has_style:
      return widget

   style = widget[style_start:style_end].replace("\n", "")
   return widget[:style_start] + style + widget[style_end:]


def write_if_changed(path, text):
   if path.is_file() and path.read_text(encoding="utf-8") == text:
      return False

   staging_path = path.with_name(path.name + ".tmp")
   staging_path.write_text(text, encoding="utf-8")
   os.replace(staging_path, path)
   return True


def remove_old_outputs(out_dir, patterns):
   for pattern in patterns:
      for old_path in out_dir.glob(pattern):
         old_path.unlink()


def write_mode_outputs(out_dir, slug, data, mode):
   out_dir.mkdir(parents=True, exist_ok=True)
   remove_old_outputs(out_dir, OLD_OUTPUT_PATTERNS)

   if mode == "page":
      page_path = out_dir / PAGE_NAME
      write_if_changed(page_path, render_page(render_widget(data), slug))
      return [str(page_path)]

   widget = minify_widget(render_widget(inline_data(data)))
   parts = split_parts(widget)
   remove_old_outputs(out_dir, (INLINE_NAME, INLINE_PART_PATTERN))

   if len(parts) == 1:
      inline_path = out_dir / INLINE_NAME
      write_if_changed(inline_path, widget)
      return [str(inline_path)]

   part_paths = []

   for number, part in enumerate(parts, start=1):
      part_path = out_dir / f"menu.inline-{number}.html"
      write_if_changed(part_path, part)
      part_paths.append(str(part_path))

   return part_paths


def file_stamp(path):
   try:
      stats = Path(path).stat()
   except OSError:
      return [str(path), None, None]

   return [str(path), stats.st_size, stats.st_mtime_ns]


def program_stamps(program_dir):
   stamps = []

   for directory, child_dirs, file_names in os.walk(program_dir):
      child_dirs[:] = sorted(name for name in child_dirs if name not in PROGRAM_SKIPPED_DIRS)

      for file_name in sorted(file_names):
         if file_name not in PROGRAM_SKIPPED_FILES:
            stamps.append(file_stamp(Path(directory) / file_name))

   return stamps


def digest(value):
   encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
   return hashlib.sha256(encoded).hexdigest()[:16]


def option_source_paths(root, hints):
   paths = []

   for section in ("option_sources", "datalists"):
      for spec in (hints.get(section) or {}).values():
         source = spec.get("source") if isinstance(spec, dict) else None
         candidates = source if isinstance(source, list) else [source]
         paths.extend(root / candidate for candidate in candidates if candidate)

   return paths


def program_fingerprint(root, program_command, help_json_path):
   if help_json_path:
      return digest(["help-json", file_stamp(Path(help_json_path).expanduser())])

   return digest([program_command, program_stamps(root / "program")])


def input_fingerprint(root, skill_path, hints, program_key):
   shared_files = [Path(__file__).resolve(), TEMPLATE_PATH, PAGE_TEMPLATE_PATH]
   site_files = [root / "site.json", root / "plan" / "plan.json", root / "menu" / "hints.json", skill_path]
   endpoint_files = sorted((root / "knowledge" / "endpoints").glob("*.md"))
   watched = shared_files + site_files + endpoint_files + option_source_paths(root, hints)
   return digest([CONTRACT, program_key, [file_stamp(path) for path in watched]])


def read_hints_quietly(root):
   try:
      hints = read_json(root / "menu" / "hints.json", {})
   except (json.JSONDecodeError, OSError):
      return {}

   return hints if isinstance(hints, dict) else {}


def load_cache(out_dir):
   try:
      cache = read_json(out_dir / CACHE_NAME, {})
   except (json.JSONDecodeError, OSError):
      cache = {}

   is_current = isinstance(cache, dict) and cache.get("contract") == CONTRACT

   if not is_current:
      cache = {"contract": CONTRACT}

   cache.setdefault("builds", {})
   return cache


def save_cache(out_dir, cache):
   out_dir.mkdir(parents=True, exist_ok=True)
   write_if_changed(out_dir / CACHE_NAME, json.dumps(cache, indent=1, sort_keys=True) + "\n")


def field_problems(field, where, option_sets):
   problems = []
   control = field.get("t")
   options = field.get("o")

   if field.get("k") in NEVER_OFFERED:
      problems.append(f"{where} offers --{field.get('k')}")

   if control not in CONTROLS:
      problems.append(f"{where}: control {control} is not one of {sorted(CONTROLS)}")

   is_select = control == "select"
   names_unknown_options = isinstance(options, str) and options not in option_sets
   lacks_options = not options or names_unknown_options

   if is_select and lacks_options:
      problems.append(f"{where}: a select needs options")

   return problems


def validate_data(data):
   """Check the menu data against the contract the template reads."""
   missing_keys = [key for key in DATA_KEYS if key not in data]

   if missing_keys:
      return [f"menu data lacks {', '.join(missing_keys)}"]

   problems = []

   if data["v"] != CONTRACT:
      problems.append(f"menu data is version {data['v']}, the template reads {CONTRACT}")

   if CONTRACT_MARKER not in TEMPLATE_PATH.read_text(encoding="utf-8"):
      problems.append(f"{TEMPLATE_PATH.name} does not declare {CONTRACT_MARKER}")

   group_keys = [group.get("key") for group in data["groups"]]
   option_sets = data.get("opts") or {}

   if len(set(group_keys)) != len(group_keys):
      problems.append("two menu groups share a key")

   for field in data["global"]:
      problems.extend(field_problems(field, f"global field {field.get('k')}", option_sets))

   for command in data["commands"]:
      name = command.get("n", "?")
      missing_command_keys = [key for key in ("n", "g", "k", "s", "d") if key not in command]

      if missing_command_keys:
         problems.append(f"{name} lacks {', '.join(missing_command_keys)}")
         continue

      if command["s"] not in STATUSES:
         problems.append(f"{name} has status {command['s']}, which the template does not know")

      if command["g"] not in group_keys:
         problems.append(f"{name} is in group {command['g']}, which the menu does not show")

      is_runnable = command["s"] in RUNNABLE_STATUSES
      has_form = isinstance(command.get("f"), list)
      has_input_list = isinstance(command.get("ins"), list)
      shape_matches = has_form if is_runnable else has_input_list

      if not shape_matches:
         problems.append(f"{name}: a {command['s']} command needs {'f' if is_runnable else 'ins'}")

      for field in command.get("f") or []:
         problems.extend(field_problems(field, f"{name} field {field.get('k')}", option_sets))

   return problems


def counts_text(counts):
   pieces = [f"{counts['ready']} ready", f"{counts['verified']} verified live", f"{counts['unverified']} unverified"]

   if counts["blocked"]:
      pieces.append(f"{counts['blocked']} blocked")

   pieces.append(f"{counts['planned']} planned")
   pieces.append(f"{counts['endpoints_verified']}/{counts['endpoints']} endpoints verified")
   return ", ".join(pieces)


def build(root, mode="page", help_json_path=None, skill_md_path=None, force=False):
   """Build the page or the inline widget, reusing the last output when no input changed."""
   site = read_json(root / "site.json", {}) or {}
   slug = site.get("slug") or root.name
   skill_path = Path(skill_md_path).expanduser() if skill_md_path else default_skill_path(root, slug)
   refresh_installed_section(skill_path, slug, root)

   hints = read_hints_quietly(root)
   program_command = hints.get("program_command", slug)
   program_key = program_fingerprint(root, program_command, help_json_path)
   fingerprint = input_fingerprint(root, skill_path, hints, program_key)
   out_dir = root / "var" / "menu"
   cache = load_cache(out_dir)
   last_build = cache["builds"].get(mode) or {}
   last_files = last_build.get("files") or []
   outputs_exist = bool(last_files) and all(Path(path).is_file() for path in last_files)
   summary = cache.get("summary") or {}
   is_unchanged = last_build.get("fingerprint") == fingerprint and summary.get("fingerprint") == fingerprint
   can_reuse = is_unchanged and outputs_exist and not force

   if can_reuse:
      return {"slug": slug, "mode": mode, "files": last_files, "summary": summary, "reused": True, "help_ran": False, "fingerprint": fingerprint}

   help_cache = cache.get("help") or {}
   has_cached_help = help_cache.get("key") == program_key and isinstance(help_cache.get("data"), dict)
   help_ran = force or not has_cached_help

   if help_ran:
      program_help = run_program_help(root, program_command, help_json_path)
   else:
      program_help = (help_cache["data"], None)

   help_data, help_problem = program_help

   if help_ran and help_problem is None and isinstance(help_data, dict):
      cache["help"] = {"key": program_key, "data": {"commands": help_data.get("commands", [])}}

   data, warnings, problems = collect(root, help_json_path, skill_path, program_help)
   problems = problems + validate_data(data)
   files = write_mode_outputs(out_dir, slug, data, mode)
   summary = {"fingerprint": fingerprint, "counts": data["counts"], "warnings": warnings, "problems": problems}
   cache["summary"] = summary
   cache["builds"][mode] = {"fingerprint": fingerprint, "files": files}
   save_cache(out_dir, cache)
   return {"slug": slug, "mode": mode, "files": files, "summary": summary, "reused": False, "help_ran": help_ran, "fingerprint": fingerprint}


def server_token(page_path):
   return digest(["webapp-re-menu", str(page_path)])


def server_answers(port, token):
   connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)

   try:
      connection.request("GET", "/__menu")
      response = connection.getresponse()
      return response.status == 200 and response.read().decode("utf-8") == token
   except (OSError, http.client.HTTPException):
      return False
   finally:
      connection.close()


def ensure_server(page_path):
   """Return the port of a 127.0.0.1 server for this page, starting one when none answers."""
   state_path = Path(page_path).parent / SERVER_NAME
   token = server_token(page_path)

   try:
      state = read_json(state_path, {}) or {}
   except (json.JSONDecodeError, OSError):
      state = {}

   known_port = state.get("port")
   is_running = isinstance(known_port, int) and server_answers(known_port, token)

   if is_running:
      return known_port

   listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   listener.bind(("127.0.0.1", 0))
   listener.listen(16)
   port = listener.getsockname()[1]
   serve_command = [sys.executable, str(Path(__file__).resolve()), "serve", "--page", str(page_path), "--fd", str(listener.fileno()), "--token", token]
   subprocess.Popen(serve_command, pass_fds=(listener.fileno(),), start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
   listener.close()
   write_if_changed(state_path, json.dumps({"port": port}) + "\n")
   return port


def serve(page_path, listener_fd, token, idle_seconds=SERVER_IDLE_SECONDS):
   page = Path(page_path)
   last_request = [time.monotonic()]

   class MenuHandler(BaseHTTPRequestHandler):
      def do_GET(self):
         last_request[0] = time.monotonic()
         path = urlsplit(self.path).path

         if path == "/__menu":
            self.respond(200, "text/plain; charset=utf-8", token.encode("utf-8"))
            return

         if path == "/favicon.ico":
            self.respond(404, "text/plain; charset=utf-8", b"")
            return

         try:
            body = page.read_bytes()
         except OSError:
            self.respond(404, "text/plain; charset=utf-8", b"The menu page is not built.")
            return

         self.respond(200, "text/html; charset=utf-8", body)

      def respond(self, status, content_type, body):
         self.send_response(status)
         self.send_header("Content-Type", content_type)
         self.send_header("Content-Length", str(len(body)))
         self.send_header("Cache-Control", "no-store")
         self.end_headers()
         self.wfile.write(body)

      def log_message(self, *arguments):
         pass

   server = HTTPServer(("127.0.0.1", 0), MenuHandler, bind_and_activate=False)
   server.socket.close()
   server.socket = socket.socket(fileno=listener_fd)
   server.timeout = min(5, idle_seconds)

   while time.monotonic() - last_request[0] < idle_seconds:
      server.handle_request()

   server.server_close()


def refresh_installed_section(skill_path, slug, root):
   if not skill_path.is_file():
      return False

   original = skill_path.read_text(encoding="utf-8")
   has_block = SECTION_START in original and SECTION_END in original

   if not has_block:
      return False

   refreshed = install_section(original, slug, root)

   if refreshed == original:
      return False

   skill_path.write_text(refreshed, encoding="utf-8")
   return True


def section_text(slug, root):
   pipeline = home_relative(MENU_DIR.parent)
   site_root = home_relative(root)
   template = SECTION_PATH.read_text(encoding="utf-8")

   return template.replace("{pipeline}", pipeline).replace("{root}", site_root).replace("{slug}", slug).strip()


def install_section(skill_text, slug, root):
   section_body = section_text(slug, root)
   block = f"{SECTION_START}\n{section_body}\n{SECTION_END}"
   has_block = SECTION_START in skill_text and SECTION_END in skill_text

   if has_block:
      before = skill_text.split(SECTION_START, 1)[0]
      after = skill_text.split(SECTION_END, 1)[1]
      return before + block + after

   for anchor in ("\n## Errors", "\n## Provenance"):
      if anchor in skill_text:
         before, after = skill_text.split(anchor, 1)
         return before.rstrip("\n") + "\n\n" + block + "\n" + anchor + after

   return skill_text.rstrip("\n") + "\n\n" + block + "\n"


def add_menu_to_description(skill_text):
   """Return the updated text, a problem that blocks the write, and a warning."""
   match = re.search(r"^description: (.*)$", skill_text, re.MULTILINE)

   if not match:
      return skill_text, None, "no description line in the frontmatter, so add menu to it by hand"

   description = match.group(1)
   already_listed = re.search(r"Commands: help, menu\b", description)

   if already_listed:
      return skill_text, None, None

   if "Commands: help, " not in description:
      return skill_text, None, "the description has no 'Commands: help, ' list, so add menu to it by hand"

   updated = description.replace("Commands: help, ", "Commands: help, menu, ", 1)
   is_quoted = updated.startswith('"') and updated.endswith('"')
   value = updated[1:-1] if is_quoted else updated

   if len(value) > DESCRIPTION_LIMIT:
      return skill_text, f"adding menu would make the description {len(value)} characters, over {DESCRIPTION_LIMIT}", None

   return skill_text[: match.start(1)] + updated + skill_text[match.end(1):], None, None


def install(root, skill_md_path=None):
   site = read_json(root / "site.json", {}) or {}
   slug = site.get("slug") or root.name
   skill_path = Path(skill_md_path).expanduser() if skill_md_path else default_skill_path(root, slug)

   if not skill_path.is_file():
      raise MenuError(f"No skill at {skill_path}. Run /webapp-re:engineer {slug} first.")

   original = skill_path.read_text(encoding="utf-8")
   with_section = install_section(original, slug, root)
   updated, problem, warning = add_menu_to_description(with_section)
   problems = [problem] if problem else []
   warnings = [warning] if warning else []
   changed = updated != original and not problems

   if changed:
      skill_path.write_text(updated, encoding="utf-8")

   return {"skill_md": str(skill_path), "changed": changed, "warnings": warnings, "problems": problems}


def site_roots(site_argument):
   if site_argument != "all":
      return [resolve_root(site_argument)]

   return sorted(path.parent for path in webapp_re_home().glob("*/site.json"))


def compact_line(fields):
   kept = {key: value for key, value in fields.items() if value not in (None, [], "")}
   return json.dumps(kept, ensure_ascii=False, separators=(",", ":"))


def build_line(result, serve_page=True):
   summary = result["summary"]
   fields = {"counts": counts_text(summary["counts"]), "warnings": summary["warnings"], "problems": summary["problems"]}

   if summary["problems"]:
      return compact_line(fields)

   files = result["files"]

   if result["mode"] == "inline":
      chars = sum(len(Path(path).read_text(encoding="utf-8")) for path in files)
      return compact_line({"inline": files, "chars": chars, **fields})

   if serve_page:
      port = ensure_server(files[0])
      opened = f"http://127.0.0.1:{port}/{result['slug']}?v={result['fingerprint'][:10]}"
   else:
      opened = Path(files[0]).as_uri()

   return compact_line({"open": opened, **fields})


def check_line(root, help_json_path, skill_md_path):
   data, warnings, problems = collect(root, help_json_path, skill_md_path)
   problems = problems + validate_data(data)
   page_chars = len(render_page(render_widget(data), data["site"]["slug"]))
   fields = {"site": data["site"]["slug"], "counts": counts_text(data["counts"]), "page_chars": page_chars, "warnings": warnings, "problems": problems}
   return compact_line(fields), bool(problems)


def install_line(root, skill_md_path, only_integrated):
   site = read_json(root / "site.json", {}) or {}
   slug = site.get("slug") or root.name
   skill_path = Path(skill_md_path).expanduser() if skill_md_path else default_skill_path(root, slug)
   skill_text = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
   is_integrated = SECTION_START in skill_text

   if only_integrated and not is_integrated:
      return compact_line({"site": slug, "skipped": "no menu section yet"}), False

   result = install(root, skill_md_path)
   return compact_line({"site": slug, **result}), bool(result["problems"])


def main(argv=None):
   parser = argparse.ArgumentParser(description="Build the command menu of a webapp-re site skill.")
   subcommands = parser.add_subparsers(dest="action", required=True)

   for action in ("build", "check", "install"):
      subparser = subcommands.add_parser(action)
      subparser.add_argument("--site", required=True, help="Site slug under WEBAPP_RE_HOME or a site root; check and install also take all")
      subparser.add_argument("--skill-md", help="Site skill file, defaults to <root>/plugin/skills/<slug>/SKILL.md")

      if action != "install":
         subparser.add_argument("--help-json", help="Use this file instead of running the program's help")

      if action == "build":
         modes = subparser.add_mutually_exclusive_group()
         modes.add_argument("--inline", action="store_true", help="Write the slim widget for show_widget instead of the page")
         modes.add_argument("--file", "--standalone", dest="file", action="store_true", help="Print the page's file URL instead of serving it")
         subparser.add_argument("--force", action="store_true", help="Rebuild and rerun the program's help even when nothing changed")

   server_parser = subcommands.add_parser("serve")
   server_parser.add_argument("--page", required=True)
   server_parser.add_argument("--fd", type=int, required=True)
   server_parser.add_argument("--token", required=True)
   server_parser.add_argument("--idle", type=int, default=SERVER_IDLE_SECONDS)

   arguments = parser.parse_args(argv)

   if arguments.action == "serve":
      serve(arguments.page, arguments.fd, arguments.token, arguments.idle)
      return 0

   try:
      if arguments.action == "build":
         root = resolve_root(arguments.site)
         mode = "inline" if arguments.inline else "page"
         result = build(root, mode, arguments.help_json, arguments.skill_md, arguments.force)
         print(build_line(result, serve_page=not arguments.file))
         return 1 if result["summary"]["problems"] else 0

      roots = site_roots(arguments.site)
      any_problems = False

      for root in roots:
         if arguments.action == "check":
            line, has_problems = check_line(root, arguments.help_json, arguments.skill_md)
         else:
            line, has_problems = install_line(root, arguments.skill_md, only_integrated=arguments.site == "all")

         print(line)
         any_problems = any_problems or has_problems

      return 1 if any_problems else 0
   except MenuError as error:
      print(compact_line({"problems": [str(error)]}))
      return 1


if __name__ == "__main__":
   sys.exit(main())
