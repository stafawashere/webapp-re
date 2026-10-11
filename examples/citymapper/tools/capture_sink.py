#!/usr/bin/env python3
"""Local sink for page captures from the Chrome walk.

The page POSTs JSON records to http://127.0.0.1:<port>/sink and each one is appended as a line to
var/captures/<label>.jsonl. Only listens on loopback.

   python3 tools/capture_sink.py --port 8765 --label walk-2026-10-10
"""

import argparse
import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
SENSITIVE_KEY = re.compile(r"(?i)cookie|csrf|xsrf|token|secret|session|password|authorization|signature")


def redact(node):
   if isinstance(node, dict):
      return {key: "<redacted>" if SENSITIVE_KEY.search(key) and isinstance(value, (str, int)) else redact(value) for key, value in node.items()}

   if isinstance(node, list):
      return [redact(item) for item in node]

   return node


class SinkHandler(BaseHTTPRequestHandler):
   output_path = None

   def _cors(self):
      self.send_header("Access-Control-Allow-Origin", "https://citymapper.com")
      self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
      self.send_header("Access-Control-Allow-Headers", "Content-Type")
      self.send_header("Access-Control-Allow-Private-Network", "true")

   def do_OPTIONS(self):
      self.send_response(204)
      self._cors()
      self.end_headers()

   def do_POST(self):
      length = int(self.headers.get("Content-Length", "0"))
      raw = self.rfile.read(length)

      try:
         payload = json.loads(raw)
      except ValueError:
         self.send_response(400)
         self._cors()
         self.end_headers()
         return

      records = payload if isinstance(payload, list) else [payload]

      with self.output_path.open("a", encoding="utf-8") as handle:
         for record in records:
            record = redact(record)
            record["received"] = datetime.now().isoformat(timespec="seconds")
            handle.write(json.dumps(record) + "\n")

      self.send_response(200)
      self._cors()
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({"stored": len(records)}).encode())

   def log_message(self, format, *args):
      pass


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("--port", type=int, default=8765)
   parser.add_argument("--label", required=True)
   args = parser.parse_args()

   captures_dir = SITE_ROOT / "var" / "captures"
   captures_dir.mkdir(parents=True, exist_ok=True)
   SinkHandler.output_path = captures_dir / (args.label + ".jsonl")

   server = ThreadingHTTPServer(("127.0.0.1", args.port), SinkHandler)
   print("sink listening on 127.0.0.1:{0} -> {1}".format(args.port, SinkHandler.output_path), flush=True)
   server.serve_forever()


if __name__ == "__main__":
   main()
