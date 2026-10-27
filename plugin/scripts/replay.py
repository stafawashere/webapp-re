#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Replay a request exported by assets/reverse-export.js outside the browser.

Prints status, size and the top-level response shape, never header or parameter values.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def load_export(path):
   raw = open(path, "r", encoding="utf-8").read()
   start = raw.find("{")
   end = raw.rfind("}")

   if start < 0 or end < 0:
      sys.exit("replay: no JSON object in {0}".format(path))

   return json.loads(raw[start:end + 1])


def apply_overrides(export, assignments):
   url = urllib.parse.urlsplit(export["url"])
   query = urllib.parse.parse_qsl(url.query, keep_blank_values=True)
   body = export.get("body")

   try:
      fields = json.loads(body) if body else None
   except ValueError:
      fields = None

   for assignment in assignments:
      name, _, value = assignment.partition("=")

      try:
         parsed_value = json.loads(value)
      except ValueError:
         parsed_value = value

      body_has_field = isinstance(fields, dict)
      query_has_name = any(pair[0] == name for pair in query)

      if body_has_field and not query_has_name:
         fields[name] = parsed_value
      else:
         query = [pair for pair in query if pair[0] != name] + [(name, value)]

   export["url"] = urllib.parse.urlunsplit(url._replace(query=urllib.parse.urlencode(query)))

   if isinstance(fields, dict):
      export["body"] = json.dumps(fields)

   return export


def top_shape(document):
   if isinstance(document, list):
      return "array {0}".format(len(document))

   if not isinstance(document, dict):
      return type(document).__name__

   parts = []

   for name, value in list(document.items())[:20]:
      is_list = isinstance(value, list)
      parts.append("{0}[{1}]".format(name, len(value)) if is_list else name)

   return ", ".join(parts)


def first_item_preview(document, fields):
   lists = [value for value in document.values() if isinstance(value, list) and value] if isinstance(document, dict) else [document]
   items = max(lists, key=len) if lists else []
   first = items[0] if items else None

   if not isinstance(first, dict):
      return None

   return {name: first.get(name) for name in fields if name in first}


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("export", help="file written by reverse-export.js through evaluate_script filePath")
   parser.add_argument("--set", action="append", default=[], help="name=value for a query parameter or JSON body field")
   parser.add_argument("--show", default="", help="comma separated fields of the first list item to print")
   parser.add_argument("--save", help="write the response body here")
   parser.add_argument("--consume", action="store_true", help="delete the export file afterwards, it holds live values")
   args = parser.parse_args()

   export = apply_overrides(load_export(args.export), args.set)
   headers = dict(export.get("headers") or {})
   headers.setdefault("origin", export.get("origin", ""))
   data = export["body"].encode("utf-8") if export.get("body") else None
   request = urllib.request.Request(export["url"], data=data, method=export["method"], headers=headers)

   try:
      response = urllib.request.urlopen(request, timeout=30)
      status = response.status
      text = response.read().decode("utf-8", "replace")
   except urllib.error.HTTPError as error:
      status = error.code
      text = error.read().decode("utf-8", "replace")
   finally:
      if args.consume:
         os.remove(args.export)

   if args.save:
      open(args.save, "w", encoding="utf-8").write(text)

   try:
      document = json.loads(text)
   except ValueError:
      document = None

   path = urllib.parse.urlsplit(export["url"]).path
   print("{0} {1} -> {2}, {3} bytes".format(export["method"], path, status, len(text)))
   print("headers sent: {0}".format(", ".join(sorted(headers)) or "none"))

   if document is None:
      print("body: text {0}".format(re.sub(r"\s+", " ", text[:120])))
      return

   print("shape: {0}".format(top_shape(document)))
   show = [name for name in args.show.split(",") if name]

   if show:
      print("first: {0}".format(json.dumps(first_item_preview(document, show))))


if __name__ == "__main__":
   main()
