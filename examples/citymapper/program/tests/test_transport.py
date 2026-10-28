import json
import os
import subprocess
import sys
from datetime import datetime

import httpx
import pytest

from citymapper_client import cli, endpoints
from citymapper_client.errors import ChallengeRequired, ContractBroken, NotFound, RateLimited, SessionExpired, TransportError
from citymapper_client.pacing import Pacer
from citymapper_client.session import Session
from citymapper_client.transport import Request, Transport

from support import SIGNED_IN_COOKIES

JSON_HEADERS = {"content-type": "application/json; charset=utf8"}
CITYMAPPER_HOSTS = {"citymapper.com", "turnstile-api.citymapper.com"}
FOREIGN_LOCATION = "https://elsewhere.example.net/collect"


class RecordingHandler:
   def __init__(self, respond):
      self.respond = respond
      self.requests = []

   def __call__(self, request):
      self.requests.append(request)
      return self.respond(request)


def json_reply(body, status=200):
   return lambda request: httpx.Response(status, headers=JSON_HEADERS, content=json.dumps(body).encode())


def raise_every_time(error_type):
   def respond(request):
      raise error_type("network down", request=request)

   return respond


def redirect_first_request_to(location):
   def respond(request):
      is_first_request = request.url.host in CITYMAPPER_HOSTS and "hop" not in request.url.params
      if is_first_request:
         return httpx.Response(302, headers={"location": location})

      return httpx.Response(200, headers=JSON_HEADERS, content=b"{\"ok\": 1}")

   return respond


def build_transport(tmp_path, handler, session=None, sleeps=None, run_id=None, command=None):
   recorded_sleeps = sleeps if sleeps is not None else []
   client = httpx.Client(transport=httpx.MockTransport(handler))
   pacer = Pacer(tmp_path / "state" / "pacer.json", minimum_gap=0, sleeper=recorded_sleeps.append)
   transport = Transport(session or Session(), pacer, tmp_path / "logs", client=client, sleeper=recorded_sleeps.append, run_id=run_id, command=command)
   return transport, pacer


def log_lines(tmp_path):
   log_file = tmp_path / "logs" / "requests-{0}.jsonl".format(datetime.now().strftime("%Y-%m-%d"))
   return [json.loads(line) for line in log_file.read_text().splitlines()]


def test_form_json_request_is_form_encoded_with_a_json_body(tmp_path):
   handler = RecordingHandler(json_reply({"results": []}))
   transport, _ = build_transport(tmp_path, handler)
   search_body = {"query": "Harbour", "region_id": "zz-portvale"}

   transport.send(Request(endpoints.SEARCH, form_json=search_body, headers={"Citymapper-Region": "zz-portvale"}))

   sent = handler.requests[0]
   assert sent.method == "POST"
   assert sent.url.path == "/api/4/searchpost"
   assert sent.headers["content-type"].startswith("application/x-www-form-urlencoded")
   assert json.loads(sent.content) == search_body
   assert sent.headers["citymapper-region"] == "zz-portvale"


def test_json_body_request_is_sent_as_json(tmp_path):
   handler = RecordingHandler(json_reply({"journey_times": []}))
   transport, _ = build_transport(tmp_path, handler)

   transport.send(Request(endpoints.JOURNEY_TIMES, query={"region_id": "zz-portvale"}, json_body={"signatures": ["sig"]}))

   sent = handler.requests[0]
   assert sent.headers["content-type"].startswith("application/json")
   assert json.loads(sent.content) == {"signatures": ["sig"]}
   assert sent.url.params["region_id"] == "zz-portvale"


def test_cookies_go_only_to_signed_in_endpoints(tmp_path):
   handler = RecordingHandler(json_reply({"ok": 1}))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   transport.send(Request(endpoints.TRAVEL_TIME, query={"startcoord": "10.5,20.5"}))
   transport.send(Request(endpoints.USER_DATA))

   public_request, signed_in_request = handler.requests
   assert "cookie" not in public_request.headers
   assert "sessionid=" + SIGNED_IN_COOKIES["sessionid"] in signed_in_request.headers["cookie"]


def test_site_cookies_never_go_to_the_turnstile_host(tmp_path):
   handler = RecordingHandler(json_reply({"ttl": 60}))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   transport.send(Request(endpoints.PASS_SESSION_TTL))

   sent = handler.requests[0]
   assert sent.url.host == "turnstile-api.citymapper.com"
   assert "cookie" not in sent.headers


def test_csrf_header_goes_only_to_csrf_endpoints(tmp_path):
   handler = RecordingHandler(json_reply({"ok": 1}))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   transport.send(Request(endpoints.USER_DATA))
   transport.send(Request(endpoints.CITY_VOTE, json_body={"city_slug": "newtown", "email": "someone@example.test"}))

   user_request, vote_request = handler.requests
   assert "x-csrftoken" not in user_request.headers
   assert vote_request.headers["x-csrftoken"] == SIGNED_IN_COOKIES["csrftoken"]


def test_get_retries_transport_errors_then_succeeds(tmp_path):
   attempts = []

   def flaky(request):
      attempts.append(request)

      if len(attempts) < 3:
         raise httpx.ConnectError("connection refused", request=request)

      return httpx.Response(200, headers=JSON_HEADERS, content=b"{\"travel_time_minutes\": 19}")

   sleeps = []
   transport, _ = build_transport(tmp_path, flaky, sleeps=sleeps)

   body = transport.send(Request(endpoints.TRAVEL_TIME))

   assert body == {"travel_time_minutes": 19}
   assert len(attempts) == 3
   assert sleeps == [5, 10]


def test_get_gives_up_after_three_attempts(tmp_path):
   handler = RecordingHandler(raise_every_time(httpx.ReadTimeout))
   transport, _ = build_transport(tmp_path, handler)

   with pytest.raises(TransportError):
      transport.send(Request(endpoints.TRAVEL_TIME))

   assert len(handler.requests) == 3


def test_post_is_not_retried(tmp_path):
   handler = RecordingHandler(raise_every_time(httpx.ConnectError))
   sleeps = []
   transport, _ = build_transport(tmp_path, handler, sleeps=sleeps)

   with pytest.raises(TransportError):
      transport.send(Request(endpoints.SEARCH, form_json={"query": "x"}))

   assert len(handler.requests) == 1
   assert sleeps == []


def test_a_write_that_times_out_warns_it_may_have_landed(tmp_path):
   handler = RecordingHandler(raise_every_time(httpx.ReadTimeout))
   transport, _ = build_transport(tmp_path, handler)

   with pytest.raises(TransportError) as caught:
      transport.send(Request(endpoints.SEARCH, form_json={"query": "x"}))

   assert "may have reached Citymapper" in caught.value.message
   assert caught.value.detail["write_may_have_landed"] is True


def test_a_write_that_never_connected_keeps_the_plain_network_error(tmp_path):
   handler = RecordingHandler(raise_every_time(httpx.ConnectTimeout))
   transport, _ = build_transport(tmp_path, handler)

   with pytest.raises(TransportError) as caught:
      transport.send(Request(endpoints.SEARCH, form_json={"query": "x"}))

   assert caught.value.message.startswith("Network error")
   assert "write_may_have_landed" not in caught.value.detail


def test_a_read_that_times_out_keeps_the_plain_network_error(tmp_path):
   handler = RecordingHandler(raise_every_time(httpx.ReadTimeout))
   transport, _ = build_transport(tmp_path, handler)

   with pytest.raises(TransportError) as caught:
      transport.send(Request(endpoints.TRAVEL_TIME))

   assert caught.value.message.startswith("Network error")
   assert "write_may_have_landed" not in caught.value.detail


def test_the_default_client_fails_a_dead_connection_fast(tmp_path):
   transport = Transport(Session(), Pacer(tmp_path / "pacer.json"), tmp_path / "logs")

   timeout = transport.client.timeout

   assert timeout.connect == 8.0
   assert timeout.read == 20.0


def test_a_login_page_on_a_signed_in_read_is_session_expired(tmp_path):
   login_page = lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<form action='/login'></form>")
   transport, _ = build_transport(tmp_path, RecordingHandler(login_page), session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   with pytest.raises(SessionExpired):
      transport.send(Request(endpoints.USER_DATA))


def test_a_bot_check_on_a_200_halts_the_pacer(tmp_path):
   bot_check = lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html><title>px-captcha</title></html>")
   handler = RecordingHandler(bot_check)
   transport, pacer = build_transport(tmp_path, handler)

   with pytest.raises(ChallengeRequired):
      transport.send(Request(endpoints.TRAVEL_TIME))

   assert pacer.status()["halt_reason"] == "challenge"

   with pytest.raises(ChallengeRequired):
      transport.send(Request(endpoints.TRAVEL_TIME))

   assert len(handler.requests) == 1


@pytest.mark.parametrize("location", ["/login?next=/api/1/identity/user_data", "/accounts/sign-in"])
def test_a_redirect_to_a_login_path_on_a_signed_in_read_is_session_expired(tmp_path, location):
   handler = RecordingHandler(redirect_first_request_to(location))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   with pytest.raises(SessionExpired):
      transport.send(Request(endpoints.USER_DATA))

   assert len(handler.requests) == 1


def test_an_unwritable_log_directory_does_not_fail_a_sent_request(tmp_path):
   blocked_logs = tmp_path / "logs"
   blocked_logs.write_text("a file where the logs directory should be")
   transport, _ = build_transport(tmp_path, RecordingHandler(json_reply({"ok": 1})))

   body = transport.send(Request(endpoints.SEARCH, form_json={"query": "x"}))

   assert body == {"ok": 1}


def test_the_cli_reports_a_local_file_failure_as_json(tmp_path, monkeypatch, capsys):
   monkeypatch.setenv("CITYMAPPER_ROOT", str(tmp_path / "cli-root"))
   monkeypatch.setattr(cli, "run_command", lambda command, context, values: (_ for _ in ()).throw(PermissionError(13, "Permission denied")))

   exit_code = cli.main(["reverse-geocode", "--lat", "51.5", "--lng", "-0.12"])

   error = json.loads(capsys.readouterr().err)
   assert exit_code == 18
   assert error["class"] == "LocalFileError"
   assert "may already have been sent" in error["message"]
   assert error["detail"]["error"] == "PermissionError"


@pytest.mark.parametrize("endpoint", [endpoints.CREATE_TRIP_URL, endpoints.CREATE_SHORT_URL])
def test_a_get_that_writes_is_sent_once_on_a_timeout(tmp_path, endpoint):
   handler = RecordingHandler(raise_every_time(httpx.ReadTimeout))
   sleeps = []
   transport, _ = build_transport(tmp_path, handler, sleeps=sleeps)

   with pytest.raises(TransportError):
      transport.send(Request(endpoint, query={"signature": "sig"}))

   assert len(handler.requests) == 1
   assert sleeps == []


SESSION_HEADER_CASES = {
   "pass read with Session-Id": lambda: Request(endpoints.PASS_SESSION_TTL, headers={"Session-Id": SIGNED_IN_COOKIES["sessionid"], "User-Device": SIGNED_IN_COOKIES["uid"]}),
   "signed-in read with cookies": lambda: Request(endpoints.USER_DATA),
   "write with X-CSRFToken": lambda: Request(endpoints.CITY_VOTE, json_body={"city_slug": "newtown", "email": "someone@example.test"}),
}


@pytest.mark.parametrize("case", sorted(SESSION_HEADER_CASES))
def test_a_redirect_to_another_host_is_refused_before_it_is_sent(tmp_path, case):
   handler = RecordingHandler(redirect_first_request_to(FOREIGN_LOCATION))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   with pytest.raises(ContractBroken) as refused:
      transport.send(SESSION_HEADER_CASES[case]())

   assert refused.value.detail["status"] == 302
   assert len(handler.requests) == 1
   assert {sent.url.host for sent in handler.requests} <= CITYMAPPER_HOSTS
   assert log_lines(tmp_path)[0]["class"] == "ContractBroken"


def test_a_public_read_follows_a_redirect_to_another_host_without_credentials(tmp_path):
   handler = RecordingHandler(redirect_first_request_to(FOREIGN_LOCATION))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   transport.send(Request(endpoints.TRAVEL_TIME))

   foreign_hops = [sent for sent in handler.requests if sent.url.host not in CITYMAPPER_HOSTS]
   assert len(handler.requests) == 2
   assert len(foreign_hops) == 1
   assert not {name.lower() for name in foreign_hops[0].headers} & {"cookie", "x-csrftoken", "session-id", "user-device"}


def test_a_write_is_not_followed_even_to_the_same_host(tmp_path):
   handler = RecordingHandler(redirect_first_request_to("/cities/vote_submit/?hop=1"))
   transport, _ = build_transport(tmp_path, handler, session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   with pytest.raises(ContractBroken):
      transport.send(Request(endpoints.CITY_VOTE, json_body={"city_slug": "newtown", "email": "someone@example.test"}))

   assert len(handler.requests) == 1


def test_a_same_host_redirect_on_a_read_is_paced_and_logged_per_hop(tmp_path):
   handler = RecordingHandler(redirect_first_request_to("/api/1/traveltime?hop=1"))
   transport, _ = build_transport(tmp_path, handler)

   body = transport.send(Request(endpoints.TRAVEL_TIME))

   assert body == {"ok": 1}
   assert [sent.url.params.get("hop") for sent in handler.requests] == [None, "1"]
   assert transport.request_count == 2
   assert [(line["status"], line["class"]) for line in log_lines(tmp_path)] == [(302, "Redirect"), (200, None)]


def test_log_lines_carry_the_run_the_command_and_the_attempt(tmp_path):
   attempts = []

   def flaky(request):
      attempts.append(request)

      if len(attempts) < 2:
         raise httpx.ConnectError("connection refused", request=request)

      return httpx.Response(200, headers=JSON_HEADERS, content=b"{\"ok\": 1}")

   transport, _ = build_transport(tmp_path, flaky, run_id="run-7f3a", command="get-travel-time")

   transport.send(Request(endpoints.TRAVEL_TIME))

   lines = log_lines(tmp_path)
   assert [(line["run"], line["command"], line["attempt"]) for line in lines] == [("run-7f3a", "get-travel-time", 1), ("run-7f3a", "get-travel-time", 2)]


def test_the_cli_tags_its_log_lines_and_its_error_with_the_run_id(tmp_path, monkeypatch, capsys):
   site_root = tmp_path / "cli-root"
   monkeypatch.setenv("CITYMAPPER_ROOT", str(site_root))
   monkeypatch.setenv(cli.RUN_ID_VARIABLE, "live-check-42")
   monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: httpx.Response(404, headers=JSON_HEADERS, content=b"{}"))

   exit_code = cli.main(["reverse-geocode", "--lat", "51.5", "--lng", "-0.12"])

   error = json.loads(capsys.readouterr().err)
   log_file = site_root / "var" / "logs" / "requests-{0}.jsonl".format(datetime.now().strftime("%Y-%m-%d"))
   lines = [json.loads(line) for line in log_file.read_text().splitlines()]
   assert exit_code == 17
   assert error["detail"]["run"] == "live-check-42"
   assert [(line["run"], line["command"]) for line in lines] == [("live-check-42", "reverse-geocode")]


def test_building_the_context_leaves_httpx_unimported(tmp_path):
   probe = "import sys\nfrom citymapper_client import cli\ncli.Context.build()\nprint(sorted(name for name in sys.modules if name.split(\".\")[0] == \"httpx\"))"
   environment = {**os.environ, "CITYMAPPER_ROOT": str(tmp_path / "probe-root")}

   finished = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=environment, check=True)

   assert finished.stdout.strip() == "[]"


def test_429_halts_the_pacer_and_blocks_the_next_request(tmp_path):
   handler = RecordingHandler(json_reply({}, status=429))
   transport, pacer = build_transport(tmp_path, handler)

   with pytest.raises(RateLimited):
      transport.send(Request(endpoints.TRAVEL_TIME))

   status = pacer.status()
   assert status["halted"] is True
   assert status["halt_reason"] == "throttle"

   with pytest.raises(RateLimited):
      transport.send(Request(endpoints.TRAVEL_TIME))

   assert len(handler.requests) == 1


def test_challenge_page_halts_the_pacer_with_reason_challenge(tmp_path):
   challenge = lambda request: httpx.Response(403, headers={"content-type": "text/html"}, content=b"<html><title>Just a moment...</title></html>")
   transport, pacer = build_transport(tmp_path, RecordingHandler(challenge))

   with pytest.raises(ChallengeRequired):
      transport.send(Request(endpoints.TRAVEL_TIME))

   assert pacer.status()["halt_reason"] == "challenge"


def test_every_request_appends_one_log_line_without_cookie_values(tmp_path):
   def reply(request):
      is_missing_page = request.url.path == "/api/1/routeinfo"

      if is_missing_page:
         return httpx.Response(404, headers=JSON_HEADERS, content=b"{}")

      return httpx.Response(200, headers=JSON_HEADERS, content=b"{\"ok\": 1}")

   transport, _ = build_transport(tmp_path, RecordingHandler(reply), session=Session(cookies=dict(SIGNED_IN_COOKIES)))

   transport.send(Request(endpoints.USER_DATA))
   transport.send(Request(endpoints.TRAVEL_TIME))

   with pytest.raises(NotFound):
      transport.send(Request(endpoints.ROUTE_INFO, query={"route": "metro-a"}))

   lines = log_lines(tmp_path)
   log_text = "".join(json.dumps(line) for line in lines)
   assert [line["finding"] for line in lines] == ["identity-user-data", "traveltime", "routeinfo1"]
   assert [line["status"] for line in lines] == [200, 200, 404]
   assert lines[2]["class"] == "NotFound"

   for cookie_value in SIGNED_IN_COOKIES.values():
      assert cookie_value not in log_text
