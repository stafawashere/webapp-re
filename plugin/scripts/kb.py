#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Per-site knowledge base for the webapp-re skill.

    uv run --script kb.py init --site https://app.example.com
    uv run --script kb.py new-run --site example --goal "list my saved items"
    uv run --script kb.py record-finding --site example --run <run> --goal "list my saved items" --method GET --url <url>
    uv run --script kb.py verify --site example --run <run> --id <finding> --result pass --detail "<observed>"
    uv run --script kb.py close-run --site example --run <run> --requests 3 --takeaway "<lesson>"

Every subcommand takes either --site (a URL, host or slug, resolved under $WEBAPP_RE_HOME)
or --root (an explicit site directory). Stdlib only.
"""

import argparse
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import urlparse

DEFAULT_HOME = os.path.expanduser("~/dev/webapp-re/apps")
STATUS_VALUES = ("hypothesis", "verified", "stale", "dead")
SURFACE_VALUES = ("rest", "graphql", "rpc", "websocket", "sse", "html", "unknown")
PATTERN_KINDS = ("dead-end", "noise", "quirk", "technique", "surface", "pacing", "auth")
TWO_PART_SUFFIXES = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.jp", "co.nz", "com.br", "co.in", "com.mx", "co.za", "com.tr", "com.cn"}
LIST_FIELDS = ("runs", "required_headers", "required_cookies")
FRONT_FENCE = "---"
WORKSPACE_GITIGNORE = """.env
.env.*
!.env.example
var/
*.session.json
.session.json
optimize/*/before/
.claude/
plugin/
.venv/
node_modules/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
"""

SECRET_PATTERNS = [
   ("cookie assignment", re.compile(r"(?i)\b(session(id)?|sid|csrftoken|xsrf-token|auth[_-]?token|access[_-]?token|refresh[_-]?token)\s*[=:]\s*[\"']?[A-Za-z0-9%._\-]{16,}")),
   ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
   ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
   ("cookie header", re.compile(r"(?i)^\s*cookie\s*:\s*\S+=\S{12,}", re.MULTILINE)),
]
HIGH_ENTROPY_TOKEN = re.compile(r"[A-Za-z0-9+/_\-]{40,}={0,2}")
ENTROPY_THRESHOLD = 4.3


def today():
   return datetime.now().strftime("%Y-%m-%d")


def stamp():
   return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def slugify(text):
   collapsed = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())

   return collapsed.strip("-")[:60] or "unnamed"


def site_slug(site):
   looks_like_slug = re.fullmatch(r"[a-z0-9][a-z0-9-]*", site) is not None and "." not in site
   if looks_like_slug:
      return site

   host = urlparse(site if "//" in site else "https://" + site).hostname or site
   labels = host.lower().split(".")
   last_two = ".".join(labels[-2:])
   has_two_part_suffix = last_two in TWO_PART_SUFFIXES and len(labels) >= 3

   if has_two_part_suffix:
      return slugify(labels[-3])

   if len(labels) >= 2:
      return slugify(labels[-2])

   return slugify(labels[0])


def resolve_root(args):
   if getattr(args, "root", None):
      return os.path.abspath(os.path.expanduser(args.root))

   if not getattr(args, "site", None):
      sys.exit("kb: pass --site or --root")

   home = os.environ.get("WEBAPP_RE_HOME", DEFAULT_HOME)
   slug = args.slug if getattr(args, "slug", None) else site_slug(args.site)

   return os.path.join(os.path.expanduser(home), slug)


class Paths:
   def __init__(self, root):
      self.root = root
      self.knowledge = os.path.join(root, "knowledge")
      self.endpoints = os.path.join(self.knowledge, "endpoints")
      self.patterns = os.path.join(self.knowledge, "patterns")
      self.index = os.path.join(self.knowledge, "INDEX.md")
      self.changelog = os.path.join(self.knowledge, "CHANGELOG.md")
      self.sessions = os.path.join(self.knowledge, "sessions.md")
      self.toolkit = os.path.join(root, "toolkit", "js")
      self.runs = os.path.join(root, "var", "runs")
      self.logs = os.path.join(root, "var", "logs")
      self.captures = os.path.join(root, "var", "captures")

   def require(self):
      if not os.path.isdir(self.knowledge):
         sys.exit("kb: no knowledge base at {0}, run kb.py init first".format(self.root))


def parse_front_matter(raw):
   lines = raw.splitlines()
   has_fence = bool(lines) and lines[0].strip() == FRONT_FENCE

   if not has_fence:
      return {}, raw

   meta = {}
   body_start = len(lines)

   for line_number in range(1, len(lines)):
      line = lines[line_number]

      if line.strip() == FRONT_FENCE:
         body_start = line_number + 1
         break

      key, separator, value = line.partition(":")
      if not separator:
         continue

      meta[key.strip()] = decode_value(value.strip())

   return meta, "\n".join(lines[body_start:]).lstrip("\n")


def decode_value(value):
   is_list = value.startswith("[") and value.endswith("]")

   if is_list:
      inner = value[1:-1].strip()
      return [item.strip() for item in inner.split(",") if item.strip()] if inner else []

   if re.fullmatch(r"-?\d+", value):
      return int(value)

   return value


def encode_value(value):
   if isinstance(value, list):
      return "[" + ", ".join(str(item) for item in value) + "]"

   return str(value)


def render_document(meta, body):
   header = [FRONT_FENCE] + ["{0}: {1}".format(key, encode_value(value)) for key, value in meta.items()] + [FRONT_FENCE]

   return "\n".join(header) + "\n\n" + body.rstrip("\n") + "\n"


def read_document(path):
   with open(path, encoding="utf-8") as handle:
      return parse_front_matter(handle.read())


def write_text(path, text):
   os.makedirs(os.path.dirname(path), exist_ok=True)

   with open(path, "w", encoding="utf-8") as handle:
      handle.write(text)


def append_text(path, text):
   os.makedirs(os.path.dirname(path), exist_ok=True)

   with open(path, "a", encoding="utf-8") as handle:
      handle.write(text)


def log_event(paths, run, event, **fields):
   record = {"at": datetime.now().isoformat(timespec="seconds"), "run": run, "event": event}
   record.update(fields)
   append_text(os.path.join(paths.logs, "kb-{0}.jsonl".format(today())), json.dumps(record) + "\n")


def changelog(paths, line):
   append_text(paths.changelog, "- {0} {1}\n".format(today(), line))


def documents(directory):
   if not os.path.isdir(directory):
      return []

   names = sorted(name for name in os.listdir(directory) if name.endswith(".md") and not name.startswith("_"))

   return [(name[:-3],) + read_document(os.path.join(directory, name)) for name in names]


def command_init(args):
   root = resolve_root(args)
   paths = Paths(root)

   for directory in (paths.endpoints, paths.patterns, paths.toolkit, paths.runs, paths.logs, paths.captures,
                     os.path.join(root, "scope"), os.path.join(root, "plan"), os.path.join(root, "openapi")):
      os.makedirs(directory, exist_ok=True)

   site_file = os.path.join(root, "site.json")
   if not os.path.exists(site_file):
      origin = args.site if args.site and "." in args.site else ""
      site = {"slug": os.path.basename(root), "origins": [origin] if origin else [], "created": today(), "browser_path": ""}
      write_text(site_file, json.dumps(site, indent=3) + "\n")

   gitignore = os.path.join(root, ".gitignore")
   if not os.path.exists(gitignore):
      write_text(gitignore, WORKSPACE_GITIGNORE)

   has_own_repo = os.path.isdir(os.path.join(root, ".git"))
   if not has_own_repo:
      subprocess.run(["git", "init", "--quiet", root], check=False)

   if not os.path.exists(paths.sessions):
      write_text(paths.sessions, "# Sessions\n\nAppend-only ledger, one entry per closed run, newest last.\n")

   if not os.path.exists(paths.changelog):
      write_text(paths.changelog, "# Changelog\n\n")

   rebuild_index(paths)
   has_plugin = os.path.isfile(os.path.join(root, "plugin", ".claude-plugin", "plugin.json"))
   if not has_plugin:
      scaffold_site_plugin(root)

   print(root)


def scaffold_site_plugin(root):
   generator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_plugin.py")
   generator_spec = importlib.util.spec_from_file_location("site_plugin", generator_path)
   site_plugin = importlib.util.module_from_spec(generator_spec)
   generator_spec.loader.exec_module(site_plugin)
   result = site_plugin.scaffold(site_plugin.Path(root))
   print("kb: plugin scaffolded at {0}, marketplace {1}".format(result["plugin"], result["marketplace"]["path"]), file=sys.stderr)


def command_path(args):
   print(resolve_root(args))


def command_stats(args):
   paths = Paths(resolve_root(args))
   paths.require()
   findings = documents(paths.endpoints)
   patterns = documents(paths.patterns)
   by_status = Counter(meta.get("status", "unknown") for _, meta, _ in findings)
   cutoff = (datetime.now() - timedelta(days=args.stale_after)).strftime("%Y-%m-%d")
   aged = [identifier for identifier, meta, _ in findings if meta.get("status") == "verified" and str(meta.get("last_verified", "")) < cutoff]
   promotable = [identifier for identifier, meta, _ in patterns if int(meta.get("seen", 1)) >= 3]

   print("root: {0}".format(paths.root))
   print("findings: {0} ({1})".format(len(findings), ", ".join("{0} {1}".format(count, status) for status, count in sorted(by_status.items())) or "none"))
   print("patterns: {0}".format(len(patterns)))
   print("verified but older than {0} days: {1}".format(args.stale_after, ", ".join(aged) or "none"))
   print("patterns seen 3 or more times: {0}".format(", ".join(promotable) or "none"))


def matching(entries, goal):
   words = {word for word in re.findall(r"[a-z0-9]{3,}", goal.lower())}
   hits = []

   for identifier, meta, body in entries:
      haystack = (identifier + " " + str(meta.get("goal", "")) + " " + str(meta.get("title", "")) + " " + body).lower()
      score = sum(1 for word in words if word in haystack)
      if score:
         hits.append((score, identifier, meta))

   return sorted(hits, key=lambda hit: -hit[0])


def command_new_run(args):
   paths = Paths(resolve_root(args))
   paths.require()
   run = "run-{0}".format(stamp())
   finding_hits = matching(documents(paths.endpoints), args.goal)
   pattern_hits = matching(documents(paths.patterns), args.goal)

   lines = ["# {0}".format(run), "", "Goal: {0}".format(args.goal), "", "## Matching findings", ""]
   lines += ["- {0} ({1}, verified {2}x, last {3})".format(identifier, meta.get("status"), meta.get("verify_count", 0), meta.get("last_verified", "never")) for _, identifier, meta in finding_hits[:10]] or ["- none"]
   lines += ["", "## Matching patterns", ""]
   lines += ["- {0}: {1}".format(identifier, meta.get("title", "")) for _, identifier, meta in pattern_hits[:10]] or ["- none"]
   lines += ["", "## UI action sequence", "", "1. ", "", "## Candidates and rejections", "", "## Requests spent", "", "0", ""]

   write_text(os.path.join(paths.runs, run, "notes.md"), "\n".join(lines))
   log_event(paths, run, "new_run", goal_length=len(args.goal))
   print("\n".join(lines))

   if os.path.exists(paths.sessions):
      with open(paths.sessions, encoding="utf-8") as handle:
         tail = handle.read().strip().split("\n## ")[-3:]
      print("## Last sessions\n\n## " + "\n## ".join(tail) if len(tail) > 1 else "")

   print("run: {0}".format(run))


def command_record_finding(args):
   paths = Paths(resolve_root(args))
   paths.require()

   if args.status == "verified":
      sys.exit("kb: a finding becomes verified only through kb.py verify")

   identifier = args.id or slugify(args.goal)
   path = os.path.join(paths.endpoints, identifier + ".md")
   exists = os.path.exists(path)
   meta, body = read_document(path) if exists else ({}, "")
   contract_changed = exists and (meta.get("url") != args.url or str(meta.get("operation_id", "")) != (args.operation_id or "") or meta.get("method") != args.method.upper())

   meta.update({
      "id": identifier,
      "goal": args.goal,
      "method": args.method.upper(),
      "url": args.url,
      "surface": args.surface,
      "operation": args.operation or meta.get("operation", ""),
      "operation_id": args.operation_id or "",
      "status": args.status,
      "required_headers": split_names(args.headers) or meta.get("required_headers", []),
      "required_cookies": split_names(args.cookies) or meta.get("required_cookies", []),
      "first_seen": meta.get("first_seen", today()),
      "last_seen": today(),
      "last_verified": "" if contract_changed else meta.get("last_verified", ""),
      "verify_count": 0 if contract_changed else meta.get("verify_count", 0),
      "fail_count": 0 if contract_changed else meta.get("fail_count", 0),
      "runs": sorted(set(meta.get("runs", [])) | {args.run}),
   })

   if not body:
      body = finding_body(args)
   else:
      body = body.rstrip("\n") + "\n\n### {0} {1}\n\n{2}\n".format(today(), args.run, args.notes or "Contract re-recorded.")

   write_text(path, render_document(meta, body))
   changelog(paths, "finding {0} recorded as {1} in {2}{3}".format(identifier, args.status, args.run, ", contract changed, tallies reset" if contract_changed else ""))
   log_event(paths, args.run, "record_finding", id=identifier, status=args.status)
   rebuild_index(paths)
   print(path)


def split_names(raw):
   return [name.strip() for name in (raw or "").split(",") if name.strip()]


def finding_body(args):
   replay = {"method": args.method.upper(), "url": args.url, "headers": split_names(args.headers), "body": None}

   return "\n".join([
      "## Goal", "", args.goal, "",
      "## Request", "", "```", "{0} {1}".format(args.method.upper(), args.url), "```", "",
      "## Headers that matter", "", args.headers_notes or "Names in front matter. Where each value comes from: fill in.", "",
      "## Cookies that gate it", "", ", ".join(split_names(args.cookies)) or "unknown", "",
      "## Request body", "", args.body_shape or "Field names and value shapes, no values.", "",
      "## Response, trimmed", "", args.response_shape or "Paste shape.py output trimmed to what answers the goal.", "",
      "## Success signal", "", args.success or "unknown", "",
      "## Failure signals", "", args.failure or "unknown", "",
      "## Notes", "", args.notes or "", "",
      "## Replay template", "", "```json", json.dumps(replay, indent=3), "```", "",
      "## Verification history", "",
   ])


def command_verify(args):
   paths = Paths(resolve_root(args))
   paths.require()
   path = os.path.join(paths.endpoints, args.id + ".md")

   if not os.path.exists(path):
      sys.exit("kb: no finding {0}".format(args.id))

   meta, body = read_document(path)
   passed = args.result == "pass"

   if passed:
      meta["verify_count"] = int(meta.get("verify_count", 0)) + 1
      meta["last_verified"] = today()
      meta["status"] = "verified"
   else:
      meta["fail_count"] = int(meta.get("fail_count", 0)) + 1
      meta["status"] = "stale"

   meta["runs"] = sorted(set(meta.get("runs", [])) | {args.run})
   body = body.rstrip("\n") + "\n- {0} {1} {2}: {3}\n".format(today(), args.run, args.result, args.detail)
   write_text(path, render_document(meta, body))
   changelog(paths, "finding {0} replay {1} in {2}, now {3}".format(args.id, args.result, args.run, meta["status"]))
   log_event(paths, args.run, "verify", id=args.id, result=args.result)
   rebuild_index(paths)
   print("{0}: {1}, verify_count {2}, fail_count {3}".format(args.id, meta["status"], meta.get("verify_count", 0), meta.get("fail_count", 0)))


def command_record_pattern(args):
   paths = Paths(resolve_root(args))
   paths.require()
   identifier = args.id or slugify(args.title)
   path = os.path.join(paths.patterns, identifier + ".md")
   exists = os.path.exists(path)
   meta, body = read_document(path) if exists else ({}, "")

   meta.update({
      "id": identifier,
      "kind": args.kind,
      "title": args.title,
      "seen": int(meta.get("seen", 0)) + 1,
      "first_seen": meta.get("first_seen", today()),
      "last_seen": today(),
      "runs": sorted(set(meta.get("runs", [])) | {args.run}),
   })

   if not body:
      body = "## Lesson\n\n{0}\n\n## Action next time\n\n{1}\n\n## Sightings\n".format(args.lesson, args.action)

   body = body.rstrip("\n") + "\n- {0} {1}\n".format(today(), args.run)
   write_text(path, render_document(meta, body))
   changelog(paths, "pattern {0} {1} in {2}".format(identifier, "bumped" if exists else "added", args.run))
   log_event(paths, args.run, "record_pattern", id=identifier, kind=args.kind)
   rebuild_index(paths)
   print(path)


def rebuild_index(paths):
   findings = documents(paths.endpoints)
   patterns = documents(paths.patterns)
   scripts = sorted(name for name in os.listdir(paths.toolkit)) if os.path.isdir(paths.toolkit) else []

   lines = ["# Index", "", "Generated by kb.py. Do not hand edit.", "", "## Findings", ""]
   lines += ["| id | status | method | url | operation | verified | last verified |", "|---|---|---|---|---|---|---|"]
   lines += ["| [{0}](endpoints/{0}.md) | {1} | {2} | `{3}` | {4} | {5} | {6} |".format(identifier, meta.get("status", ""), meta.get("method", ""), meta.get("url", ""), meta.get("operation", ""), meta.get("verify_count", 0), meta.get("last_verified", "")) for identifier, meta, _ in findings]
   lines += ["", "## Patterns", "", "| id | kind | title | seen |", "|---|---|---|---|"]
   lines += ["| [{0}](patterns/{0}.md) | {1} | {2} | {3} |".format(identifier, meta.get("kind", ""), meta.get("title", ""), meta.get("seen", 1)) for identifier, meta, _ in patterns]
   lines += ["", "## Toolkit scripts", ""]
   lines += ["- `toolkit/js/{0}`".format(name) for name in scripts] or ["- none"]

   write_text(paths.index, "\n".join(lines) + "\n")


def command_index(args):
   paths = Paths(resolve_root(args))
   paths.require()
   rebuild_index(paths)
   print(paths.index)


def shannon_entropy(text):
   counts = Counter(text)
   total = len(text)

   return -sum((count / total) * math.log2(count / total) for count in counts.values())


def find_secrets(paths):
   problems = []
   scanned_roots = (paths.knowledge, os.path.dirname(paths.toolkit), paths.logs, paths.runs)

   for scanned_root in scanned_roots:
      for directory, _, names in os.walk(scanned_root):
         for name in names:
            file_path = os.path.join(directory, name)

            try:
               with open(file_path, encoding="utf-8", errors="replace") as handle:
                  text = handle.read()
            except OSError:
               continue

            for label, pattern in SECRET_PATTERNS:
               for match in pattern.finditer(text):
                  problems.append((file_path, text.count("\n", 0, match.start()) + 1, label))

            for match in HIGH_ENTROPY_TOKEN.finditer(text):
               token = match.group(0)
               is_hex_digest = re.fullmatch(r"[0-9a-f]{40,64}", token) is not None
               is_random_looking = shannon_entropy(token) >= ENTROPY_THRESHOLD
               if is_random_looking and not is_hex_digest:
                  problems.append((file_path, text.count("\n", 0, match.start()) + 1, "high-entropy token"))

   return problems


def command_scan_secrets(args):
   paths = Paths(resolve_root(args))
   paths.require()
   problems = find_secrets(paths)

   for file_path, line_number, label in problems:
      print("{0}:{1}: {2}".format(file_path, line_number, label))

   print("scan: {0} possible secrets".format(len(problems)))
   sys.exit(1 if problems else 0)


def command_close_run(args):
   paths = Paths(resolve_root(args))
   paths.require()
   problems = find_secrets(paths)

   if problems:
      for file_path, line_number, label in problems:
         print("{0}:{1}: {2}".format(file_path, line_number, label))
      sys.exit("kb: refusing to close, {0} possible secrets on disk".format(len(problems)))

   events = []
   log_path = os.path.join(paths.logs, "kb-{0}.jsonl".format(today()))
   if os.path.isdir(paths.logs):
      kb_log_names = [name for name in sorted(os.listdir(paths.logs)) if name.startswith("kb-") and name.endswith(".jsonl")]
      for name in kb_log_names:
         with open(os.path.join(paths.logs, name), encoding="utf-8") as handle:
            events += [json.loads(line) for line in handle if line.strip() and json.loads(line).get("run") == args.run]

   mutations = [event for event in events if event["event"] in ("record_finding", "verify", "record_pattern")]
   learned_nothing_unstated = not mutations and not args.learned_nothing
   if learned_nothing_unstated:
      sys.exit("kb: the run mutated nothing; pass --learned-nothing to say so deliberately")

   touched = sorted({event.get("id") for event in mutations if event.get("id")})
   entry = [
      "", "## {0}".format(args.run), "",
      "- closed {0}, browser {1}, live requests {2}".format(today(), args.browser or "unknown", args.requests),
      "- touched: {0}".format(", ".join(touched) or "nothing"),
      "- takeaway: {0}".format(args.takeaway),
      "- still open: {0}".format(args.open or "nothing recorded"),
      "",
   ]
   append_text(paths.sessions, "\n".join(entry))
   log_event(paths, args.run, "close_run", requests=args.requests, touched=len(touched))
   rebuild_index(paths)
   print("\n".join(entry).strip())
   print("log: {0}".format(log_path))


def build_parser():
   parser = argparse.ArgumentParser(description="Per-site reverse engineering knowledge base")
   commands = parser.add_subparsers(dest="command", required=True)

   def add(name, handler):
      sub = commands.add_parser(name)
      sub.add_argument("--site", help="URL, host or slug")
      sub.add_argument("--slug", help="override the derived slug")
      sub.add_argument("--root", help="explicit site directory instead of --site")
      sub.set_defaults(handler=handler)
      return sub

   add("init", command_init)
   add("path", command_path)
   add("stats", command_stats).add_argument("--stale-after", type=int, default=30)
   add("new-run", command_new_run).add_argument("--goal", required=True)

   finding = add("record-finding", command_record_finding)
   finding.add_argument("--run", required=True)
   finding.add_argument("--goal", required=True)
   finding.add_argument("--id")
   finding.add_argument("--method", required=True)
   finding.add_argument("--url", required=True)
   finding.add_argument("--surface", choices=SURFACE_VALUES, default="unknown")
   finding.add_argument("--operation")
   finding.add_argument("--operation-id")
   finding.add_argument("--status", choices=STATUS_VALUES, default="hypothesis")
   finding.add_argument("--headers", help="comma separated header names that matter")
   finding.add_argument("--headers-notes")
   finding.add_argument("--cookies", help="comma separated cookie names that gate it")
   finding.add_argument("--body-shape")
   finding.add_argument("--response-shape")
   finding.add_argument("--success")
   finding.add_argument("--failure")
   finding.add_argument("--notes")

   verify = add("verify", command_verify)
   verify.add_argument("--run", required=True)
   verify.add_argument("--id", required=True)
   verify.add_argument("--result", choices=("pass", "fail"), required=True)
   verify.add_argument("--detail", required=True)

   pattern = add("record-pattern", command_record_pattern)
   pattern.add_argument("--run", required=True)
   pattern.add_argument("--id")
   pattern.add_argument("--kind", choices=PATTERN_KINDS, required=True)
   pattern.add_argument("--title", required=True)
   pattern.add_argument("--lesson", required=True)
   pattern.add_argument("--action", required=True)

   add("index", command_index)
   add("scan-secrets", command_scan_secrets)

   close = add("close-run", command_close_run)
   close.add_argument("--run", required=True)
   close.add_argument("--requests", type=int, required=True)
   close.add_argument("--takeaway", required=True)
   close.add_argument("--open")
   close.add_argument("--browser")
   close.add_argument("--learned-nothing", action="store_true")

   return parser


def main():
   args = build_parser().parse_args()
   args.handler(args)


if __name__ == "__main__":
   main()
