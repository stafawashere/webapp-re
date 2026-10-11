"""Record every non-noise scope endpoint as a knowledge base finding with status hypothesis.

Existing findings are skipped, so a rerun never resets a verified finding.
   python3 tools/scope/record_findings.py run-2026-10-10-082844
"""
import json
import subprocess
import sys
from pathlib import Path

from scope_data import CAPABILITIES, ENDPOINTS

ROOT = Path(__file__).resolve().parents[2]
KB = str(Path.home() / "dev/webapp-re/plugin/scripts/kb.py")


def goal_for(endpoint_id):
   for capability in CAPABILITIES:
      if endpoint_id in capability["endpoints"]:
         return capability["name"]

   return endpoint_id


def main():
   run_id = sys.argv[1]
   recorded = 0
   skipped = 0

   for endpoint in ENDPOINTS:
      if endpoint.get("noise"):
         continue

      finding_path = ROOT / "knowledge" / "endpoints" / (endpoint["id"] + ".md")
      if finding_path.exists():
         skipped += 1
         continue

      seen = "observed live in the 2026-10-10 scope walk" if endpoint["observed"] else "read from the bundle only, not observed live"
      notes = "{0}. {1}".format(seen, endpoint.get("notes", "")).strip()
      command = [
         "uv", "run", "--script", KB, "record-finding",
         "--root", str(ROOT),
         "--run", run_id,
         "--id", endpoint["id"],
         "--goal", goal_for(endpoint["id"]),
         "--method", endpoint["method"],
         "--url", endpoint["url_pattern"],
         "--surface", endpoint["surface"],
         "--status", "hypothesis",
         "--headers", ",".join(endpoint.get("request_header_names", [])),
         "--body-shape", ", ".join(endpoint.get("body_fields", [])) or "none",
         "--response-shape", json.dumps(endpoint.get("response_shape", {})),
         "--notes", notes,
      ]
      result = subprocess.run(command, capture_output=True, text=True)

      if result.returncode != 0:
         print("failed {0}: {1}".format(endpoint["id"], result.stderr.strip()[-300:]))
         continue

      recorded += 1

   print("findings recorded {0}, skipped {1}".format(recorded, skipped))


if __name__ == "__main__":
   main()
