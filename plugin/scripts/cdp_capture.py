#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=12"]
# ///
"""One capture window over the Chrome DevTools Protocol.

    uv run --script cdp_capture.py --root <site-root> --run <run-id> --label inbox --url https://example.com/inbox --seconds 12
    uv run --script cdp_capture.py --root <site-root> --run <run-id> --label send --target-id <id> --action-file click.js

Attaches to a Chromium already listening on --port. Never launches one. Opens its own tab as
about:blank, attaches to it explicitly, enables Network, and navigates last, so the cold load is
inside the window. Bodies are read on loadingFinished. Credential header values and token-like
body fields are redacted at the writer. Closes only the tab it created.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from urllib.parse import parse_qsl, urlencode

import websockets

DEFAULT_FILTER = r"/api/|graphql|/rpc|/ajax/|/_next/data/|\.json(\?|$)"
SENSITIVE_HEADER = re.compile(r"(?i)^(cookie|set-cookie|authorization|proxy-authorization|uid)$|csrf|xsrf|token|secret|session|api-key|apikey|user-device|device-id")
SENSITIVE_FIELD = re.compile(r"(?i)csrf|xsrf|token|secret|session|password|passwd|dtsg|^lsd$|auth|signature|nonce")
CALL_TIMEOUT_SECONDS = 10


def redact(value):
   return "<redacted len={0}>".format(len(value or ""))


def redact_headers(headers):
   return {name: redact(str(value)) if SENSITIVE_HEADER.search(name) else value for name, value in (headers or {}).items()}


def redact_body(body, content_type):
   if not body:
      return body

   looks_like_json = "json" in (content_type or "") or body.lstrip().startswith(("{", "["))
   if looks_like_json:
      try:
         return json.dumps(redact_json(json.loads(body)))
      except ValueError:
         pass

   looks_like_form = "=" in body and " " not in body[:200]
   if looks_like_form:
      pairs = parse_qsl(body, keep_blank_values=True)
      return urlencode([(key, redact(value) if SENSITIVE_FIELD.search(key) else value) for key, value in pairs])

   return body


def redact_json(node):
   if isinstance(node, dict):
      return {key: redact(str(value)) if SENSITIVE_FIELD.search(key) and isinstance(value, (str, int)) else redact_json(value) for key, value in node.items()}

   if isinstance(node, list):
      return [redact_json(item) for item in node]

   return node


class Connection:
   def __init__(self, socket):
      self.socket = socket
      self.next_id = 0
      self.pending = {}
      self.events = asyncio.Queue()

   async def pump(self):
      async for raw in self.socket:
         message = json.loads(raw)
         waiter = self.pending.pop(message.get("id"), None)

         if waiter is not None:
            waiter.set_result(message)
         elif "method" in message:
            await self.events.put(message)

   async def call(self, method, params=None, session=None):
      self.next_id += 1
      call_id = self.next_id
      waiter = asyncio.get_running_loop().create_future()
      self.pending[call_id] = waiter
      payload = {"id": call_id, "method": method, "params": params or {}}

      if session:
         payload["sessionId"] = session

      await self.socket.send(json.dumps(payload))

      try:
         message = await asyncio.wait_for(waiter, CALL_TIMEOUT_SECONDS)
      except asyncio.TimeoutError:
         self.pending.pop(call_id, None)
         return {"error": {"message": "timeout after {0}s".format(CALL_TIMEOUT_SECONDS)}}

      return message


def browser_socket_url(port):
   with urllib.request.urlopen("http://127.0.0.1:{0}/json/version".format(port), timeout=5) as response:
      return json.loads(response.read())["webSocketDebuggerUrl"]


async def capture(args):
   try:
      socket_url = browser_socket_url(args.port)
   except OSError as error:
      sys.exit("cdp_capture: nothing listening on port {0} ({1}). Start the browser with --remote-debugging-port.".format(args.port, error))

   url_filter = None if args.filter == "all" else re.compile(args.filter)
   records = {}
   frames = []

   async with websockets.connect(socket_url, max_size=None) as socket:
      connection = Connection(socket)
      pump = asyncio.create_task(connection.pump())
      created_target = None

      if args.target_id:
         target_id = args.target_id
      else:
         created = await connection.call("Target.createTarget", {"url": "about:blank"})
         target_id = created["result"]["targetId"]
         created_target = target_id

      attached = await connection.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})
      session = attached["result"]["sessionId"]
      await connection.call("Network.enable", {"maxTotalBufferSize": 200_000_000, "maxResourceBufferSize": 50_000_000}, session)
      await connection.call("Page.enable", {}, session)

      if args.url and not args.target_id:
         await connection.call("Page.navigate", {"url": args.url}, session)

      action_result = None
      if args.action_js or args.action_file:
         expression = args.action_js or open(args.action_file, encoding="utf-8").read()
         await asyncio.sleep(args.settle)
         evaluated = await connection.call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True}, session)
         action_result = evaluated.get("result", {}).get("result", {}).get("value")

      deadline = asyncio.get_running_loop().time() + args.seconds

      while True:
         remaining = deadline - asyncio.get_running_loop().time()
         if remaining <= 0:
            break

         try:
            event = await asyncio.wait_for(connection.events.get(), remaining)
         except asyncio.TimeoutError:
            break

         if event.get("sessionId") != session:
            continue

         await handle_event(connection, session, event, records, frames, url_filter)

      if created_target and not args.keep_tab:
         await connection.call("Target.closeTarget", {"targetId": created_target})

      pump.cancel()

   return target_id, records, frames, action_result


async def handle_event(connection, session, event, records, frames, url_filter):
   method = event["method"]
   params = event["params"]
   request_id = params.get("requestId")

   if method == "Network.requestWillBeSent":
      request = params["request"]
      is_candidate = url_filter is None or url_filter.search(request["url"]) is not None
      if not is_candidate:
         return

      record = records.setdefault(request_id, {})
      record.update({"request_id": request_id, "method": request["method"], "url": request["url"], "type": params.get("type"), "request_headers": request.get("headers", {}), "post_data": request.get("postData")})
      needs_post_data = request.get("hasPostData") and not request.get("postData")
      if needs_post_data:
         reply = await connection.call("Network.getRequestPostData", {"requestId": request_id}, session)
         record["post_data"] = reply.get("result", {}).get("postData")
      return

   if method == "Network.requestWillBeSentExtraInfo":
      records.setdefault(request_id, {})["wire_headers"] = params.get("headers", {})
      return

   if method == "Network.responseReceived" and request_id in records:
      response = params["response"]
      records[request_id].update({"status": response.get("status"), "mime": response.get("mimeType"), "response_headers": response.get("headers", {}), "from_service_worker": response.get("fromServiceWorker", False)})
      return

   if method == "Network.loadingFinished" and "url" in records.get(request_id, {}):
      reply = await connection.call("Network.getResponseBody", {"requestId": request_id}, session)
      if "error" in reply:
         records[request_id]["body_error"] = reply["error"].get("message")
      else:
         result = reply["result"]
         records[request_id]["response_body"] = "<base64 len={0}>".format(len(result["body"])) if result.get("base64Encoded") else result["body"]
      return

   if method == "Network.loadingFailed" and "url" in records.get(request_id, {}):
      records[request_id]["failed"] = params.get("errorText")
      return

   if method in ("Network.webSocketFrameSent", "Network.webSocketFrameReceived"):
      payload = params["response"].get("payloadData", "")
      frames.append({"direction": "sent" if method.endswith("Sent") else "received", "opcode": params["response"].get("opcode"), "length": len(payload)})


def write_capture(args, records, frames):
   directory = os.path.join(args.root, "var", "captures")
   os.makedirs(directory, exist_ok=True)
   path = os.path.join(directory, "{0}-{1}.jsonl".format(args.run, args.label))
   kept = [record for record in records.values() if "url" in record]

   descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
   os.fchmod(descriptor, 0o600)

   with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
      for record in kept:
         request_type = (record.get("request_headers") or {}).get("Content-Type") or (record.get("request_headers") or {}).get("content-type")
         clean = dict(record)
         clean["request_headers"] = redact_headers(record.get("request_headers"))
         clean["wire_headers"] = redact_headers(record.get("wire_headers"))
         clean["response_headers"] = redact_headers(record.get("response_headers"))
         clean["post_data"] = redact_body(record.get("post_data"), request_type)
         clean["captured_at"] = datetime.now().isoformat(timespec="seconds")
         handle.write(json.dumps(clean) + "\n")

      for frame in frames:
         handle.write(json.dumps({"websocket_frame": frame}) + "\n")

   return path, kept


def main():
   parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
   parser.add_argument("--root", required=True, help="site directory from kb.py path")
   parser.add_argument("--run", required=True)
   parser.add_argument("--label", required=True)
   parser.add_argument("--url")
   parser.add_argument("--target-id", help="reuse a tab a previous window kept open")
   parser.add_argument("--action-js")
   parser.add_argument("--action-file")
   parser.add_argument("--settle", type=float, default=4.0, help="seconds to wait before the action")
   parser.add_argument("--seconds", type=float, default=12.0, help="drain window")
   parser.add_argument("--filter", default=DEFAULT_FILTER, help="regex on the URL, or 'all'")
   parser.add_argument("--port", type=int, default=9222)
   parser.add_argument("--keep-tab", action="store_true")
   args = parser.parse_args()

   has_trigger = args.url or args.target_id
   if not has_trigger:
      parser.error("pass --url for a new tab or --target-id to reuse one")

   target_id, records, frames, action_result = asyncio.run(capture(args))
   path, kept = write_capture(args, records, frames)

   for record in kept:
      path_only = record["url"].split("?")[0]
      response_length = len(record.get("response_body") or "")
      request_length = len(record.get("post_data") or "")
      print("{0:6} {1:>4} req {2:>6} res {3:>8}  {4}".format(record["method"], record.get("status", "-"), request_length, response_length, path_only))

   print("records: {0}, websocket frames: {1}".format(len(kept), len(frames)))
   print("capture: {0}".format(path))
   print("target: {0}".format(target_id))

   if action_result is not None:
      print("action: {0}".format(json.dumps(action_result)[:2000]))


if __name__ == "__main__":
   main()
