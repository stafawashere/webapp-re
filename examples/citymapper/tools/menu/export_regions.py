"""Write var/public/regions.json, the region list the /citymapper menu offers for --city.

Reads the program's catalogue cache (var/cache/catalogue.json, filled by list-cities); sends nothing.
   python3 tools/menu/export_regions.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "var/cache/catalogue.json"
OUTPUT = ROOT / "var/public/regions.json"


def main():
   catalogue = json.loads(CATALOGUE.read_text())
   rows = []

   for region in catalogue["regions"]:
      label = "{0} ({1})".format(region["name"], region["slug"])
      rows.append({"slug": region["slug"], "label": label, "region_id": region["region_id"], "api_enabled": region.get("api_enabled", True)})

   rows.sort(key=lambda row: row["label"].lower())
   OUTPUT.parent.mkdir(parents=True, exist_ok=True)
   OUTPUT.write_text(json.dumps(rows, indent=1) + "\n")
   print("regions: {0} -> {1}".format(len(rows), OUTPUT.relative_to(ROOT)))


if __name__ == "__main__":
   main()
