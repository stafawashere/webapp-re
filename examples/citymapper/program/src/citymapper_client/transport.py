import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit

from .classify import classify
from .config import DEFAULT_USER_AGENT
from .endpoints import ORIGIN
from .errors import ChallengeRequired, ContractBroken, RateLimited, TransportError

RETRY_DELAYS_SECONDS = (5, 10)
MAX_REDIRECTS = 5
CREDENTIAL_HEADER_NAMES = {"cookie", "x-csrftoken", "session-id", "user-device", "authorization"}
VOLATILE_BODY_FIELDS = ("created", "modified", "last_used")
CONFIRM_DIGEST_LENGTH = 12


def network_error_type():
   # httpx costs tens of milliseconds to import, and commands that send nothing never need it.
   import httpx

   return httpx.HTTPError


def origin_of(address):
   parts = urlsplit(str(address))
   return "{0}://{1}".format(parts.scheme, parts.netloc)


def utc_now_iso():
   return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def without_volatile_fields(value):
   if isinstance(value, dict):
      return {key: without_volatile_fields(item) for key, item in value.items() if key not in VOLATILE_BODY_FIELDS}

   if isinstance(value, list):
      return [without_volatile_fields(item) for item in value]

   looks_like_json_object = isinstance(value, str) and value.startswith("{")
   if looks_like_json_object:
      try:
         decoded = json.loads(value)
      except ValueError:
         return value

      return without_volatile_fields(decoded)

   return value


class Request:
   def __init__(self, endpoint, query=None, json_body=None, form_json=None, headers=None, path_values=None):
      self.endpoint = endpoint
      self.query = {key: value for key, value in (query or {}).items() if value is not None}
      self.json_body = json_body
      self.form_json = form_json
      self.headers = dict(headers or {})
      self.path_values = path_values or {}

   @property
   def url(self):
      address = self.endpoint.url(**self.path_values)
      return address + ("?" + urlencode(self.query) if self.query else "")

   def body_text(self):
      if self.form_json is not None:
         return json.dumps(self.form_json)

      if self.json_body is not None:
         return json.dumps(self.json_body)

      return None

   def describe(self):
      body = self.form_json if self.form_json is not None else self.json_body
      return {"method": self.endpoint.method, "url": self.url, "body": body if body is not None else {}, "finding": self.endpoint.finding}

   def confirm_digest(self):
      body = self.form_json if self.form_json is not None else self.json_body
      stable_request = {"method": self.endpoint.method, "url": self.url, "body": without_volatile_fields(body)}
      encoded = json.dumps(stable_request, sort_keys=True, separators=(",", ":")).encode()
      return hashlib.sha256(encoded).hexdigest()[:CONFIRM_DIGEST_LENGTH]


class Transport:
   def __init__(self, session, pacer, logs_dir, client=None, sleeper=time.sleep, clock=utc_now_iso, run_id=None, command=None):
      self.session = session
      self.pacer = pacer
      self.logs_dir = logs_dir
      self.sleeper = sleeper
      self.clock = clock
      self.run_id = run_id
      self.command = command
      self.request_count = 0
      self.first_sent_at = None
      self.last_sent_at = None
      self._client = client

   @property
   def client(self):
      if self._client is None:
         import httpx

         self._client = httpx.Client(timeout=40.0, follow_redirects=False)

      return self._client

   def _headers(self, request):
      headers = {
         "User-Agent": self.session.user_agent or DEFAULT_USER_AGENT,
         "Accept": "*/*",
         "Accept-Language": "en-US,en;q=0.9",
         "Referer": ORIGIN + "/",
         "Content-Type": "application/json; charset=utf-8",
      }

      if request.form_json is not None:
         headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

      has_body = request.form_json is not None or request.json_body is not None
      if has_body:
         headers["Origin"] = ORIGIN

      wants_cookies = request.endpoint.signed_in or request.endpoint.sends_cookies
      is_site_host = request.endpoint.host == ORIGIN
      should_send_cookies = wants_cookies and is_site_host and bool(self.session.cookies)
      if should_send_cookies:
         headers["Cookie"] = self.session.cookie_header()

      csrf_token = self.session.cookies.get("csrftoken")
      wants_csrf = request.endpoint.csrf and csrf_token
      if wants_csrf:
         headers["X-CSRFToken"] = csrf_token

      headers.update(request.headers)
      return headers

   def _log(self, request, status, elapsed_ms, size, error_class=None, attempt=1):
      self.logs_dir.mkdir(parents=True, exist_ok=True)
      line = {
         "at": datetime.now().isoformat(timespec="seconds"),
         "run": self.run_id,
         "command": self.command,
         "attempt": attempt,
         "finding": request.endpoint.finding,
         "method": request.endpoint.method,
         "path": request.endpoint.path,
         "status": status,
         "ms": elapsed_ms,
         "bytes": size,
         "class": error_class,
      }
      log_path = self.logs_dir / "requests-{0}.jsonl".format(datetime.now().strftime("%Y-%m-%d"))

      with log_path.open("a") as handle:
         handle.write(json.dumps(line) + "\n")

   def _record_send_time(self):
      sent_at = self.clock()

      if self.first_sent_at is None:
         self.first_sent_at = sent_at

      self.last_sent_at = sent_at

   def _send_once(self, request, address):
      with self.pacer.turn():
         self._record_send_time()
         started = time.monotonic()
         response = self.client.request(request.endpoint.method, address, headers=self._headers(request), content=request.body_text(), follow_redirects=False)
         elapsed_ms = int((time.monotonic() - started) * 1000)

      self.request_count += 1
      return response, elapsed_ms

   def _carries_credentials(self, request):
      sent_header_names = {name.lower() for name in self._headers(request)}
      return bool(sent_header_names & CREDENTIAL_HEADER_NAMES)

   def _refused_redirect(self, request, response, target, is_read, hops_followed):
      stays_on_endpoint_host = origin_of(target) == request.endpoint.host
      detail = {"status": response.status_code, "url_path": request.endpoint.path}

      if not is_read:
         return ContractBroken("Citymapper redirected a {0} request, which was not followed. If it was a write it may have landed, so re-read before sending it again.".format(request.endpoint.method), detail)

      leaves_with_credentials = not stays_on_endpoint_host and self._carries_credentials(request)
      if leaves_with_credentials:
         return ContractBroken("Citymapper redirected to another host, which was not followed.", {**detail, "redirect_host": target.host})

      if hops_followed >= MAX_REDIRECTS:
         return ContractBroken("Citymapper redirected more than {0} times.".format(MAX_REDIRECTS), detail)

      return None

   def _exchange(self, request, is_read, attempt):
      address = request.url
      hops_followed = 0

      while True:
         response, elapsed_ms = self._send_once(request, address)

         if not response.is_redirect:
            return response, elapsed_ms

         target = response.url.join(response.headers["location"])
         refusal = self._refused_redirect(request, response, target, is_read, hops_followed)
         if refusal is not None:
            self._log(request, response.status_code, elapsed_ms, len(response.content), refusal.error_class, attempt)
            raise refusal

         self._log(request, response.status_code, elapsed_ms, len(response.content), "Redirect", attempt)
         address = str(target)
         hops_followed += 1

   def send(self, request):
      is_read = request.endpoint.method == "GET" and not request.endpoint.writes
      attempts = len(RETRY_DELAYS_SECONDS) + 1 if is_read else 1

      for attempt_index in range(attempts):
         attempt = attempt_index + 1

         try:
            response, elapsed_ms = self._exchange(request, is_read, attempt)
            break
         except network_error_type() as error:
            self._log(request, None, 0, 0, "TransportError", attempt)
            is_last_attempt = attempt == attempts

            if is_last_attempt:
               raise TransportError("Network error talking to Citymapper: {0}".format(type(error).__name__), {"url_path": request.endpoint.path}) from error

            self.sleeper(RETRY_DELAYS_SECONDS[attempt_index])

      try:
         body = classify(response.status_code, response.headers.get("content-type"), response.text, request.endpoint.expect, request.endpoint.signed_in)
      except RateLimited as error:
         self.pacer.halt("throttle")
         self._log(request, response.status_code, elapsed_ms, len(response.content), error.error_class, attempt)
         raise
      except ChallengeRequired as error:
         self.pacer.halt("challenge")
         self._log(request, response.status_code, elapsed_ms, len(response.content), error.error_class, attempt)
         raise
      except Exception as error:
         self._log(request, response.status_code, elapsed_ms, len(response.content), type(error).__name__, attempt)
         raise

      self._log(request, response.status_code, elapsed_ms, len(response.content), attempt=attempt)
      return body
