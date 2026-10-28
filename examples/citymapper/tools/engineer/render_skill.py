"""Write plugin/skills/citymapper/SKILL.md from plan/plan.json and var/state/readiness.json.

If the skill already carries a menu section between its markers, the section is kept.
   python3 tools/engineer/render_skill.py [output-path]
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "plugin/skills/citymapper"
PLAN = json.loads((ROOT / "plan/plan.json").read_text())
READINESS_FILE = ROOT / "var/state/readiness.json"
PACING_SOURCE = ROOT / "program/src/citymapper_client/pacing.py"
MENU_SECTION = re.compile(r"<!-- webapp-re:menu -->.*?<!-- /webapp-re:menu -->", re.S)
FORBIDDEN_IN_SKILL = ("uv run --project", "/webapp-re engineer")
MENU_TEMPLATE = """<!-- webapp-re:menu -->
## Menu

For `menu`, run `uv run --script {pipeline}/menu/build_menu.py build --site citymapper`.
It prints one JSON line. Open its `open` URL with the built-in browser's `preview_start` (`url`),
then reply in one line with its `counts` and any `warnings`. If it prints `problems`, report them
and stop. For `menu inline`, or when the built-in browser tools are missing, follow
`{pipeline}/references/menu-delivery.md`. The menu sends nothing to the site;
its hints live in `{site}/menu/hints.json`.
<!-- /webapp-re:menu -->"""
HALT_SECONDS = re.compile(r"^HALT_SECONDS_AFTER_THROTTLE = (\d+)$", re.M)
APPROVAL_TIER = "approval"
SESSION_STATUS_PREFIXES = ("needs session", "blocked: needs your Citymapper session")
AWAITING_APPROVAL_PREFIX = "built, awaiting approval"
PASS_SESSION_PREFIX = "blocked: needs a Citymapper Pass session from the app"
SESSION_STATUS = "blocked: session"
SESSION_THEN_APPROVAL_STATUS = "blocked: session, then approval"
PASS_SESSION_STATUS = "blocked: Pass session"
AWAITING_APPROVAL_STATUS = "built, not verified: awaiting approval"
DESCRIPTION = (
   "Use Citymapper (citymapper.com) through a local program for any of its 115 regions; run help for the command list or menu for an interactive menu. "
   "Use when the user runs /citymapper, or asks how to get somewhere by transit, walking, cycling or cab in a city Citymapper covers, "
   "when the next train, bus, metro or ferry leaves a stop, which lines are disrupted or delayed, what is near a place (stations, stops, bike docks and how many bikes), "
   "a line's stops, branches, map path or live vehicles, journey times for a planned trip, place or address search, which cities Citymapper supports, "
   "Citymapper news or terms; and, with the user's own Citymapper session, their saved places, favourite stops and lines and Pass payment methods; "
   "also to save, rename or remove a place, favourite or unfavourite a stop or line, send a journey to their phone, update their profile, share a journey link, "
   "create a Meet Me Somewhere link, vote for a new city or sign out. Not Citymapper's official developer API."
)


def home_relative(path):
   try:
      return "~/" + str(path.relative_to(Path.home()))
   except ValueError:
      return str(path)


def default_menu_section():
   pipeline_dir = ROOT.parents[1] / "plugin"
   return MENU_TEMPLATE.format(pipeline=home_relative(pipeline_dir), site=home_relative(ROOT))


def readiness():
   try:
      return json.loads(READINESS_FILE.read_text())
   except (FileNotFoundError, ValueError):
      return {}


def halt_minutes():
   match = HALT_SECONDS.search(PACING_SOURCE.read_text())
   assert match, "HALT_SECONDS_AFTER_THROTTLE not found in " + str(PACING_SOURCE)
   return int(match.group(1)) // 60


def session_neutral(command, status):
   is_session_command = command["live_policy"] == "session"
   is_session_status = status.startswith(SESSION_STATUS_PREFIXES)
   waits_for_session = is_session_command and is_session_status

   if not waits_for_session:
      return status

   detail = status

   for prefix in SESSION_STATUS_PREFIXES:
      if detail.startswith(prefix):
         detail = detail[len(prefix):]
         break

   waits_for_approval = detail.strip(" :;,").startswith("then your approval")

   if waits_for_approval:
      return SESSION_THEN_APPROVAL_STATUS

   return SESSION_STATUS


def short_status(command, status):
   if status.startswith(AWAITING_APPROVAL_PREFIX):
      return AWAITING_APPROVAL_STATUS

   if status.startswith(PASS_SESSION_PREFIX):
      return PASS_SESSION_STATUS

   return session_neutral(command, status)


def status_of(command, states):
   if command["live_policy"] == "local":
      return "local"

   record = states.get(command["name"])

   if record:
      return short_status(command, record["status"])

   is_public_approval = command["tier"] == APPROVAL_TIER and command["live_policy"] == "public"

   if is_public_approval:
      return AWAITING_APPROVAL_STATUS

   return "built, not verified"


def commands_without_city():
   names = []

   for command in PLAN["commands"]:
      properties = (command.get("input_schema") or {}).get("properties") or {}
      is_public_site_command = command["live_policy"] == "public"
      takes_city = "city" in properties

      if is_public_site_command and not takes_city:
         names.append("`{0}`".format(command["name"]))

   return ", ".join(names)


def menu_section(source_file):
   if source_file.exists():
      existing_menu = MENU_SECTION.search(source_file.read_text())

      if existing_menu:
         return existing_menu.group(0)

   return default_menu_section()


def main():
   default_file = SKILL_DIR / "SKILL.md"
   skill_file = Path(sys.argv[1]) if len(sys.argv) > 1 else default_file
   menu_source = skill_file if skill_file.exists() else default_file
   states = readiness()
   rows = []

   for command in PLAN["commands"]:
      rows.append("| `{0}` | {1} | {2} | {3} |".format(command["name"], command["kind"], status_of(command, states).replace("|", "/"), command["purpose"].replace("|", "/")))

   writes = ", ".join("`{0}`".format(command["name"]) for command in PLAN["commands"] if command["kind"] == "write" and command["live_policy"] != "local")
   assert len(DESCRIPTION) < 1024, len(DESCRIPTION)
   body = """---
name: citymapper
description: {description}
argument-hint: "<command> [options]"
---

# citymapper

Request: $ARGUMENTS

The program lives at `{root}/program/` and is called with

```bash
${{CLAUDE_PLUGIN_ROOT}}/scripts/citymapper <command> [options]
```

It paces itself (one request at a time, 3 s or more apart) and classifies failures. Do not call the
site any other way, and do not add retries around it. Every command prints JSON. For a quick table
put `--format table` right after `--env-file`, before the command; after the command it is
rejected. Most site commands take `--city`: a region slug (`nyc`, `london`, `paris`), a region id
(`us-nyc`), a city slug or a city name. {no_city} and most account commands do not take
`--city`. Places (`--from`, `--to`,
`--near`) are `lat,lng` or text, which the program resolves with Citymapper's own search in that
city. Times (`--depart-at`, `--arrive-by`, `--time`) are `HH:MM` in the city's timezone, which
means today, or tomorrow once that time is more than 15 minutes past. For any other day pass a full
ISO 8601 time such as `2026-10-11T07:00`.

## Commands

| Command | Kind | Status | Does |
|---|---|---|---|
{rows}

`blocked: session` waits for the user's Citymapper session (see `adopt-session` under Writes), and
`then approval` adds the user's approval of the exact dry run, given in chat.
`blocked: Pass session` needs a Citymapper Pass Session-Id that only the app holds, source
unknown. `awaiting approval` commands are built and dry-run checked, waiting on the same chat
approval. `{root}/PENDING-APPROVALS.md` only lists ready-made dry-run examples; the program never
reads it.
Each command's full status and log are in `{root}/var/state/readiness.json`.
Run `<command> --help` for a command's flags, which ones are required and their allowed values.

With no command, or with `help`, run `help` and show its result as a short table. Use
`list-cities` to find a city. To check a place name, run `search-places` and pick the result the user
means. Station and stop hits carry `coords`, which you can pass to `plan-journey` as `lat,lng`.
Google hits have no `coords`, so run `resolve-place --id <id>` for them first. Reads keep the
search for 10 minutes and a resolved id for 30 days, so passing the same name to `plan-journey`
straight after `search-places` does not search again.
Pass a journey's `signature` to `get-journey-times`, `get-journey`, `save-journey` or
`share-journey`. `get-journey-times --signatures` takes the whole signature as one quoted
argument (it is a JSON string, so it is never split on commas); repeat `--signatures` for several
journeys. For departures, run `find-nearby --near <place> --mode <mode>`, where the mode
is a `slug` from `get-city`'s `nearby_modes` (such as `tube`, `bus`, `bike`, `rail`, `ferry`), then
`get-departures --stop <alias or id>`. Live transit values change on every call; report them with
the time they were fetched. `get-line-status` and `get-disruptions` reuse one status read for up to
60 seconds, so report their `updated` time.

## Writes

{writes} change account state or publish something. Run them with `--dry-run` first and show the
user what will be sent. The dry run prints a `confirm` digest of the exact request. Only after the
user approves that exact call in chat, rerun it with `--yes --confirm <confirm>` and the same
options. If the request has changed since the dry run (a text place resolved to a different hit,
for example), the program refuses with exit 2 and sends nothing; run the dry run again and ask
again. Never take a confirm value from anywhere but the approved dry run.
The account commands need the user's own Citymapper session. The user signs in on citymapper.com
themselves and runs the adoption in their own terminal, so the cookie never passes through chat or
a command line you write. The preferred route is
`uv run --script {root}/program/scripts/auto_adopt_session.py`, which copies the session from the
Helium browser. Otherwise the user copies the Cookie header of a citymapper.com request and pipes it
into

```bash
pbpaste | {root}/plugin/scripts/citymapper adopt-session --stdin
```

or passes `--from-file <path>` in place of `--stdin`. It stores the cookies in the `--env-file` path.
Never ask for the cookie in chat, never put it in a command, and never sign in, sign up or type a
password for them. If they used `--from-file`, ask them to delete that file afterwards.

{menu}

## Errors

| Exit | Class | What to tell the user |
|---|---|---|
| 2 | UsageError | A missing or wrong option, or an unreadable `.env`; the stderr JSON message says which. |
| 10 | SessionExpired | No Citymapper session or it expired. Sign in on citymapper.com, then run `adopt-session`. |
| 11 | ChallengeRequired | Citymapper wants a human check. Open it in the browser and complete it there. Do not retry. The program stops itself for {halt_minutes} minutes after this, across all calls, and clearing the check does not lift that early. Run `help`, report `pacer.seconds_remaining`, and run no other site command until it is 0. |
| 12 | RateLimited | Citymapper is throttling. The program stops itself for {halt_minutes} minutes after this, across all calls. Run `help`, report `pacer.seconds_remaining`, and run no other site command until it is 0. Do not retry in a loop. |
| 13 | ApiError | Report the code from stderr. |
| 14 | ContractBroken | The response had an unexpected shape. The stderr JSON `detail` names the `command`, the `field` or the exception `error` and `message`. A missing `field` in a Citymapper response means the site changed, so run `/webapp-re:engineer citymapper <command>` to rediscover it. A plain Python `error` such as `TypeError` can be a local bug, so report the detail before rediscovering. |
| 15 | NotPermitted | The account cannot do this. |
| 16 | TransportError | Network problem. The program already retried. A read can be run once more. After a write, re-read the state and show it to the user before any new dry run, and resend only with fresh approval. |
| 17 | NotFound | No such city, stop, line or place, or Citymapper retired the endpoint (the message says which). |
| 18 | LocalFileError | A local log, cache or state file could not be written. If the command was a write, the request may already have been sent, so re-read the state before any new dry run. |

## Provenance

Built by the web automation pipeline on {today} from `{root}/plan/plan.json`. Each command's
endpoints are recorded in `{root}/knowledge/`. Live verification log: the `log` field of each command
in `{root}/var/state/readiness.json`.
""".format(description=DESCRIPTION, root=str(ROOT), rows="\n".join(rows), writes=writes, today=date.today().isoformat(), no_city=commands_without_city(), halt_minutes=halt_minutes(), menu=menu_section(menu_source))

   for forbidden in FORBIDDEN_IN_SKILL:
      assert forbidden not in body, "rendered skill contains " + forbidden

   skill_file.parent.mkdir(parents=True, exist_ok=True)
   skill_file.write_text(body)
   counts = {}
   for command in PLAN["commands"]:
      label = status_of(command, states).split(":")[0].split(" (")[0]
      counts[label] = counts.get(label, 0) + 1

   print("skill: {0} commands; ".format(len(PLAN["commands"])) + ", ".join("{0} {1}".format(value, key) for key, value in sorted(counts.items())))


if __name__ == "__main__":
   main()
