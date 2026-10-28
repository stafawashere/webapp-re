"""Run every write command with --dry-run and write PENDING-APPROVALS.md with the exact calls.

Dry runs send nothing to the write endpoint; a few resolve a city, place or line first (reads).
   python3 tools/engineer/pending_approvals.py
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = ROOT / "program"
CLI = "UV_PROJECT_ENVIRONMENT={0} uv run --frozen --project {1} citymapper --env-file {2}".format(PROGRAM / ".venv", PROGRAM, ROOT / ".env")
SAMPLE_SIGNATURE_NOTE = "<signature from plan-journey>"

APPROVAL_WRITES = [
   {"command": "share-journey", "argv": ["--city", "nyc", "--signature", SAMPLE_SIGNATURE_NOTE], "why": "Creates a public citymapper.com/trip link to a journey; anyone with the link can open it and it cannot be deleted."},
   {"command": "create-go-link", "argv": ["--city", "nyc", "--place", "40.748441,-73.985664", "--title", "Meet at the Empire State Building", "--message", "See you at 7"], "why": "Creates a public Meet Me Somewhere link with your title and message; it cannot be deleted."},
   {"command": "vote-for-city", "argv": ["--city-slug", "<city to vote for>", "--email", "<your e-mail>"], "why": "Sends your e-mail address to Citymapper with a city vote; no undo."},
   {"command": "sign-out", "argv": [], "why": "Ends the stored Citymapper session; signing back in is yours to do."},
   {"command": "pass-set-default-payment", "argv": ["--use-web-session-id", "--provider", "<payment provider id>", "--payment-method-id", "<payment method id from pass-account>"], "why": "Changes the default payment method of your paid Citymapper Pass."},
   {"command": "pass-add-payment-method", "argv": ["--use-web-session-id", "--provider", "<payment provider id>", "--payment-method-id", "<token from the payment provider>"], "why": "Attaches a payment method to Citymapper Pass. The token comes from the payment provider; never type a card number."},
   {"command": "pass-remove-payment-method", "argv": ["--use-web-session-id", "--provider", "<payment provider id>", "--payment-method-id", "<payment method id from pass-account>"], "why": "Removes a Pass payment method; no inverse."},
   {"command": "pass-remove-all-payment-methods", "argv": ["--use-web-session-id", "--provider", "<payment provider id>"], "why": "Removes every Pass payment method for a provider; no inverse."},
]

ROUND_TRIP_WRITES = [
   {"command": "save-place", "argv": ["--city", "nyc", "--name", "Test place (citymapper skill)", "--near", "40.748441,-73.985664"], "inverse": "remove-place --id <place id returned>"},
   {"command": "update-place", "argv": ["--id", "<place id from list-saved-places>", "--name", "Renamed place"], "inverse": "update-place --id <same id> --name <name read before>"},
   {"command": "remove-place", "argv": ["--id", "<place id from list-saved-places>"], "inverse": "save-place with the name, address and coords read before (the id changes)"},
   {"command": "add-favourite", "argv": ["--city", "nyc", "--line", "subway-6"], "inverse": "remove-favourite --id <favourite id returned>"},
   {"command": "remove-favourite", "argv": ["--id", "<favourite id from list-favourites>"], "inverse": "add-favourite with the same stop or line"},
   {"command": "save-journey", "argv": ["--city", "nyc", "--signature", SAMPLE_SIGNATURE_NOTE], "inverse": "remove-saved-journey --document-id <document id returned>; may also notify your phone, which cannot be undone"},
   {"command": "remove-saved-journey", "argv": ["--document-id", "<document id returned by save-journey>"], "inverse": "only for a journey this program saved"},
   {"command": "update-profile", "argv": ["--first-name", "<new first name>"], "inverse": "update-profile with the values whoami shows before"},
]


def dry_run(command, argv):
   program_environment = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(PROGRAM / ".venv")}
   result = subprocess.run(["uv", "run", "--frozen", "--project", str(PROGRAM), "citymapper", command, *argv, "--dry-run"], capture_output=True, text=True, cwd=PROGRAM, env=program_environment)

   if result.returncode != 0:
      return {"exit": result.returncode, "stderr": result.stderr.strip()[-400:]}

   return json.loads(result.stdout)


def quote(argv):
   return " ".join("'{0}'".format(item) if (" " in item or "<" in item) else item for item in argv)


READINESS_FILE = ROOT / "var/state/readiness.json"
PUBLIC_APPROVAL = {"share-journey", "create-go-link"}


def readiness_status(command, preview, is_round_trip):
   if "exit" in preview:
      return None

   if is_round_trip:
      return "needs session: round trip with inverse ready, dry run checked"

   if command in PUBLIC_APPROVAL:
      return "built, awaiting approval (dry run checked; PENDING-APPROVALS.md)"

   if command.startswith("pass-"):
      return "blocked: needs a Citymapper Pass session from the app (Session-Id source unknown); dry run checked; PENDING-APPROVALS.md"

   return "needs session: then your approval (dry run checked; PENDING-APPROVALS.md)"


def section(entry, extra_line):
   command = entry["command"]
   preview = dry_run(command, entry["argv"])
   lines = [
      "### {0}".format(command),
      "",
      extra_line,
      "",
      "Dry run (sends nothing to the write endpoint):",
      "",
      "```bash",
      "{0} {1} {2} --dry-run".format(CLI, command, quote(entry["argv"])).strip(),
      "```",
      "",
      "```json",
      json.dumps(preview, indent=1)[:1500],
      "```",
      "",
      "After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:",
      "",
      "```bash",
      "{0} {1} {2} --yes --confirm '<confirm value printed by the dry run you approved>'".format(CLI, command, quote(entry["argv"])).strip(),
      "```",
      "",
   ]
   return lines, preview


def main():
   parts = [
      "# Pending approvals",
      "",
      "Generated {0} by tools/engineer/pending_approvals.py. Nothing here was sent. Each entry shows the".format(datetime.now().strftime("%Y-%m-%d %H:%M")),
      "dry run the program prints and the exact live call to run after you approve it in chat. Values in",
      "angle brackets are yours to choose.",
      "",
      "## First: your Citymapper session",
      "",
      "Every account command below needs your own session. The program never signs in for you (it could",
      "create an account). If `help` shows no session cookie: sign in on citymapper.com in your browser,",
      "copy the Cookie request header of any citymapper.com request, then",
      "",
      "```bash",
      "pbpaste | {0} adopt-session --stdin".format(CLI),
      "```",
      "",
      "It stores only sessionid, csrftoken, uid, uid_set, cm_region and _locale in `.env` (mode 600) and",
      "prints names and lengths, never values. Then `whoami` should print `\"signed_in\": true`.",
      "",
      "## Approval writes",
      "",
      "Public, personal-data, payment or no-inverse actions. Never run without your approval of the exact call.",
      "",
   ]
   failures = 0
   readiness = json.loads(READINESS_FILE.read_text()) if READINESS_FILE.exists() else {}
   stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")

   for entry in APPROVAL_WRITES:
      lines, preview = section(entry, "Why it needs approval: " + entry["why"])
      failures += 1 if "exit" in preview else 0
      parts += lines
      status = readiness_status(entry["command"], preview, False)
      if status:
         readiness[entry["command"]] = {"status": status, "checked_at": stamp, "log": "PENDING-APPROVALS.md"}

   parts += [
      "## Round-trip writes (need your session)",
      "",
      "Each has an exact inverse the program implements. With a session, they can be verified by: read, write,",
      "read back, run the inverse, read back to the starting state. They were not run overnight because there",
      "is no session.",
      "",
   ]

   for entry in ROUND_TRIP_WRITES:
      lines, preview = section(entry, "Inverse: " + entry["inverse"])
      failures += 1 if "exit" in preview else 0
      parts += lines
      status = readiness_status(entry["command"], preview, True)
      if status:
         readiness[entry["command"]] = {"status": status, "checked_at": stamp, "log": "PENDING-APPROVALS.md"}

   READINESS_FILE.write_text(json.dumps(readiness, indent=1) + "\n")

   (ROOT / "PENDING-APPROVALS.md").write_text("\n".join(parts).rstrip("\n") + "\n")
   print("PENDING-APPROVALS.md: {0} approval writes, {1} round-trip writes; dry runs failed: {2}".format(len(APPROVAL_WRITES), len(ROUND_TRIP_WRITES), failures))


if __name__ == "__main__":
   main()
