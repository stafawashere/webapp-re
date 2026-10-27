#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fold the scope-probe.js outputs of one walk into a short report and a resumable state file.

    uv run --script walk_summary.py <capture-dir>
    uv run --script walk_summary.py <capture-dir> --endpoint "/pulls/inbox/queries?filter&max_pr_age"
    uv run --script walk_summary.py <capture-dir> --draft-scope draft.json

Reads every *.json probe file in the directory, writes <capture-dir>/walk.json (visited pages,
frontier, endpoints, noise, render verdict) and prints names and counts only. A walk that stops
halfway resumes from walk.json: visited patterns are skipped, the frontier is what is left.
"""

import argparse
import json
import pathlib
import re
import sys

SHELL_NOISE_SHARE = 0.5
SHELL_NOISE_MIN_PAGES = 3
SECRET_KEY = re.compile(r"(?i)(cookie|token|secret|session|password|api[-_]?key|auth)")


def load_probes(capture_dir):
   probes = []

   for path in sorted(capture_dir.glob("*.json")):
      if path.name in ("walk.json", "draft-scope.json"):
         continue

      try:
         probe = json.loads(path.read_text(encoding="utf-8"))
      except (ValueError, UnicodeDecodeError):
         print("skipped unreadable probe: {0}".format(path.name), file=sys.stderr)
         continue

      is_probe = isinstance(probe, dict) and "url" in probe and "calls" in probe
      if is_probe:
         probe["_file"] = path.name
         probes.append(probe)

   return probes


def fold(probes):
   endpoints = {}
   noise = {}
   call_pages = {}
   visited = []

   for probe in probes:
      visited.append(probe["url"])
      endpoints.setdefault(probe["url"], {"pattern": probe["url"], "via": "document", "pages": 1, "header_names": [], "shape": [], "status": probe.get("status", 0)})

      for pattern, count in probe.get("noise", {}).items():
         noise[pattern] = noise.get(pattern, 0) + count

      for call in probe.get("calls", []):
         record = endpoints.setdefault(call["pattern"], {"pattern": call["pattern"], "via": call["via"], "pages": 0, "header_names": [], "shape": [], "status": call.get("status", 0)})
         record["pages"] += 1
         call_pages.setdefault(call["pattern"], set()).add(probe["url"])

      for shape in probe.get("shapes", []):
         if "pattern" not in shape:
            continue

         record = endpoints.setdefault(shape["pattern"], {"pattern": shape["pattern"], "via": "fetch", "pages": 0, "header_names": [], "shape": [], "status": 0})
         record["header_names"] = sorted(set(record["header_names"]) | set(shape.get("headerNames", [])))
         record["shape"] = record["shape"] or shape.get("shape", [])
         record["type"] = shape.get("type", "")
         record["status"] = shape.get("status", record["status"])

   page_count = max(len(probes), 1)
   shell_threshold = max(SHELL_NOISE_MIN_PAGES, page_count * SHELL_NOISE_SHARE)

   for pattern, pages in call_pages.items():
      is_shell_poll = len(pages) >= shell_threshold and pattern not in visited
      if is_shell_poll:
         noise[pattern] = noise.get(pattern, 0) + len(pages)
         endpoints[pattern]["noise"] = True

   return endpoints, noise, visited


def frontier_of(probes, visited):
   seen = set(visited)
   frontier = {}

   for probe in probes:
      for link in probe.get("links", []):
         pattern = link["pattern"]
         is_new = pattern not in seen and pattern not in frontier
         if is_new:
            frontier[pattern] = {"pattern": pattern, "sample": link.get("sample", ""), "count": link["count"], "kind": link_kind(pattern)}

      for pattern in probe.get("pagination", {}).get("links", []):
         if pattern not in seen:
            frontier[pattern] = {"pattern": pattern, "sample": "", "count": 1, "kind": "pagination"}

   return sorted(frontier.values(), key=lambda entry: (entry["kind"] != "pagination", entry["kind"] != "detail", -entry["count"]))


def link_kind(pattern):
   has_id = "{id}" in pattern
   has_page_key = re.search(r"[?&](page|after|before|cursor|offset)", pattern) is not None

   if has_page_key:
      return "pagination"
   if has_id:
      return "detail"

   return "nav"


def page_render(probe, endpoints):
   real_calls = [call for call in probe.get("calls", []) if not endpoints.get(call["pattern"], {}).get("noise")]

   return "server" if len(real_calls) <= 2 else "api"


def render_verdict(probes, endpoints):
   server = sum(1 for probe in probes if page_render(probe, endpoints) == "server")
   api = len(probes) - server

   if not probes:
      return "unknown"

   return "server-rendered" if server >= api else "api-driven"


def timing_cleared(probes):
   return any(probe.get("timing", {}).get("clearCalls", 0) > 0 for probe in probes)


def safe_names(names):
   return [name for name in names if not SECRET_KEY.search(name) or name.lower() in ("set-cookie", "cookie")]


def draft_scope(probes, endpoints, noise):
   pages = []

   for index, probe in enumerate(probes):
      page_endpoints = [probe["url"]] + [call["pattern"] for call in probe.get("calls", []) if not endpoints.get(call["pattern"], {}).get("noise")]
      pages.append({
         "id": "page-{0:02d}".format(index + 1),
         "url_pattern": probe["url"],
         "purpose": probe.get("title", ""),
         "endpoints": sorted(set(page_endpoints)),
         "forms": probe.get("forms", []),
         "visited": True,
      })

   endpoint_list = []
   for pattern, record in endpoints.items():
      if record.get("noise"):
         continue

      is_document = record["via"] == "document"
      endpoint_list.append({
         "id": pattern,
         "method": "GET",
         "url_pattern": pattern,
         "surface": "html" if is_document or "html" in record.get("type", "") else ("rest" if "json" in record.get("type", "") else "unknown"),
         "observed": True,
         "response_header_names": record["header_names"],
         "response_shape": record["shape"],
      })

   return {"pages": pages, "endpoints": endpoint_list, "noise": sorted(noise)}


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("capture_dir")
   parser.add_argument("--endpoint", help="print the shape and header names of one endpoint pattern")
   parser.add_argument("--draft-scope", help="write a draft pages and endpoints file for scope.json")
   args = parser.parse_args()

   capture_dir = pathlib.Path(args.capture_dir)
   probes = load_probes(capture_dir)
   endpoints, noise, visited = fold(probes)
   frontier = frontier_of(probes, visited)

   state = {
      "visited": visited,
      "frontier": frontier,
      "render": render_verdict(probes, endpoints),
      "timing_cleared": timing_cleared(probes),
      "noise": noise,
      "endpoints": endpoints,
   }
   (capture_dir / "walk.json").write_text(json.dumps(state, indent=3), encoding="utf-8")

   if args.endpoint:
      record = endpoints.get(args.endpoint)
      if not record:
         sys.exit("no endpoint {0}".format(args.endpoint))

      print("headers: {0}".format(", ".join(safe_names(record["header_names"]))))
      for line in record["shape"]:
         print(line)

      return

   if args.draft_scope:
      pathlib.Path(args.draft_scope).write_text(json.dumps(draft_scope(probes, endpoints, noise), indent=3), encoding="utf-8")

   real_endpoints = [record for record in endpoints.values() if not record.get("noise")]
   print("pages {0}, render {1}, timing cleared {2}".format(len(probes), state["render"], state["timing_cleared"]))

   for probe in probes:
      forms = probe.get("forms", [])
      writes = sum(1 for form in forms if form.get("method") != "GET")
      pagination = probe.get("pagination", {})
      print("page {0} | {1} | calls {2} | forms {3} ({4} non-GET) | pagination links {5}, load-more {6}".format(
         probe["url"], page_render(probe, endpoints), len([call for call in probe.get("calls", []) if not endpoints.get(call["pattern"], {}).get("noise")]), len(forms), writes, len(pagination.get("links", [])), pagination.get("loadMoreControls", 0)))

   print("endpoints {0}:".format(len(real_endpoints)))
   for record in sorted(real_endpoints, key=lambda item: item["pattern"]):
      print("  {0} {1} | pages {2} | headers {3} | shape fields {4}".format(record["via"], record["pattern"], record["pages"], len(record["header_names"]), len(record["shape"])))

   print("noise {0}: {1}".format(len(noise), ", ".join(sorted(noise))))
   kinds = {}
   for entry in frontier:
      kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1

   print("frontier {0} ({1})".format(len(frontier), ", ".join("{0} {1}".format(count, kind) for kind, count in sorted(kinds.items()))))
   for entry in frontier[:12]:
      print("  {0} {1} x{2} e.g. {3}".format(entry["kind"], entry["pattern"], entry["count"], entry["sample"]))


if __name__ == "__main__":
   main()
