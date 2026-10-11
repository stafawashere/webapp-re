import json
from dataclasses import dataclass, field

import httpx
import pytest

from citymapper_client import registry
from citymapper_client.capabilities import account
from citymapper_client.errors import SessionExpired, UsageError
from citymapper_client.pacing import Pacer
from citymapper_client.session import Session
from citymapper_client.transport import Transport

from support import SIGNED_IN_COOKIES, assert_valid, load_fixture, signed_in_session

SCHEMAS = registry.load_schemas()
SIGNATURE = load_fixture("journeys.json")["journeys"][0]["signature"]
TURNSTILE = "https://turnstile-api.citymapper.com"
PASS_ARGUMENTS = {"provider": "stripe", "payment_method_id": "pm_test_fake_0001", "use_web_session_id": True}


@dataclass(frozen=True)
class WriteCase:
   arguments: dict
   finding: str
   method: str
   url: str
   reply: object = field(default_factory=dict)
   lookups: dict = field(default_factory=dict)


WRITE_CASES = {
   "save-place": WriteCase({"city": "portvale", "near": "10.5,20.5", "name": "Studio", "role": "work"}, "identity-places-create", "POST", "https://citymapper.com/api/1/identity/places", {"place_id": "pl-1", "name": "Studio"}),
   "update-place": WriteCase({"id": "pl-77", "name": "Studio Two"}, "identity-places-update", "PUT", "https://citymapper.com/api/1/identity/places/pl-77", {"place_id": "pl-77"}),
   "remove-place": WriteCase({"id": "pl-77"}, "identity-places-delete", "DELETE", "https://citymapper.com/api/1/identity/places/pl-77"),
   "add-favourite": WriteCase({"city": "portvale", "stop": "harbour-sq"}, "identity-favorites-create", "POST", "https://citymapper.com/api/1/identity/favorites", {"favorite_id": "fav-1"}, {"stopinfo": load_fixture("stopinfo_metro.json")}),
   "remove-favourite": WriteCase({"id": "fav-9"}, "identity-favorites-delete", "DELETE", "https://citymapper.com/api/1/identity/favorites/fav-9"),
   "save-journey": WriteCase({"city": "portvale", "signature": SIGNATURE}, "identity-save-journey", "POST", "https://citymapper.com/api/1/identity/documents/SavedJourney", {"document_id": "doc-1"}),
   "remove-saved-journey": WriteCase({"document_id": "doc-5"}, "identity-delete-journey", "DELETE", "https://citymapper.com/api/1/identity/documents/SavedJourney/doc-5"),
   "update-profile": WriteCase({"first_name": "Ada"}, "identity-update-user", "POST", "https://citymapper.com/api/1/identity/update_user", {"first_name": "Ada"}),
   "sign-out": WriteCase({}, "identity-sessions-delete", "DELETE", "https://citymapper.com/api/1/identity/sessions"),
   "share-journey": WriteCase({"city": "portvale", "signature": SIGNATURE}, "createtripurl", "GET", "https://citymapper.com/api/1/createtripurl", {"url": "https://citymapper.com/trip/Tfake01"}),
   "create-go-link": WriteCase({"city": "portvale", "place": "10.5,20.5", "title": "Meet here"}, "createshorturl", "GET", "https://citymapper.com/api/1/createshorturl", {"slug": "gq7d"}),
   "vote-for-city": WriteCase({"city_slug": "newtown", "email": "someone@example.test"}, "city-vote", "POST", "https://citymapper.com/cities/vote_submit/"),
   "pass-set-default-payment": WriteCase(PASS_ARGUMENTS, "turnstile-setdefaultpaymentmethod", "POST", TURNSTILE + "/web/1/setdefaultpaymentmethod"),
   "pass-add-payment-method": WriteCase(PASS_ARGUMENTS, "turnstile-addpaymentmethod", "POST", TURNSTILE + "/web/1/addpaymentmethod"),
   "pass-remove-payment-method": WriteCase(PASS_ARGUMENTS, "turnstile-deletepaymentmethod", "POST", TURNSTILE + "/web/1/deletepaymentmethod"),
   "pass-remove-all-payment-methods": WriteCase({"provider": "stripe", "use_web_session_id": True}, "turnstile-deleteallpaymentmethods", "POST", TURNSTILE + "/web/1/deleteallpaymentmethods"),
}

SESSION_WRITES = sorted(name for name in WRITE_CASES if SCHEMAS[name]["live_policy"] == "session")
PUBLIC_WRITES = sorted(name for name in WRITE_CASES if SCHEMAS[name]["live_policy"] == "public")


def approved_arguments(context, name, arguments):
   dry_run = registry.FUNCTIONS[name](context, {**arguments, "dry_run": True})
   return {**arguments, "yes": True, "confirm": dry_run["confirm"]}


def run_write(make_context, name, session=None, **flags):
   case = WRITE_CASES[name]
   context, fake = make_context({**case.lookups, case.finding: case.reply}, session=session)
   arguments = {**case.arguments, **flags}
   sends_for_real = flags.get("yes") and not flags.get("dry_run")

   if sends_for_real:
      arguments = approved_arguments(context, name, arguments)

   output = registry.FUNCTIONS[name](context, arguments)
   return output, fake


def assert_sent_nothing(fake, name):
   assert fake.findings == list(WRITE_CASES[name].lookups)


def test_cases_cover_every_remote_write_command():
   remote_writes = {name for name, record in SCHEMAS.items() if record["kind"] == "write" and record["live_policy"] != "local"}

   assert set(WRITE_CASES) == remote_writes


@pytest.mark.parametrize("name", sorted(WRITE_CASES))
def test_dry_run_describes_the_request_and_sends_nothing(make_context, name):
   output, fake = run_write(make_context, name, session=signed_in_session(), dry_run=True, yes=True)

   case = WRITE_CASES[name]
   assert output["dry_run"] is True
   assert output["request"]["method"] == case.method
   assert output["request"]["url"].split("?")[0] == case.url
   assert output["request"]["finding"] == case.finding
   assert_sent_nothing(fake, name)


DRY_RUN_SCHEMA_CASES = sorted(WRITE_CASES)


@pytest.mark.parametrize("name", DRY_RUN_SCHEMA_CASES)
def test_dry_run_output_matches_its_schema(make_context, name):
   output, _ = run_write(make_context, name, session=signed_in_session(), dry_run=True)

   assert_valid(output, SCHEMAS[name]["output_schema"])


@pytest.mark.parametrize("name", sorted(WRITE_CASES))
def test_without_yes_is_a_usage_error_and_sends_nothing(make_context, name):
   case = WRITE_CASES[name]
   context, fake = make_context({**case.lookups, case.finding: case.reply}, session=signed_in_session())

   with pytest.raises(UsageError) as caught:
      registry.FUNCTIONS[name](context, dict(case.arguments))

   assert caught.value.detail["request"]["method"] == case.method
   assert_sent_nothing(fake, name)


@pytest.mark.parametrize("name", SESSION_WRITES)
def test_account_write_without_a_session_is_session_expired_and_sends_nothing(make_context, name):
   case = WRITE_CASES[name]
   context, fake = make_context({**case.lookups, case.finding: case.reply})

   with pytest.raises(SessionExpired):
      registry.FUNCTIONS[name](context, {**case.arguments, "yes": True})

   assert_sent_nothing(fake, name)


@pytest.mark.parametrize("name", sorted(WRITE_CASES))
def test_approved_write_sends_exactly_one_request_to_its_endpoint(make_context, name):
   case = WRITE_CASES[name]

   output, fake = run_write(make_context, name, session=signed_in_session(), yes=True)

   writes = [request for request in fake.requests if request.endpoint.finding not in case.lookups]
   assert len(writes) == 1
   assert writes[0].endpoint.finding == case.finding
   assert writes[0].endpoint.method == case.method
   assert writes[0].url.split("?")[0] == case.url
   assert_valid(output, SCHEMAS[name]["output_schema"])


@pytest.mark.parametrize("name", PUBLIC_WRITES)
def test_public_write_with_yes_needs_no_session(make_context, name):
   output, fake = run_write(make_context, name, yes=True)

   assert fake.findings[-1] == WRITE_CASES[name].finding


def sent_write(make_context, name, **argument_overrides):
   case = WRITE_CASES[name]
   context, fake = make_context({**case.lookups, case.finding: case.reply, "routeinfo1": load_fixture("routeinfo1.json")}, session=signed_in_session())
   registry.FUNCTIONS[name](context, approved_arguments(context, name, {**case.arguments, **argument_overrides}))
   return fake.only_request(case.finding)


def test_save_place_body_has_region_coords_name_and_role(make_context):
   body = sent_write(make_context, "save-place").json_body

   assert body["region_code"] == "zz-portvale"
   assert body["coords"] == [10.5, 20.5]
   assert body["name"] == "Studio"
   assert body["role"] == "work"


def test_update_place_body_has_only_the_changed_fields(make_context):
   body = sent_write(make_context, "update-place").json_body

   assert body == {"name": "Studio Two"}


def test_add_favourite_for_a_station_uses_target_type_2(make_context):
   body = sent_write(make_context, "add-favourite").json_body

   assert body["target_type"] == 2
   assert body["target_id"] == "MetroHarbourSq"
   assert body["region_code"] == "zz-portvale"
   assert body["coords"] == [10.512, 20.488]


def test_add_favourite_for_a_bus_stop_uses_target_type_1(make_context):
   case = WRITE_CASES["add-favourite"]
   context, fake = make_context({"stopinfo": load_fixture("stopinfo_bus.json"), case.finding: case.reply}, session=signed_in_session())
   registry.FUNCTIONS["add-favourite"](context, approved_arguments(context, "add-favourite", {"city": "portvale", "stop": "pier-st-mill-ln"}))

   body = fake.only_request(case.finding).json_body

   assert body["target_type"] == 1
   assert body["target_id"] == "PVBus_4471"


def test_add_favourite_for_a_line_uses_target_type_3(make_context):
   request = sent_write(make_context, "add-favourite", stop=None, line="metro-a")

   assert request.json_body["target_type"] == 3
   assert request.json_body["target_id"] == "A"
   assert request.json_body["name"] == "Airport - Harbour"


def test_add_favourite_needs_exactly_one_target(make_context):
   context, fake = make_context(session=signed_in_session())

   with pytest.raises(UsageError):
      registry.FUNCTIONS["add-favourite"](context, {"city": "portvale", "stop": "harbour-sq", "line": "metro-a", "yes": True})

   assert fake.requests == []


def test_save_journey_sends_the_signature_as_a_document(make_context):
   body = sent_write(make_context, "save-journey").json_body

   document = json.loads(body["document_data"])
   assert document["signature"] == SIGNATURE
   assert document["region_id"] == "zz-portvale"


def test_share_journey_sends_signature_and_region(make_context):
   query = sent_write(make_context, "share-journey").query

   assert query == {"signature": SIGNATURE, "trip_region_id": "zz-portvale"}


def test_vote_for_city_posts_the_slug_and_email(make_context):
   body = sent_write(make_context, "vote-for-city").json_body

   assert body == {"city_slug": "newtown", "email": "someone@example.test"}


def recording_transport(tmp_path, session, sent_requests):
   def reply_ok(request):
      sent_requests.append(request)
      return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}")

   client = httpx.Client(transport=httpx.MockTransport(reply_ok))
   pacer = Pacer(tmp_path / "pacer.json", minimum_gap=0, sleeper=lambda seconds: None)
   return Transport(session, pacer, tmp_path / "logs", client=client, sleeper=lambda seconds: None)


def test_approved_vote_for_city_sends_the_session_cookie_and_the_csrf_header(make_context, tmp_path):
   session = signed_in_session()
   context, _ = make_context(session=session)
   sent_requests = []
   context.transport = recording_transport(tmp_path, session, sent_requests)

   registry.FUNCTIONS["vote-for-city"](context, approved_arguments(context, "vote-for-city", WRITE_CASES["vote-for-city"].arguments))

   assert len(sent_requests) == 1
   assert "csrftoken=" + SIGNED_IN_COOKIES["csrftoken"] in sent_requests[0].headers["cookie"]
   assert sent_requests[0].headers["x-csrftoken"] == SIGNED_IN_COOKIES["csrftoken"]


def test_vote_for_city_without_a_csrftoken_sends_nothing(make_context):
   session_without_token = Session(cookies={"sessionid": SIGNED_IN_COOKIES["sessionid"]})
   context, fake = make_context(session=session_without_token)

   with pytest.raises(SessionExpired):
      registry.FUNCTIONS["vote-for-city"](context, {**WRITE_CASES["vote-for-city"].arguments, "yes": True})

   assert fake.requests == []


@pytest.mark.parametrize("name", ["pass-set-default-payment", "pass-add-payment-method", "pass-remove-payment-method", "pass-remove-all-payment-methods"])
def test_pass_writes_send_device_and_session_headers(make_context, name):
   request = sent_write(make_context, name)

   assert request.headers == {"User-Device": SIGNED_IN_COOKIES["uid"], "Session-Id": SIGNED_IN_COOKIES["sessionid"]}
   assert request.json_body["payment_provider_id"] == "stripe"


def test_pass_payment_method_id_is_sent_only_where_needed(make_context):
   with_method = sent_write(make_context, "pass-remove-payment-method").json_body
   without_method = sent_write(make_context, "pass-remove-all-payment-methods").json_body

   assert with_method["payment_method_id"] == "pm_test_fake_0001"
   assert "payment_method_id" not in without_method


@pytest.mark.parametrize("name", sorted(WRITE_CASES))
def test_yes_without_confirm_is_a_usage_error_and_sends_nothing(make_context, name):
   case = WRITE_CASES[name]
   context, fake = make_context({**case.lookups, case.finding: case.reply}, session=signed_in_session())

   with pytest.raises(UsageError):
      registry.FUNCTIONS[name](context, {**case.arguments, "yes": True})

   assert_sent_nothing(fake, name)


def search_reply(name, coords):
   return {"results": [{"id": "citymapper:" + name, "name": name, "coords": coords, "type": "station", "source": "citymapper_stations"}]}


def test_a_place_that_resolves_differently_after_the_dry_run_sends_nothing(make_context):
   search_replies = iter([search_reply("Harbour Sq", [10.512, 20.488]), search_reply("Harbour Sq East", [10.6, 20.6])])
   context, fake = make_context({"searchpost": lambda request: next(search_replies), "identity-places-create": {}}, session=signed_in_session())
   arguments = {"city": "portvale", "near": "Harbour Sq", "name": "Studio"}
   approved = approved_arguments(context, "save-place", arguments)

   with pytest.raises(UsageError) as caught:
      registry.FUNCTIONS["save-place"](context, approved)

   assert caught.value.detail["request"]["body"]["coords"] == [10.6, 20.6]
   assert "identity-places-create" not in fake.findings


@pytest.mark.parametrize("name", ["save-place", "save-journey"])
def test_confirm_survives_the_clock_moving_between_dry_run_and_send(make_context, monkeypatch, name):
   case = WRITE_CASES[name]
   context, fake = make_context({**case.lookups, case.finding: case.reply}, session=signed_in_session())
   clock = iter([1760000000, 1760000090])
   monkeypatch.setattr(account.time, "time", lambda: next(clock))

   registry.FUNCTIONS[name](context, approved_arguments(context, name, case.arguments))

   assert fake.findings[-1] == case.finding


def test_a_refused_send_does_not_reveal_the_digest_it_wanted(make_context):
   case = WRITE_CASES["update-profile"]
   context, fake = make_context({case.finding: case.reply}, session=signed_in_session())
   wanted_digest = registry.FUNCTIONS["update-profile"](context, {**case.arguments, "dry_run": True})["confirm"]

   for confirm in (None, "000000000000"):
      with pytest.raises(UsageError) as caught:
         registry.FUNCTIONS["update-profile"](context, {**case.arguments, "yes": True, "confirm": confirm})

      assert wanted_digest not in json.dumps(caught.value.as_dict())

   assert fake.requests == []


PASS_COMMANDS_WITHOUT_OPT_IN = {
   "pass-account": {},
   "pass-session-time": {},
   "pass-set-default-payment": {"provider": "stripe", "payment_method_id": "pm_test_fake_0001", "yes": True},
   "pass-add-payment-method": {"provider": "stripe", "payment_method_id": "pm_test_fake_0001", "yes": True},
   "pass-remove-payment-method": {"provider": "stripe", "payment_method_id": "pm_test_fake_0001", "yes": True},
   "pass-remove-all-payment-methods": {"provider": "stripe", "yes": True},
}


@pytest.mark.parametrize("name", sorted(PASS_COMMANDS_WITHOUT_OPT_IN))
def test_pass_commands_send_nothing_without_the_web_session_id_opt_in(make_context, name):
   context, fake = make_context(session=signed_in_session())

   with pytest.raises(UsageError) as caught:
      registry.FUNCTIONS[name](context, dict(PASS_COMMANDS_WITHOUT_OPT_IN[name]))

   assert "--use-web-session-id" in caught.value.message
   assert fake.requests == []


def approved_go_link(make_context, reply, **argument_overrides):
   case = WRITE_CASES["create-go-link"]
   context, _ = make_context({case.finding: reply}, session=signed_in_session())
   arguments = approved_arguments(context, "create-go-link", {**case.arguments, **argument_overrides})
   return registry.FUNCTIONS["create-go-link"](context, arguments)


def test_create_go_link_warns_when_the_title_and_message_are_not_echoed(make_context):
   output = approved_go_link(make_context, {"slug": "gq7d"}, message="See you at 7")

   assert output["title"] is None
   assert output["message"] is None
   assert "title and message" in output["warning"]
   assert "open-go-link --slug gq7d" in output["warning"]
   assert_valid(output, SCHEMAS["create-go-link"]["output_schema"])


def test_create_go_link_reports_the_echoed_title_without_a_warning(make_context):
   output = approved_go_link(make_context, {"slug": "gq7d", "title": "Meet here"})

   assert output["title"] == "Meet here"
   assert output["warning"] is None
