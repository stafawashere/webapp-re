import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

from .config import site_paths
from .context import Context
from .errors import CitymapperError, ContractBroken, LocalFileError, UsageError
from .pacing import Pacer
from .registry import build_registry, load_readiness, readiness_of

TABLE_KEY = {
   "plan-journey": "journeys",
   "plan-walk": "journeys",
   "plan-cycle": "journeys",
   "plan-vehicle-hire": "journeys",
   "plan-cab": "routes",
   "get-line": "stops",
   "get-stop": "routes",
}
JOURNEY_COLUMNS = ["index", "duration_seconds", "departure_time", "arrival_time", "legs", "price", "signature"]
RUN_ID_VARIABLE = "CITYMAPPER_RUN_ID"
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,32}")
JSON_ARRAY_OPTIONS = {"signatures"}
ERROR_MESSAGE_LIMIT = 300


class JsonArgumentParser(argparse.ArgumentParser):
   def error(self, message):
      usage_error = UsageError(message, {"command": self.prog})
      sys.stderr.write(json.dumps(usage_error.as_dict(), ensure_ascii=False) + "\n")
      raise SystemExit(usage_error.exit_code)


def current_run_id():
   given = os.environ.get(RUN_ID_VARIABLE, "").strip()

   if RUN_ID_PATTERN.fullmatch(given):
      return given

   return uuid.uuid4().hex[:8]


def option_name(property_name):
   return "--" + property_name.replace("_", "-")


def comma_separated(text):
   return [item.strip() for item in text.split(",") if item.strip()]


def json_aware_list(text):
   stripped = text.strip()

   if stripped.startswith("["):
      try:
         items = json.loads(stripped)
      except json.JSONDecodeError:
         raise argparse.ArgumentTypeError("a value starting with [ must be a JSON array of strings")

      holds_only_text = isinstance(items, list) and all(isinstance(item, str) for item in items)

      if not holds_only_text:
         raise argparse.ArgumentTypeError("a value starting with [ must be a JSON array of strings")

      return [item for item in items if item.strip()]

   if stripped.startswith("{"):
      try:
         json.loads(stripped)
      except json.JSONDecodeError:
         raise argparse.ArgumentTypeError("a value starting with { must be one complete JSON object")

      return [stripped]

   return comma_separated(text)


def integer_at_least(minimum):
   def parse(text):
      try:
         number = int(text)
      except ValueError:
         raise argparse.ArgumentTypeError("invalid int value: {0!r}".format(text))

      is_below_minimum = minimum is not None and number < minimum

      if is_below_minimum:
         raise argparse.ArgumentTypeError("must be at least {0}, got {1}".format(minimum, number))

      return number

   return parse


def add_property(parser, property_name, schema, required):
   kind = schema.get("type")
   description = schema.get("description", "")
   options = {"dest": property_name, "help": description}

   if kind == "boolean":
      parser.add_argument(option_name(property_name), action=argparse.BooleanOptionalAction, default=None, **options)
      return

   if kind == "integer":
      options["type"] = integer_at_least(schema.get("minimum"))
   elif kind == "number":
      options["type"] = float
   elif kind == "array":
      if property_name in JSON_ARRAY_OPTIONS:
         options["type"] = json_aware_list
         options["action"] = "extend"
         options["help"] = (description + " (one journey signature or a JSON array of them; repeatable)").strip()
      else:
         options["type"] = comma_separated
         options["help"] = (description + " (comma separated)").strip()

   if schema.get("enum"):
      options["choices"] = schema["enum"]

   parser.add_argument(option_name(property_name), required=required, **options)


def build_parser(registry):
   parser = JsonArgumentParser(prog="citymapper", description="Citymapper web API client. Every command prints JSON.")
   parser.add_argument("--env-file", help="path to the .env holding your Citymapper cookies (default: the site root .env)")
   parser.add_argument("--format", choices=["json", "table"], default="json")
   subparsers = parser.add_subparsers(dest="command")
   subparsers.add_parser("help", help="list every command, its kind and readiness, and the session status")

   for name, command in registry.items():
      if name == "help":
         continue

      subparser = subparsers.add_parser(name, help=command.purpose, description=command.purpose)
      schema = command.input_schema or {}
      required = set(schema.get("required") or [])

      for property_name, property_schema in (schema.get("properties") or {}).items():
         add_property(subparser, property_name, property_schema, property_name in required)

   return parser


def help_output(registry, paths, context):
   readiness = load_readiness(paths)
   has_session = context.session.signed_in
   commands = []

   for name, command in registry.items():
      commands.append({"name": name, "kind": command.kind, "tier": command.tier, "readiness": readiness_of(name, readiness, command, has_session), "purpose": command.purpose, "inputs": sorted((command.input_schema.get("properties") or {}).keys())})

   pacer = Pacer(paths.pacer_state)
   return {"commands": commands, "session": {**context.session.describe(), "env_file": str(context.env_file)}, "pacer": pacer.status()}


def leg_summary(leg):
   route_names = [route.get("name") for route in leg.get("routes") or [] if route.get("name")]
   mode = str(leg.get("mode", ""))

   if route_names:
      return "{0} {1}".format(mode, "/".join(route_names))

   return mode


def journey_row(journey):
   row = {column: journey.get(column) for column in JOURNEY_COLUMNS}
   row["legs"] = " > ".join(leg_summary(leg) for leg in journey.get("legs") or [])
   return row


def first_list_of_records(output):
   for value in output.values():
      is_non_empty_list = isinstance(value, list) and bool(value)
      holds_records = is_non_empty_list and isinstance(value[0], dict)

      if holds_records:
         return value

   return None


def table_rows(output, command_name):
   if not isinstance(output, dict):
      return None

   table_key = TABLE_KEY.get(command_name)

   if table_key is None:
      return first_list_of_records(output)

   rows = output.get(table_key)
   has_rows = isinstance(rows, list) and bool(rows)

   if not has_rows:
      return None

   if table_key == "journeys":
      return [journey_row(journey) for journey in rows]

   return rows


def as_table(output, command_name=None):
   rows = table_rows(output, command_name)

   if rows is None:
      return json.dumps(output, indent=1, ensure_ascii=False)

   columns = [key for key, value in rows[0].items() if not isinstance(value, (dict, list))][:8]
   lines = [" | ".join(columns), " | ".join("---" for _ in columns)]

   for row in rows:
      lines.append(" | ".join(str(row.get(column, "")) for column in columns))

   return "\n".join(lines)


def run_command(command, context, values):
   # Writes resolve text places afresh so the dry run and the send can catch a place that moved.
   context.cache_text_places = command.kind == "read"
   output = command.function(context, values)
   is_remote_read = command.kind == "read" and command.live_policy != "local"
   first_sent_at = context.transport.first_sent_at
   should_stamp = is_remote_read and isinstance(output, dict) and first_sent_at is not None

   if should_stamp:
      output.setdefault("fetched_at", first_sent_at)

   return output


def redact(text, session):
   if session is None:
      return text

   for value in session.cookies.values():
      is_worth_hiding = bool(value) and len(value) >= 4

      if is_worth_hiding:
         text = text.replace(value, "[redacted]")

   return text


def build_context(arguments, paths, run_id):
   env_path = Path(arguments.env_file).expanduser() if arguments.env_file else paths.env_file

   try:
      return Context.build(env_file=arguments.env_file, paths=paths, run_id=run_id, command=arguments.command or "help")
   except (OSError, UnicodeDecodeError) as error:
      failing_file = getattr(error, "filename", None) or env_path
      raise UsageError("Cannot read {0}: {1}.".format(failing_file, type(error).__name__), {"file": str(failing_file)})


def main(argv=None):
   registry = build_registry()
   parser = build_parser(registry)
   arguments = parser.parse_args(argv)
   paths = site_paths()
   run_id = current_run_id()
   context = None

   try:
      context = build_context(arguments, paths, run_id)

      if arguments.command in (None, "help"):
         output = help_output(registry, paths, context)
      else:
         command = registry[arguments.command]

         if command.function is None:
            raise UsageError("Command {0} is planned but has no implementation.".format(command.name))

         values = {key: value for key, value in vars(arguments).items() if key not in ("command", "env_file", "format")}
         output = run_command(command, context, values)
   except CitymapperError as error:
      error.detail.setdefault("run", run_id)
      sys.stderr.write(json.dumps(error.as_dict(), ensure_ascii=False) + "\n")
      return error.exit_code
   except OSError as error:
      message = redact(str(error), context.session if context else None)[:ERROR_MESSAGE_LIMIT]
      detail = {"command": arguments.command or "help", "error": type(error).__name__, "message": message, "run": run_id}
      local_failure = LocalFileError("A local file could not be read or written. The request may already have been sent, so re-read before sending it again.", detail)
      sys.stderr.write(json.dumps(local_failure.as_dict(), ensure_ascii=False) + "\n")
      return local_failure.exit_code
   except (KeyError, TypeError, AttributeError, ValueError) as error:
      message = redact(str(error), context.session if context else None)[:ERROR_MESSAGE_LIMIT]
      detail = {"command": arguments.command or "help", "error": type(error).__name__, "message": message, "run": run_id}
      broken = ContractBroken("Citymapper's response or a cached file has an unexpected shape.", detail)
      sys.stderr.write(json.dumps(broken.as_dict(), ensure_ascii=False) + "\n")
      return broken.exit_code

   text = as_table(output, arguments.command) if arguments.format == "table" else json.dumps(output, ensure_ascii=False)
   sys.stdout.write(text + "\n")
   return 0


if __name__ == "__main__":
   sys.exit(main())
