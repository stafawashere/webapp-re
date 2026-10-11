"""Live verification: run each command through the CLI against citymapper.com, validate stdout
against its output schema, check transit invariants, and record readiness.

One CLI process per run; the program's own pacer keeps one request in flight with a 3 s or more gap.
Writes run only as --dry-run here. A 429 or a challenge stops the whole check.

   uv run python scripts/live_check.py [--only name,name] [--root /path/to/throwaway/site-root]

Readiness, the verify log and the request count all follow CITYMAPPER_ROOT (or --root), the same
root the CLI uses.
"""
import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from citymapper_client.config import site_paths
from mini_schema import validate

PROGRAM_DIR = Path(__file__).resolve().parents[1]
SCHEMAS = json.loads((PROGRAM_DIR / "src/citymapper_client/schemas.json").read_text())["commands"]
ROOT_VARIABLE = "CITYMAPPER_ROOT"
RUN_ID_VARIABLE = "CITYMAPPER_RUN_ID"
STOP_CLASSES = {"RateLimited", "ChallengeRequired"}
SESSION_BLOCK = "needs session: not yet verified live"
SESSION_EXPIRED_EXIT = 10


def first_google_id(outputs):
   for place in outputs["search-places"]["results"]:
      if str(place.get("id", "")).startswith("google:"):
         return place["id"]

   return outputs["search-places"]["results"][-1]["id"]


def nyc_signature(outputs):
   return outputs["plan-journey-nyc"]["journeys"][0]["signature"]


def london_bus_stop(outputs):
   return outputs["find-nearby-london-bus"]["elements"][0]["id"]


def times_in_order(output):
   problems = []

   for journey in output["journeys"]:
      leaves = journey.get("departure_time")
      arrives = journey.get("arrival_time")
      both_known = leaves and arrives
      if both_known and leaves > arrives:
         problems.append("journey {0} arrives before it leaves".format(journey["index"]))

      if not journey["legs"]:
         problems.append("journey {0} has no legs".format(journey["index"]))

      if journey["duration_seconds"] <= 0:
         problems.append("journey {0} has duration {1}".format(journey["index"], journey["duration_seconds"]))

   return problems


def departures_sane(output):
   problems = []
   rows = output["departures"]
   seconds = [item["seconds_away"] for item in rows if item["seconds_away"] is not None]
   live_seconds = [item["seconds_away"] for item in rows if item["is_live"] and item["seconds_away"] is not None]
   timetabled_seconds = [item["seconds_away"] for item in rows if not item["is_live"] and item["seconds_away"] is not None]
   live_flags = [item["is_live"] for item in rows]
   rows_without_any_time = [item for item in rows if item["seconds_away"] is None and not item["time"] and not item["scheduled_time"] and not item["advisory"]]

   if any(value < -120 for value in seconds):
      problems.append("a live departure is more than 2 minutes in the past")

   if live_seconds != sorted(live_seconds):
      problems.append("live departures are not in time order")

   if timetabled_seconds != sorted(timetabled_seconds):
      problems.append("timetabled departures are not in time order")

   if live_flags != sorted(live_flags, reverse=True):
      problems.append("a timetabled departure sorts before a live one")

   if rows_without_any_time:
      problems.append("{0} departures carry no time, seconds or advisory".format(len(rows_without_any_time)))

   if not output["departures"]:
      problems.append("no departures")

   return problems


def line_stops_belong(output):
   stop_ids = {stop["id"] for stop in output["stops"]}
   problems = []

   for pattern in output["patterns"]:
      foreign = [stop["id"] for stop in pattern["stops"] if stop["id"] not in stop_ids]
      if foreign:
         problems.append("pattern {0} lists {1} stops not on the line".format(pattern["id"], len(foreign)))

      if not pattern["stops"]:
         problems.append("pattern {0} has no stops".format(pattern["id"]))

   return problems


def non_empty(key):
   return lambda output: [] if output.get(key) else ["{0} is empty".format(key)]


def regions_complete(output):
   regions = output["regions"]
   problems = [] if len(regions) >= 100 else ["only {0} regions".format(len(regions))]
   has_new_york = any(region["region_id"] == "us-nyc" for region in regions)
   return problems + ([] if has_new_york else ["us-nyc missing"])


def bikes_counted(output):
   docks = [element for element in output["elements"] if element["kind"] == "cycledock"]
   counted = [dock for dock in docks if dock["bikes_available"] is not None]
   return [] if docks and counted else ["no docks with bike counts"]


def all_levels_valid(output):
   return [] if all(item["level"] >= 1 and "{" not in item["description"] for item in output["disruptions"]) else ["a disruption has level 0 or an unfilled placeholder"]


RUNS = [
   {"label": "list-cities", "command": "list-cities", "argv": ["--refresh"], "check": regions_complete},
   {"label": "get-city", "command": "get-city", "argv": ["--city", "london"], "check": lambda output: [] if output["timezone"] == "Europe/London" and output["nearby_modes"] else ["wrong timezone or no modes"]},
   {"label": "list-brands", "command": "list-brands", "argv": ["--city", "nyc"], "check": non_empty("brands")},
   {"label": "search-places", "command": "search-places", "argv": ["--city", "nyc", "--query", "Times Square"], "check": non_empty("results")},
   {"label": "resolve-place", "command": "resolve-place", "argv": lambda outputs: ["--city", "nyc", "--id", first_google_id(outputs)], "check": lambda output: [] if output["place"]["coords"] else ["no coords"]},
   {"label": "reverse-geocode", "command": "reverse-geocode", "argv": ["--lat", "51.5074", "--lng", "-0.1278"], "check": lambda output: [] if output["address"] else ["no address"]},
   {"label": "plan-journey-nyc", "command": "plan-journey", "argv": ["--city", "nyc", "--from", "Grand Central", "--to", "40.706086,-73.996864", "--depart-at", "18:30", "--limit", "4"], "check": times_in_order},
   {"label": "plan-journey-london", "command": "plan-journey", "argv": ["--city", "london", "--from", "51.503324,-0.119543", "--to", "King's Cross St Pancras", "--arrive-by", "19:00", "--limit", "4"], "check": times_in_order},
   {"label": "plan-walk", "command": "plan-walk", "argv": ["--city", "paris", "--from", "48.85837,2.347", "--to", "48.88093,2.35533"], "check": times_in_order},
   {"label": "plan-cycle", "command": "plan-cycle", "argv": ["--city", "berlin", "--from", "52.5219,13.4132", "--to", "52.5163,13.3777"], "check": times_in_order},
   {"label": "plan-cab", "command": "plan-cab", "argv": ["--city", "sfbayarea", "--from", "37.7749,-122.4194", "--to", "37.8080,-122.4177"], "check": non_empty("routes")},
   {"label": "get-journey-times", "command": "get-journey-times", "argv": lambda outputs: ["--city", "nyc", "--signatures", nyc_signature(outputs)], "check": non_empty("times")},
   {"label": "get-journey", "command": "get-journey", "argv": lambda outputs: ["--city", "nyc", "--signature", nyc_signature(outputs)], "check": lambda output: [] if output["journey"] and output["journey"]["legs"] else ["no journey"]},
   {"label": "get-travel-time", "command": "get-travel-time", "argv": ["--city", "tokyo", "--from", "35.6812,139.7671", "--to", "35.6580,139.7016"], "check": lambda output: [] if output["seconds"] and output["seconds"] > 0 else ["no travel time"]},
   {"label": "find-nearby", "command": "find-nearby", "argv": ["--city", "nyc", "--near", "40.75773,-73.985708", "--mode", "bike", "--limit", "10"], "check": bikes_counted},
   {"label": "find-nearby-london-bus", "command": "find-nearby", "argv": ["--city", "london", "--near", "51.503324,-0.119543", "--mode", "bus", "--limit", "5"], "check": non_empty("elements")},
   {"label": "get-stop", "command": "get-stop", "argv": ["--city", "paris", "--stop", "chatelet"], "check": lambda output: [] if output["departure_api"] and output["routes"] else ["no departure api or routes"]},
   {"label": "get-departures-metro", "command": "get-departures", "argv": ["--city", "nyc", "--stop", "times-sq-42-st", "--limit", "15"], "check": departures_sane},
   {"label": "get-departures-bus", "command": "get-departures", "argv": lambda outputs: ["--city", "london", "--stop", london_bus_stop(outputs)], "check": departures_sane},
   {"label": "get-departures-rail", "command": "get-departures", "argv": ["--city", "nyc", "--stop", "grand-central", "--limit", "10"], "check": departures_sane},
   {"label": "get-stop-schedule", "command": "get-stop-schedule", "argv": ["--city", "nyc", "--stop", "7-avw-44-st"], "check": lambda output: [] if output["raw"].get("services") else ["no services"]},
   {"label": "get-line-status", "command": "get-line-status", "argv": ["--city", "london"], "check": non_empty("groups")},
   {"label": "get-disruptions", "command": "get-disruptions", "argv": ["--city", "nyc"], "check": all_levels_valid},
   {"label": "get-service-message", "command": "get-service-message", "argv": ["--city", "nyc"], "check": lambda output: []},
   {"label": "find-line", "command": "find-line", "argv": ["--city", "london", "--query", "73"], "check": non_empty("lines")},
   {"label": "get-line", "command": "get-line", "argv": ["--city", "nyc", "--line", "subway-6"], "check": line_stops_belong},
   {"label": "get-lines", "command": "get-lines", "argv": ["--city", "nyc", "--lines", "1,2,A"], "check": lambda output: [] if len(output["lines"]) == 3 else ["expected 3 lines"]},
   {"label": "get-vehicles", "command": "get-vehicles", "argv": ["--city", "london", "--line", "Bakerloo"], "check": lambda output: []},
   {"label": "get-route-paths", "command": "get-route-paths", "argv": ["--city", "nyc", "--lines", "6"], "check": lambda output: [] if output["paths"] and output["paths"][0]["patterns"] else ["no paths"]},
   {"label": "get-map-around", "command": "get-map-around", "argv": ["--city", "nyc", "--near", "40.75773,-73.985708", "--size", "small"], "check": non_empty("elements")},
   {"label": "list-news", "command": "list-news", "argv": ["--limit", "5"], "check": non_empty("posts")},
   {"label": "get-legal", "command": "get-legal", "argv": ["--document", "terms"], "check": lambda output: [] if len(output["text"]) > 1000 else ["short text"]},
   {"label": "whoami", "command": "whoami", "argv": [], "check": lambda output: [] if output["signed_in"] is False else ["unexpected session"]},
]

PASS_BLOCK = "blocked: needs a Citymapper Pass session from the app (Session-Id source unknown)"

EXPECTED_BLOCKS = [
   {"command": "plan-vehicle-hire", "argv": ["--city", "london", "--from", "51.503324,-0.119543", "--to", "51.531683,-0.124518"], "exit": 17, "status": "blocked: retired by Citymapper (/api/7/vehiclehire answers 404 'This API is no longer supported')"},
   {"command": "get-shared-eta", "argv": ["--city", "nyc", "--signature", "x"], "exit": 17, "status": "blocked: not served on the web (/api/1/eta answers 404 Page Not Found)"},
   {"command": "get-weather", "argv": ["--city", "nyc"], "exit": 17, "status": "blocked: retired by Citymapper (/api/1/weather answers 404)"},
   {"command": "get-transit-score", "argv": ["--city", "nyc", "--near", "40.75773,-73.985708"], "exit": 17, "status": "blocked: retired by Citymapper (/api/1/transitscore answers 404)"},
   {"command": "list-saved-places", "argv": [], "exit": 10, "status": SESSION_BLOCK},
   {"command": "list-favourites", "argv": [], "exit": 10, "status": SESSION_BLOCK},
   {"command": "pass-account", "argv": [], "exit": 10, "status": PASS_BLOCK},
   {"command": "pass-session-time", "argv": [], "exit": 10, "status": PASS_BLOCK},
]

NOT_RUNNABLE = {
   "open-trip-link": "blocked: needs a citymapper.com/trip/<slug> link; one comes from share-journey after your approval (an unknown slug answers 404)",
   "open-go-link": "blocked: needs a citymapper.com/go/<slug> link; one comes from create-go-link after your approval (an unknown slug answers 404)",
}


def run_cli(argv):
   started = time.monotonic()
   result = subprocess.run(["uv", "run", "--project", str(PROGRAM_DIR), "citymapper", *argv], capture_output=True, text=True, cwd=PROGRAM_DIR)
   return result, int((time.monotonic() - started) * 1000)


def resolve_site_paths(root_option):
   if root_option is not None:
      os.environ[ROOT_VARIABLE] = root_option

   configured_root = os.environ.get(ROOT_VARIABLE)

   if configured_root is None:
      return site_paths()

   if not configured_root.strip():
      raise SystemExit("{0} is set but empty; unset it or point it at a site root.".format(ROOT_VARIABLE))

   os.environ[ROOT_VARIABLE] = str(Path(configured_root).expanduser().resolve())
   return site_paths()


def count_requests_of_run(paths, run_id):
   log_path = paths.logs_dir / "requests-{0}.jsonl".format(datetime.now().strftime("%Y-%m-%d"))
   lines = log_path.read_text().splitlines() if log_path.exists() else []
   count = 0

   for line in lines:
      try:
         entry = json.loads(line)
      except ValueError:
         continue

      is_this_run = isinstance(entry, dict) and entry.get("run") == run_id
      count += 1 if is_this_run else 0

   return count


def run_cli_counted(paths, argv, run_id):
   os.environ[RUN_ID_VARIABLE] = run_id

   try:
      result, elapsed_ms = run_cli(argv)
   finally:
      os.environ.pop(RUN_ID_VARIABLE, None)

   return result, elapsed_ms, count_requests_of_run(paths, run_id)


def first_problem(record):
   problems = record.get("schema_problems", []) + record.get("invariant_problems", [])

   if problems:
      return problems[0]

   return "{0} (exit {1})".format(record.get("class") or "unknown error", record.get("exit"))


def record_run_readiness(readiness, labels_by_command, passed_labels, failures, stamp, log_name):
   for command, labels in labels_by_command.items():
      if command in failures:
         readiness[command] = {"status": "failing live: " + failures[command], "checked_at": stamp, "log": log_name}
         continue

      every_label_passed = labels <= passed_labels

      if every_label_passed:
         readiness[command] = {"status": "verified live", "verified_at": stamp, "log": log_name, "label": ",".join(sorted(labels))}


def is_selected(run, wanted):
   runs_everything = not wanted
   is_named = run["label"] in wanted or run["command"] in wanted
   return runs_everything or is_named


def main(argv=None):
   parser = argparse.ArgumentParser()
   parser.add_argument("--only", default="")
   parser.add_argument("--root", help="site root for readiness, logs, cache and .env (sets CITYMAPPER_ROOT for the CLI)")
   args = parser.parse_args(argv)
   paths = resolve_site_paths(args.root)
   readiness_file = paths.readiness_file
   wanted = {item for item in args.only.split(",") if item}
   stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
   log_path = paths.logs_dir / "verify-{0}.json".format(stamp)
   log_name = str(log_path.relative_to(paths.site_root))
   log_path.parent.mkdir(parents=True, exist_ok=True)
   readiness = json.loads(readiness_file.read_text()) if readiness_file.exists() else {}
   selected_runs = [run for run in RUNS if is_selected(run, wanted)]
   labels_by_command = {}

   for run in selected_runs:
      labels_by_command.setdefault(run["command"], set()).add(run["label"])

   passed_labels = set()
   failures = {}
   outputs = {}
   passed = failed = 0
   stopped = None
   run_ids = ("lc{0}-{1}".format(stamp.replace("-", ""), number) for number in itertools.count(1))

   try:
      with log_path.open("a") as log:
         for run in selected_runs:
            try:
               argv = run["argv"](outputs) if callable(run["argv"]) else run["argv"]
            except (KeyError, IndexError, TypeError):
               record = {"label": run["label"], "command": run["command"], "result": "skipped", "reason": "input from an earlier run is missing"}
               log.write(json.dumps(record) + "\n")
               print(json.dumps(record), flush=True)
               continue

            result, elapsed_ms, requests = run_cli_counted(paths, [run["command"], *argv], next(run_ids))
            record = {"label": run["label"], "command": run["command"], "exit": result.returncode, "ms": elapsed_ms, "requests": requests}

            if result.returncode != 0:
               error = json.loads(result.stderr.strip().splitlines()[-1]) if result.stderr.strip().startswith("{") else {"class": "unknown", "message": result.stderr[-300:]}
               record.update({"result": "fail", "class": error.get("class"), "message": error.get("message", "")[:200]})
               failed += 1
               log.write(json.dumps(record) + "\n")
               print(json.dumps(record), flush=True)

               if error.get("class") in STOP_CLASSES:
                  stopped = error.get("class")
                  break

               failures.setdefault(run["command"], first_problem(record))
               continue

            output = json.loads(result.stdout)
            outputs[run["label"]] = output
            schema_problems = validate(output, SCHEMAS[run["command"]]["output_schema"])
            invariant_problems = run["check"](output)
            items = sum(len(value) for value in output.values() if isinstance(value, list))
            ok = not schema_problems and not invariant_problems
            record.update({"result": "pass" if ok else "fail", "items": items, "schema_problems": schema_problems[:5], "invariant_problems": invariant_problems[:5]})
            log.write(json.dumps(record) + "\n")
            print(json.dumps(record), flush=True)

            if ok:
               passed += 1
               passed_labels.add(run["label"])
            else:
               failed += 1
               failures.setdefault(run["command"], first_problem(record))

         for block in [] if stopped else EXPECTED_BLOCKS:
            selected = not wanted or block["command"] in wanted
            if not selected:
               continue

            result, elapsed_ms, requests = run_cli_counted(paths, [block["command"], *block["argv"]], next(run_ids))
            confirmed = result.returncode == block["exit"]
            waits_for_session = block["exit"] == SESSION_EXPIRED_EXIT
            exited_cleanly = result.returncode == 0
            answered_with_session = waits_for_session and exited_cleanly
            record = {"label": block["command"], "command": block["command"], "exit": result.returncode, "ms": elapsed_ms, "requests": requests, "result": "blocked as expected" if confirmed else "unexpected exit"}

            if answered_with_session:
               schema_problems = validate(json.loads(result.stdout), SCHEMAS[block["command"]]["output_schema"])
               record.update({"result": "fail" if schema_problems else "pass", "schema_problems": schema_problems[:5]})

            log.write(json.dumps(record) + "\n")
            print(json.dumps(record), flush=True)

            if confirmed:
               readiness[block["command"]] = {"status": block["status"], "checked_at": stamp, "log": log_name}
            elif answered_with_session:
               session_read_passed = record["result"] == "pass"

               if session_read_passed:
                  passed += 1
                  readiness[block["command"]] = {"status": "verified live", "verified_at": stamp, "log": log_name, "label": block["command"]}
               else:
                  failed += 1
                  readiness[block["command"]] = {"status": "failing live: " + first_problem(record), "checked_at": stamp, "log": log_name}
   finally:
      record_run_readiness(readiness, labels_by_command, passed_labels, failures, stamp, log_name)

      for command, status in NOT_RUNNABLE.items():
         readiness[command] = {"status": status}

      readiness_file.parent.mkdir(parents=True, exist_ok=True)
      readiness_file.write_text(json.dumps(readiness, indent=1) + "\n")

   total_requests = sum(json.loads(line).get("requests", 0) for line in log_path.read_text().splitlines())
   summary = "live check: {0} of {1} runs passed; {2} requests; log {3}".format(passed, passed + failed, total_requests, log_name)

   if stopped:
      summary += "; stopped on " + stopped

   print(summary)
   sys.exit(0 if failed == 0 and not stopped else 1)


if __name__ == "__main__":
   main()
