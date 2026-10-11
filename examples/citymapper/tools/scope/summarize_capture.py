#!/usr/bin/env python3
"""Print a compact summary of CDP capture files: request line, query, header names, body, and the
response shape (key paths with types and coverage, never long values).

   python3 tools/scope/summarize_capture.py var/captures/<file>.jsonl [--match /api/] [--depth 4] [--values]
"""

import argparse
import json
from urllib.parse import parse_qsl, urlsplit

NOISY_HEADERS = {"user-agent", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "accept-language", "accept-encoding", "priority", "sec-gpc", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "upgrade-insecure-requests"}


def shape(node, path, table, depth, max_depth):
   kind = "null" if node is None else type(node).__name__
   entry = table.setdefault(path or "$", {"kinds": set(), "count": 0, "example": None})
   entry["kinds"].add(kind)
   entry["count"] += 1

   is_short_scalar = isinstance(node, (int, float, bool)) or (isinstance(node, str) and len(node) <= 40)
   if is_short_scalar and entry["example"] is None:
      entry["example"] = node

   if depth >= max_depth:
      return

   if isinstance(node, list):
      for item in node[:30]:
         shape(item, path + "[]", table, depth + 1, max_depth)
   elif isinstance(node, dict):
      is_keyed_by_id = len(node) > 12 and all(isinstance(value, dict) for value in node.values())
      if is_keyed_by_id:
         for value in list(node.values())[:30]:
            shape(value, (path + "." if path else "") + "{id}", table, depth + 1, max_depth)

         return

      for key, value in node.items():
         shape(value, (path + "." if path else "") + key, table, depth + 1, max_depth)


def describe(body, max_depth):
   try:
      parsed = json.loads(body)
   except (TypeError, ValueError):
      return ["   text len={0}".format(len(body or ""))]

   table = {}
   shape(parsed, "", table, 0, max_depth)
   lines = []
   for path, entry in table.items():
      example = "" if entry["example"] is None else "  e.g. " + json.dumps(entry["example"])[:60]
      lines.append("   {0}: {1} x{2}{3}".format(path, "/".join(sorted(entry["kinds"])), entry["count"], example))

   return lines


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("files", nargs="+")
   parser.add_argument("--match", default="")
   parser.add_argument("--depth", type=int, default=4)
   parser.add_argument("--values", action="store_true", help="print request bodies in full")
   args = parser.parse_args()

   for file_name in args.files:
      for line in open(file_name, encoding="utf-8"):
         record = json.loads(line)
         url = record.get("url", "")
         if args.match not in url or "googleapis" in url:
            continue

         parts = urlsplit(url)
         print("=== {0} {1} {2}{3}".format(record.get("method"), record.get("status"), parts.netloc, parts.path))
         query = parse_qsl(parts.query, keep_blank_values=True)
         if query:
            print("   query: " + "; ".join("{0}={1}".format(key, value[:80]) for key, value in query))

         wire = record.get("wire_headers") or record.get("request_headers") or {}
         names = sorted(name for name in wire if name.lower() not in NOISY_HEADERS and not name.startswith(":"))
         print("   headers: " + ", ".join(names))
         body = record.get("post_data")
         if body:
            print("   body: " + (body if args.values else body[:600]))

         response_headers = record.get("response_headers") or {}
         interesting = [name for name in response_headers if any(word in name.lower() for word in ("rate", "retry", "cache", "set-cookie", "x-"))]
         if interesting:
            print("   response headers: " + ", ".join(sorted(interesting)))

         for described in describe(record.get("response_body"), args.depth):
            print(described)


if __name__ == "__main__":
   main()
