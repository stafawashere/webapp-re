#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read a scope.json in slices instead of whole.

    uv run --script scope_query.py <scope.json>                      index: one line per item
    uv run --script scope_query.py <scope.json> --id <item-id>        one item in full
    uv run --script scope_query.py <scope.json> --section auth        one top-level section in full
    uv run --script scope_query.py <scope.json> --grep <regex>        ids of items whose JSON matches

The index is what plan and engineer read first; they open single items by id after that.
"""

import argparse
import json
import re
import sys

COLLECTIONS = ("pages", "capabilities", "endpoints", "entities", "pagination")
INDEX_FIELDS = {
   "pages": ("url_pattern",),
   "capabilities": ("name", "mutates", "exercised"),
   "endpoints": ("method", "url_pattern", "surface"),
   "entities": ("fields",),
   "pagination": ("kind",),
}


def summarize(value):
   if isinstance(value, list):
      return "{0} items".format(len(value)) if value and isinstance(value[0], (dict, list)) else ",".join(str(item) for item in value[:8])

   return str(value)


def print_index(scope):
   site = scope.get("site", {})
   print("site {0} | {1} | {2}".format(site.get("slug"), site.get("framework", ""), scope.get("generated", "")))

   for collection in COLLECTIONS:
      items = scope.get(collection, [])
      print("{0} ({1}):".format(collection, len(items)))

      for item in items:
         extras = " | ".join(summarize(item.get(field, "")) for field in INDEX_FIELDS[collection])
         print("  {0} | {1}".format(item.get("id"), extras))

   auth = scope.get("auth", {})
   print("auth: {0}, {1} cookie names, {2} header names".format(auth.get("mechanism"), len(auth.get("cookie_names", [])), len(auth.get("header_names", []))))
   print("caveats ({0}): {1}".format(len(scope.get("caveats", [])), "; ".join("{0}/{1}".format(caveat.get("kind"), caveat.get("severity")) for caveat in scope.get("caveats", []))))
   print("open_questions: {0}".format(len(scope.get("open_questions", []))))


def find_item(scope, identifier):
   for collection in COLLECTIONS:
      for item in scope.get(collection, []):
         if item.get("id") == identifier:
            return collection, item

   return None, None


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("scope")
   parser.add_argument("--id")
   parser.add_argument("--section")
   parser.add_argument("--grep")
   args = parser.parse_args()

   with open(args.scope, encoding="utf-8") as handle:
      scope = json.load(handle)

   if args.id:
      collection, item = find_item(scope, args.id)

      if item is None:
         sys.exit("no item with id {0}".format(args.id))

      print("{0}: {1}".format(collection, json.dumps(item, indent=1)))
      return

   if args.section:
      print(json.dumps(scope.get(args.section), indent=1))
      return

   if args.grep:
      pattern = re.compile(args.grep, re.IGNORECASE)

      for collection in COLLECTIONS:
         for item in scope.get(collection, []):
            if pattern.search(json.dumps(item)):
               print("{0} {1}".format(collection, item.get("id")))

      return

   print_index(scope)


if __name__ == "__main__":
   main()
