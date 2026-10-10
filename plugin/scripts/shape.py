#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Summarise a JSON response as key names, types and counts. Never values.

    uv run --script ~/dev/webapp-re/plugin/scripts/shape.py --file body.json
    pbpaste | uv run --script ~/dev/webapp-re/plugin/scripts/shape.py

This is the redaction step between a live response and an endpoint file. Strings become
lengths, lists become counts, and a key that is present on some items and absent on others
shows up as a coverage fraction, which is what a typed model needs to know.
"""

import argparse
import json
import sys


def walk(node, path, table, depth, max_depth):
   if depth > max_depth:
      return

   if isinstance(node, list):
      for item in node:
         note(table, path + "[]", kind_of(item), length_of(item))
         walk(item, path + "[]", table, depth + 1, max_depth)

      return

   if not isinstance(node, dict):
      return

   for key, value in node.items():
      child = path + "." + key if path else key
      note(table, child, kind_of(value), length_of(value))
      walk(value, child, table, depth + 1, max_depth)


def kind_of(value):
   if value is None:
      return "null"
   if isinstance(value, bool):
      return "bool"
   if isinstance(value, list):
      return "array"
   if isinstance(value, dict):
      return "object"
   if isinstance(value, str):
      return "str"

   return "number"


def length_of(value):
   if isinstance(value, (str, list, dict)):
      return len(value)

   return None


def note(table, path, kind, length):
   entry = table.setdefault(path, {"kinds": set(), "count": 0, "min": None, "max": None})
   entry["kinds"].add(kind)
   entry["count"] += 1

   if length is None:
      return

   entry["min"] = length if entry["min"] is None else min(entry["min"], length)
   entry["max"] = length if entry["max"] is None else max(entry["max"], length)


def descend(document, root):
   for step in root.split("."):
      document = document[int(step)] if step.isdigit() else document[step]

   return document


def render(document, max_depth=8):
   """One line per path: types, length span, and coverage when a key is not universal."""

   table = {}
   walk(document, "", table, 0, max_depth)

   parent_counts = {path: entry["count"] for path, entry in table.items()}
   parent_counts[""] = 1
   lines = []

   for path in sorted(table):
      entry = table[path]
      parent = path.rsplit(".", 1)[0] if "." in path else ""
      total = parent_counts.get(parent, entry["count"])
      span = ""

      if entry["min"] is not None:
         span = " len {0}".format(entry["min"] if entry["min"] == entry["max"] else "{0}-{1}".format(entry["min"], entry["max"]))

      is_element = path.endswith("[]")
      coverage = "" if is_element or entry["count"] == total else " present {0}/{1}".format(entry["count"], total)

      lines.append("{0} | {1}{2}{3}".format(path, "/".join(sorted(entry["kinds"])), span, coverage))

   return lines


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("--file")
   parser.add_argument("--root", default="", help="dotted path to summarise instead of the whole body")
   parser.add_argument("--max-depth", type=int, default=8)
   args = parser.parse_args()

   raw = open(args.file, "r", encoding="utf-8").read() if args.file else sys.stdin.read()
   document = json.loads(raw)

   if args.root:
      document = descend(document, args.root)

   for line in render(document, args.max_depth):
      print(line)


if __name__ == "__main__":
   main()
