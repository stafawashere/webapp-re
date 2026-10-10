#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check plan/plan.json against scope/scope.json in a site directory.

    uv run --script check_plan.py <site-root>
"""

import json
import os
import re
import sys

KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def load(root, relative):
   with open(os.path.join(root, relative), encoding="utf-8") as handle:
      return json.load(handle)


def check(plan, scope):
   problems = []
   scope_endpoints = {endpoint.get("id") for endpoint in scope.get("endpoints", [])}
   commands = plan.get("commands", [])
   names = [command.get("name") for command in commands]

   if "help" not in names:
      problems.append("no help command")

   for name in sorted({name for name in names if names.count(name) > 1}):
      problems.append("duplicate command {0}".format(name))

   for command in commands:
      name = command.get("name", "<unnamed>")

      if not KEBAB.match(name or ""):
         problems.append("command {0} is not kebab case".format(name))

      for schema_key in ("input_schema", "output_schema"):
         if not isinstance(command.get(schema_key), dict):
            problems.append("command {0} has no {1}".format(name, schema_key))

      kind = command.get("kind")
      if kind not in ("read", "write"):
         problems.append("command {0} kind must be read or write".format(name))

      write_without_confirmation = kind == "write" and not command.get("confirmation")
      if write_without_confirmation:
         problems.append("write command {0} has no confirmation rule".format(name))

      for dependency in command.get("depends_on", []):
         endpoint = dependency.get("endpoint")
         if endpoint not in scope_endpoints:
            problems.append("command {0} depends on endpoint {1}, not in scope".format(name, endpoint))

   placements = [name for step in plan.get("build_order", []) for name in step.get("commands", [])]

   for name in names:
      count = placements.count(name)
      if count != 1:
         problems.append("command {0} appears {1} times in build_order".format(name, count))

   for name in set(placements) - set(names):
      problems.append("build_order names unknown command {0}".format(name))

   return problems


def main():
   if len(sys.argv) != 2:
      sys.exit("usage: check_plan.py <site-root>")

   root = sys.argv[1]
   plan = load(root, "plan/plan.json")
   scope = load(root, "scope/scope.json")
   problems = check(plan, scope)

   for problem in problems:
      print(problem)

   open_steps = sum(len(command.get("open_steps", [])) for command in plan.get("commands", []))
   budget = sum(step.get("budget", 0) for command in plan.get("commands", []) for step in command.get("open_steps", []))
   print("plan: {0} commands, {1} build steps, {2} open steps, budget {3} requests; {4} problems".format(len(plan.get("commands", [])), len(plan.get("build_order", [])), open_steps, budget, len(problems)))
   sys.exit(1 if problems else 0)


if __name__ == "__main__":
   main()
