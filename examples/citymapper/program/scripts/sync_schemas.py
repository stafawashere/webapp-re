"""Copy every command's metadata and schemas from plan/plan.json into the package (schemas.json)."""
import json
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parents[1]
SITE_ROOT = PROGRAM_DIR.parent
KEPT_FIELDS = ("name", "purpose", "kind", "tier", "live_policy", "input_schema", "output_schema", "confirmation", "depends_on", "requests")


def main():
   plan = json.loads((SITE_ROOT / "plan/plan.json").read_text())
   commands = {command["name"]: {field: command.get(field) for field in KEPT_FIELDS} for command in plan["commands"]}
   target = PROGRAM_DIR / "src/citymapper_client/schemas.json"
   target.write_text(json.dumps({"generated_from": "plan/plan.json " + plan["generated"], "commands": commands}, indent=1) + "\n")
   print("schemas.json: {0} commands".format(len(commands)))


if __name__ == "__main__":
   main()
