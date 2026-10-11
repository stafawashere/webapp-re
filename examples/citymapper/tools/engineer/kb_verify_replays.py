"""Turn replay logs into kb.py verify calls.

Passing steps become verify passes. Steps listed in INPUT_MISTAKES failed because of the input I
chose, not the endpoint, so they are not recorded against it. Endpoints in RETIRED failed with the
site's own 'no longer supported' or 'Page Not Found' answer and are recorded as fails, then dead.

   python3 tools/engineer/kb_verify_replays.py <run-id> var/logs/replay-A.json [var/logs/replay-B.json ...]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB = str(Path.home() / "dev/webapp-re/plugin/scripts/kb.py")
INPUT_MISTAKES = {
   "placeresolve-1": "sent a citymapper station id; placeresolve resolves google: ids",
   "walk1-1": "checked for journeys; /api/1/walk answers routes[]",
   "trip-meta-1": "checked for JSON; the page answers HTML",
   "nearby2-2": "sent kinds=transitstop without brand_ids; the server answered 500 'Oh noes.'",
   "rail-2": "guessed id RailStationNewYorkPenn; the id is RailStationPennStation",
   "everything-1": "sent size=500; the API wants a named size (small, large)",
   "bus-2": "skipped, its input came from nearby2-2",
}
RETIRED = {
   "vehiclehire": "404 {\"error\": \"This API is no longer supported\"} in London and Paris",
   "eta": "404 'Page Not Found' HTML for fresh signatures in New York and Paris",
   "weather": "404 'Page Not Found' HTML in New York and London",
   "transitscore": "404 'Page Not Found' HTML in New York and London",
}


def kb(*arguments):
   result = subprocess.run(["uv", "run", "--script", KB, *arguments, "--root", str(ROOT)], capture_output=True, text=True)
   return (result.stdout or result.stderr).strip().splitlines()[-1:] or [""]


def main():
   run_id = sys.argv[1]
   passes = fails = skipped = 0

   for log_name in sys.argv[2:]:
      for line in (ROOT / log_name).read_text().splitlines():
         step = json.loads(line)
         key = step["key"]
         finding = step["finding"]

         if key in INPUT_MISTAKES:
            skipped += 1
            continue

         if step.get("pass"):
            print(kb("verify", "--run", run_id, "--id", finding, "--result", "pass", "--detail", "replay {0}: HTTP {1}, {2}".format(key, step.get("status"), step.get("detail")))[0])
            passes += 1
         elif finding in RETIRED:
            print(kb("verify", "--run", run_id, "--id", finding, "--result", "fail", "--detail", "replay {0}: HTTP {1}, {2}".format(key, step.get("status"), RETIRED[finding]))[0])
            fails += 1

   print("verify passes {0}, fails {1}, input mistakes skipped {2}".format(passes, fails, skipped))


if __name__ == "__main__":
   main()
