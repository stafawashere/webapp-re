"""Record each passing live-check command as a kb.py verify pass on the findings it used.

Only the command's primary finding (its first plan dependency) is credited, because secondary
dependencies such as search for text places or fallbacks are not always called.

   python3 tools/engineer/kb_verify_live.py <run-id> var/logs/verify-A.json [var/logs/verify-B.json ...]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB = str(Path.home() / "dev/webapp-re/plugin/scripts/kb.py")
PLAN = json.loads((ROOT / "plan/plan.json").read_text())


def main():
   run_id = sys.argv[1]
   depends = {command["name"]: [dependency["finding"] for dependency in command["depends_on"]] for command in PLAN["commands"]}
   credited = 0

   for log_name in sys.argv[2:]:
      for line in (ROOT / log_name).read_text().splitlines():
         record = json.loads(line)
         is_pass = record.get("result") == "pass" and record.get("requests", 0) > 0

         if not is_pass:
            continue

         findings = depends.get(record["command"], [])[:1]
         for finding in findings:
            detail = "program live check {0} ({1}): exit 0, schema and invariants passed, {2} requests".format(record["label"], Path(log_name).name, record["requests"])
            result = subprocess.run(["uv", "run", "--script", KB, "verify", "--root", str(ROOT), "--run", run_id, "--id", finding, "--result", "pass", "--detail", detail], capture_output=True, text=True)
            credited += 1 if result.returncode == 0 else 0

   print("credited {0} live passes".format(credited))


if __name__ == "__main__":
   main()
