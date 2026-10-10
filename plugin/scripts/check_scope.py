#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check a scope.json against the scope schema's required structure and cross-references.

    uv run --script check_scope.py <site-root>/scope/scope.json

Exits 1 with one line per problem. Stdlib only, so it checks required keys, types of the
top-level collections, id uniqueness, references between collections, and secret-looking values.
"""

import json
import re
import sys

REQUIRED_TOP = ("site", "generated", "summary", "pages", "capabilities", "endpoints", "entities", "auth", "pagination", "caveats", "open_questions")
REQUIRED_ITEM_KEYS = {
   "pages": ("id", "url_pattern", "purpose"),
   "capabilities": ("id", "name", "user_action", "mutates", "exercised", "endpoints"),
   "endpoints": ("id", "method", "url_pattern", "surface", "observed"),
   "entities": ("id", "fields"),
   "pagination": ("id", "kind"),
   "caveats": ("kind", "detail", "severity"),
}
SECRET_VALUE = re.compile(r"(?i)(bearer\s+[A-Za-z0-9._\-]{20,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.|(session|sid|csrf|token)[^\"]{0,12}[=:]\s*[A-Za-z0-9%._\-]{16,})")


def check(scope):
   problems = []

   for key in REQUIRED_TOP:
      if key not in scope:
         problems.append("missing top-level key: {0}".format(key))

   for collection, keys in REQUIRED_ITEM_KEYS.items():
      items = scope.get(collection, [])

      if not isinstance(items, list):
         problems.append("{0} must be a list".format(collection))
         continue

      seen_ids = set()
      for position, item in enumerate(items):
         for key in keys:
            if key not in item:
               problems.append("{0}[{1}] missing {2}".format(collection, position, key))

         identifier = item.get("id")
         is_duplicate = identifier is not None and identifier in seen_ids
         if is_duplicate:
            problems.append("{0} has duplicate id {1}".format(collection, identifier))
         seen_ids.add(identifier)

   endpoint_ids = {endpoint.get("id") for endpoint in scope.get("endpoints", [])}
   capability_ids = {capability.get("id") for capability in scope.get("capabilities", [])}
   pagination_ids = {scheme.get("id") for scheme in scope.get("pagination", [])}
   reached = set()

   for capability in scope.get("capabilities", []):
      for endpoint_id in capability.get("endpoints", []):
         reached.add(endpoint_id)
         if endpoint_id not in endpoint_ids:
            problems.append("capability {0} names unknown endpoint {1}".format(capability.get("id"), endpoint_id))

   for page in scope.get("pages", []):
      for endpoint_id in page.get("endpoints", []):
         reached.add(endpoint_id)
         if endpoint_id not in endpoint_ids:
            problems.append("page {0} names unknown endpoint {1}".format(page.get("id"), endpoint_id))

      for capability_id in page.get("capabilities", []):
         if capability_id not in capability_ids:
            problems.append("page {0} names unknown capability {1}".format(page.get("id"), capability_id))

   for endpoint in scope.get("endpoints", []):
      is_orphan = endpoint.get("id") not in reached and not endpoint.get("noise")
      if is_orphan:
         problems.append("endpoint {0} is reached by no page or capability".format(endpoint.get("id")))

      scheme = endpoint.get("pagination")
      if scheme and scheme not in pagination_ids:
         problems.append("endpoint {0} names unknown pagination scheme {1}".format(endpoint.get("id"), scheme))

   for match in SECRET_VALUE.finditer(json.dumps(scope)):
      problems.append("secret-looking value: {0}...".format(match.group(0)[:12]))

   return problems


def main():
   if len(sys.argv) != 2:
      sys.exit("usage: check_scope.py <scope.json>")

   with open(sys.argv[1], encoding="utf-8") as handle:
      scope = json.load(handle)

   problems = check(scope)

   for problem in problems:
      print(problem)

   counts = ", ".join("{0} {1}".format(len(scope.get(key, [])), key) for key in ("pages", "capabilities", "endpoints", "entities", "caveats", "open_questions"))
   print("scope: {0}; {1} problems".format(counts, len(problems)))
   sys.exit(1 if problems else 0)


if __name__ == "__main__":
   main()
