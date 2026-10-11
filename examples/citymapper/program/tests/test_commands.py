import io
import json
import re
import stat
import time

import pytest

from citymapper_client import cli, endpoints, registry
from citymapper_client.capabilities import journeys, misc
from citymapper_client.capabilities.departures import bus_departures
from citymapper_client.config import ROUTE_STATUS_MAX_AGE_SECONDS, STOP_CACHE_MAX_AGE_SECONDS, site_paths
from citymapper_client.context import Context
from citymapper_client.errors import ContractBroken, NotFound, SessionExpired, UsageError
from citymapper_client.session import COOKIE_KEY, read_env_file
from citymapper_client.transport import Request

from support import assert_valid, load_fixture, load_text_fixture, signed_in_session
from test_transport import RecordingHandler, build_transport, json_reply

SCHEMAS = registry.load_schemas()
COMMANDS = registry.build_registry()
WRITE_COMMANDS = {name for name, record in SCHEMAS.items() if record["kind"] == "write" and record["live_policy"] != "local"}
RETIRED_COMMANDS = {
   "plan-vehicle-hire": journeys.RETIRED_VEHICLE_HIRE,
   "get-shared-eta": journeys.RETIRED_ETA,
   "get-weather": misc.RETIRED_WEATHER,
   "get-transit-score": misc.RETIRED_TRANSIT_SCORE,
}

INSIDE_START = "10.5,20.5"
INSIDE_END = "10.6,20.7"
JOURNEY_SIGNATURE = load_fixture("journeys.json")["journeys"][0]["signature"]

GETTRIP_BODY = {"signature": JOURNEY_SIGNATURE}
GETSHORTURL_BODY = {"endname": "Lantern Market", "endcoord": "10.523,20.611", "endaddress": "Quay Rd, Portvale", "slug": "k3x9"}
USER_DATA_BODY = {"user_id": "u-5521", "first_name": "Robin", "is_interested_in_pass": False}
PLACES_LIST_BODY = {"items": [
   {"place_id": 77, "name": "Studio", "role": "work", "address": "Mill Ln, Portvale", "coords": [10.6, 20.7], "region_code": "zz-portvale"},
   {"place_id": 78, "name": "Gran's", "role": "", "address": None, "coords": "10.55,20.65", "region_code": "zz-portvale"},
]}
FAVOURITES_LIST_BODY = {"items": [
   {"favorite_id": 9, "target_type_code": 2, "target_id": "MetroHarbourSq", "name": "Harbour Sq", "region_code": "zz-portvale"},
   {"favorite_id": 10, "target_type_code": 3, "target_id": "L9", "name": "L9", "region_code": "zz-lakeshore"},
]}
PASS_USER_INFO_BODY = {"payment_methods": [], "default_payment_method_id": None}
PASS_SESSION_TTL_BODY = {"seconds_remaining": 3600}

READ_CASES = {
   "list-cities": ({}, {}),
   "get-city": ({"city": "portvale"}, {}),
   "list-brands": ({"city": "portvale"}, {"resource-brand-directory": load_fixture("brand_directory.json")}),
   "search-places": ({"city": "portvale", "query": "Harbour"}, {"searchpost": load_fixture("searchpost.json")}),
   "resolve-place": ({"city": "portvale", "id": "google:ChIJFakePlaceAlpha"}, {"placeresolve": load_fixture("placeresolve.json")}),
   "reverse-geocode": ({"lat": 10.5231, "lng": 20.6109}, {"geocode": load_fixture("geocode.json")}),
   "plan-journey": ({"city": "portvale", "from": INSIDE_START, "to": INSIDE_END, "with_paths": True}, {"journeys": load_fixture("journeys.json")}),
   "plan-walk": ({"city": "portvale", "from": INSIDE_START, "to": INSIDE_END}, {"walk7": load_fixture("walk7.json")}),
   "plan-cycle": ({"city": "portvale", "from": INSIDE_START, "to": INSIDE_END}, {"cycle": load_fixture("cycle.json")}),
   "plan-cab": ({"city": "portvale", "from": INSIDE_START, "to": INSIDE_END}, {"taxi": load_fixture("taxi.json")}),
   "get-journey-times": ({"city": "portvale", "signatures": [JOURNEY_SIGNATURE]}, {"journeytimes": load_fixture("journeytimes.json")}),
   "get-journey": ({"city": "portvale", "signature": JOURNEY_SIGNATURE, "with_paths": True}, {"refreshjourneys": load_fixture("refreshjourneys.json")}),
   "open-trip-link": ({"slug": "Tq7xk2", "city": "portvale"}, {"gettrip": GETTRIP_BODY, "refreshjourneys": load_fixture("refreshjourneys.json")}),
   "get-travel-time": ({"city": "portvale", "from": INSIDE_START, "to": INSIDE_END}, {"traveltime": load_fixture("traveltime.json")}),
   "find-nearby": ({"city": "portvale", "near": INSIDE_START, "mode": "metro"}, {"nearby3": load_fixture("nearby3.json")}),
   "get-stop": ({"city": "portvale", "stop": "harbour-sq"}, {"stopinfo": load_fixture("stopinfo_metro.json")}),
   "get-departures": ({"city": "portvale", "stop": "harbour-sq"}, {"stopinfo": load_fixture("stopinfo_metro.json"), "departures-metro": load_fixture("departures_metro.json")}),
   "get-stop-schedule": ({"city": "portvale", "stop": "pier-st-mill-ln"}, {"stopinfo": load_fixture("stopinfo_bus.json"), "schedules": load_fixture("schedules.json")}),
   "get-line-status": ({"city": "portvale"}, {"routestatus": load_fixture("routestatus.json")}),
   "get-disruptions": ({"city": "portvale"}, {"routestatus": load_fixture("routestatus.json")}),
   "get-service-message": ({"city": "portvale"}, {"message": load_fixture("message.json")}),
   "find-line": ({"city": "portvale", "query": "12"}, {"findtransport": load_fixture("findtransport.json")}),
   "get-line": ({"city": "portvale", "line": "metro-a", "with_paths": True}, {"routeinfo1": load_fixture("routeinfo1.json")}),
   "get-lines": ({"city": "portvale", "lines": ["A", "C"]}, {"routeinfo2": load_fixture("routeinfo2.json")}),
   "get-vehicles": ({"city": "portvale", "line": "A"}, {"vehiclelocations": load_fixture("vehiclelocations.json")}),
   "get-route-paths": ({"city": "portvale", "lines": ["A"]}, {"routepaths": load_fixture("routepaths.json")}),
   "get-map-around": ({"city": "portvale", "near": INSIDE_START, "size": "large"}, {"everythingmap": load_fixture("everythingmap.json")}),
   "open-go-link": ({"slug": "k3x9"}, {"getshorturl": GETSHORTURL_BODY}),
   "list-news": ({}, {"blog": load_fixture("blog.json")}),
   "get-legal": ({"document": "terms"}, {"resources": load_text_fixture("legal_terms.html")}),
   "whoami": ({}, {"identity-user-data": USER_DATA_BODY}),
   "list-saved-places": ({}, {"identity-places-list": PLACES_LIST_BODY}),
   "list-favourites": ({}, {"identity-favorites-list": FAVOURITES_LIST_BODY}),
   "pass-account": ({"use_web_session_id": True}, {"turnstile-userinfo": PASS_USER_INFO_BODY}),
   "pass-session-time": ({"use_web_session_id": True}, {"turnstile-sessionttl": PASS_SESSION_TTL_BODY}),
}


def run_command(context, name, arguments):
   return registry.FUNCTIONS[name](context, dict(arguments))


def test_cases_cover_every_command():
   covered = set(READ_CASES) | set(RETIRED_COMMANDS) | WRITE_COMMANDS | {"adopt-session"}

   assert covered == set(registry.FUNCTIONS)


@pytest.mark.parametrize("name", sorted(READ_CASES))
def test_read_output_matches_its_schema(make_context, name):
   arguments, responses = READ_CASES[name]
   context, fake = make_context(responses, session=signed_in_session())

   output = cli.run_command(COMMANDS[name], context, dict(arguments))

   assert_valid(output, SCHEMAS[name]["output_schema"])
   assert set(fake.findings) == set(responses)

   if fake.requests:
      assert output["fetched_at"] == fake.first_sent_at


def test_transport_keeps_the_first_send_time_and_updates_the_last(tmp_path):
   transport, _ = build_transport(tmp_path, RecordingHandler(json_reply({"travel_time_minutes": 4})))
   transport.clock = iter(["2026-10-10T09:00:00Z", "2026-10-10T09:00:04Z"]).__next__

   transport.send(Request(endpoints.TRAVEL_TIME))
   transport.send(Request(endpoints.TRAVEL_TIME))

   assert transport.first_sent_at == "2026-10-10T09:00:00Z"
   assert transport.last_sent_at == "2026-10-10T09:00:04Z"


def test_adopt_session_output_matches_its_schema_and_stores_the_cookie(make_context, tmp_path):
   context, fake = make_context()
   cookie_file = tmp_path / "cookie.txt"
   cookie_file.write_text("Cookie: sessionid=abc123; csrftoken=tok456; _ga=GA1.2.3")

   output = run_command(context, "adopt-session", {"from_file": str(cookie_file)})

   assert_valid(output, SCHEMAS["adopt-session"]["output_schema"])
   assert output["stored"] == ["csrftoken", "sessionid"]
   assert output["lengths"] == {"csrftoken": 6, "sessionid": 6}
   assert "abc123" not in json.dumps(output)
   assert "_ga" not in read_env_file(context.paths.env_file)[COOKIE_KEY]
   assert stat.S_IMODE(context.paths.env_file.stat().st_mode) == 0o600
   assert fake.requests == []


@pytest.mark.parametrize("name", sorted(RETIRED_COMMANDS))
def test_retired_commands_raise_not_found_and_send_nothing(make_context, name):
   context, fake = make_context()
   arguments = {"city": "portvale", "from": INSIDE_START, "to": INSIDE_END, "near": INSIDE_START, "signature": JOURNEY_SIGNATURE}

   with pytest.raises(NotFound) as caught:
      run_command(context, name, arguments)

   assert caught.value.message == RETIRED_COMMANDS[name]
   assert fake.requests == []


class TestPlanJourney:
   def plan(self, make_context, responses=None, **arguments):
      context, fake = make_context(responses or {"journeys": load_fixture("journeys.json")})
      output = run_command(context, "plan-journey", {"city": "portvale", "from": INSIDE_START, "to": INSIDE_END, **arguments})
      return output, fake

   def test_sends_coordinates_as_lat_lng_and_the_region(self, make_context):
      output, fake = self.plan(make_context)

      query = fake.only_request("journeys").query
      assert query["start"] == "10.5,20.5"
      assert query["end"] == "10.6,20.7"
      assert query["region_id"] == "zz-portvale"
      assert "departure_time" not in query
      assert "arrival_time" not in query
      assert output["time_mode"] == "now"

   def test_depart_at_is_sent_as_utc_iso_from_the_city_timezone(self, make_context):
      output, fake = self.plan(make_context, depart_at="2026-10-12T08:30")

      query = fake.only_request("journeys").query
      assert query["departure_time"] == "2026-10-11T23:30:00.000Z"
      assert "arrival_time" not in query
      assert output["time_mode"] == "depart_at"
      assert output["requested_time"] == "2026-10-11T23:30:00.000Z"

   def test_arrive_by_is_sent_as_utc_iso_from_the_city_timezone(self, make_context):
      output, fake = self.plan(make_context, arrive_by="2026-10-12T18:05")

      query = fake.only_request("journeys").query
      assert query["arrival_time"] == "2026-10-12T09:05:00.000Z"
      assert "departure_time" not in query
      assert output["time_mode"] == "arrive_by"

   def test_clock_time_uses_the_city_timezone(self, make_context):
      output, fake = self.plan(make_context, depart_at="08:30")

      departure = fake.only_request("journeys").query["departure_time"]
      assert re.fullmatch(r"\d{4}-\d\d-\d\dT23:30:00\.000Z", departure)

   def test_offset_iso_time_is_converted_not_relabelled(self, make_context):
      output, fake = self.plan(make_context, depart_at="2026-10-12T08:30:00+02:00")

      assert fake.only_request("journeys").query["departure_time"] == "2026-10-12T06:30:00.000Z"

   def test_rejects_depart_at_and_arrive_by_together(self, make_context):
      with pytest.raises(UsageError):
         self.plan(make_context, depart_at="08:30", arrive_by="09:30")

   def test_sends_nothing_when_both_times_are_given(self, make_context):
      context, fake = make_context({"journeys": load_fixture("journeys.json")})

      with pytest.raises(UsageError):
         run_command(context, "plan-journey", {"city": "portvale", "from": INSIDE_START, "to": INSIDE_END, "depart_at": "08:30", "arrive_by": "09:30"})

      assert fake.requests == []

   def test_rejects_an_unreadable_time(self, make_context):
      with pytest.raises(UsageError):
         self.plan(make_context, depart_at="half past eight")

   @pytest.mark.parametrize("outside", ["12.0,20.5", "10.5,25.0", "-10.5,-20.5"])
   def test_rejects_coordinates_outside_the_city_box(self, make_context, outside):
      context, fake = make_context({"journeys": load_fixture("journeys.json")})

      with pytest.raises(UsageError):
         run_command(context, "plan-journey", {"city": "portvale", "from": outside, "to": INSIDE_END})

      assert fake.requests == []

   def test_text_place_goes_through_search_then_place_resolve(self, make_context):
      responses = {"searchpost": load_fixture("searchpost_google_only.json"), "placeresolve": load_fixture("placeresolve.json"), "journeys": load_fixture("journeys.json")}

      output, fake = self.plan(make_context, responses, **{"from": "Lantern Market"})

      search_request = fake.only_request("searchpost")
      resolve_request = fake.only_request("placeresolve")
      assert fake.findings == ["searchpost", "placeresolve", "journeys"]
      assert search_request.form_json["query"] == "Lantern Market"
      assert search_request.form_json["region_id"] == "zz-portvale"
      assert search_request.headers["Citymapper-Region"] == "zz-portvale"
      assert resolve_request.query == {"id": "google:ChIJFakePlaceAlpha", "region_id": "zz-portvale"}
      assert fake.only_request("journeys").query["start"] == "10.523,20.611"
      assert output["from"]["name"] == "Lantern Market"
      assert output["from"]["coords"] == [10.523, 20.611]

   def test_station_result_with_coordinates_skips_place_resolve(self, make_context):
      responses = {"searchpost": load_fixture("searchpost.json"), "journeys": load_fixture("journeys.json")}

      output, fake = self.plan(make_context, responses, **{"from": "Harbour"})

      assert fake.findings == ["searchpost", "journeys"]
      assert fake.only_request("journeys").query["start"] == "10.512,20.488"

   def test_text_place_without_any_coordinates_is_not_found(self, make_context):
      context, fake = make_context({"searchpost": load_fixture("searchpost_google_only.json"), "placeresolve": load_fixture("placeresolve_null.json")})

      with pytest.raises(NotFound):
         run_command(context, "plan-journey", {"city": "portvale", "from": "Lantern Market", "to": INSIDE_END})

      assert "journeys" not in fake.findings

   def test_sections_keep_journey_indexes_within_the_limit(self, make_context):
      output, _ = self.plan(make_context, limit=1)

      assert [journey["index"] for journey in output["journeys"]] == [0]
      assert output["sections"] == [{"id": "SUGGESTED", "name": "Suggested", "journey_indexes": [0]}, {"id": "METRO_ONLY", "name": "More Metro", "journey_indexes": []}]

   def test_transit_leg_carries_routes_stops_and_price(self, make_context):
      output, _ = self.plan(make_context, with_paths=True)

      first = output["journeys"][0]
      transit_leg = first["legs"][1]
      assert first["price"] == "$2.10"
      assert first["signature"] == JOURNEY_SIGNATURE
      assert transit_leg["routes"] == [{"id": "A", "name": "A", "brand_id": "PortvaleMetro", "color": "#1A6FB0"}]
      assert [stop["name"] for stop in transit_leg["stops"]] == ["Harbour Sq", "Dock Rd", "Saltmarsh"]
      assert transit_leg["path"][0] == [10.512, 20.488]
      assert first["departure_time"] == "2026-10-12T08:31:30+09:00"
      assert first["arrival_time"] == "2026-10-12T08:45:00+09:00"

   def test_paths_are_left_out_unless_asked(self, make_context):
      output, _ = self.plan(make_context)

      assert all(leg["path"] == [] for journey in output["journeys"] for leg in journey["legs"])


def test_a_text_place_is_searched_once_across_read_commands(make_context):
   responses = {"searchpost": load_fixture("searchpost_google_only.json"), "placeresolve": load_fixture("placeresolve.json"), "journeys": load_fixture("journeys.json")}
   context, fake = make_context(responses)
   arguments = {"city": "portvale", "from": "Lantern Market", "to": INSIDE_END}

   first = cli.run_command(COMMANDS["plan-journey"], context, dict(arguments))
   second = cli.run_command(COMMANDS["plan-journey"], context, {**arguments, "from": " lantern  MARKET"})

   assert fake.findings == ["searchpost", "placeresolve", "journeys", "journeys"]
   assert second["from"] == first["from"]
   assert fake.requests[-1].query["start"] == "10.523,20.611"


def test_a_write_searches_a_text_place_again_even_when_a_read_cached_it(make_context):
   responses = {"searchpost": load_fixture("searchpost.json"), "journeys": load_fixture("journeys.json")}
   context, fake = make_context(responses, session=signed_in_session())

   cli.run_command(COMMANDS["plan-journey"], context, {"city": "portvale", "from": "Harbour", "to": INSIDE_END})
   cli.run_command(COMMANDS["save-place"], context, {"city": "portvale", "near": "Harbour", "name": "Studio", "dry_run": True})

   assert fake.findings == ["searchpost", "journeys", "searchpost"]


def test_plan_walk_asks_for_two_walks(make_context):
   context, fake = make_context({"walk7": load_fixture("walk7.json")})

   output = run_command(context, "plan-walk", {"city": "portvale", "from": INSIDE_START, "to": INSIDE_END})

   assert fake.only_request("walk7").query["limit"] == "2"
   assert [journey["profile"] for journey in output["journeys"]] == ["Fast", "Quiet"]


def test_plan_cab_lists_routes_and_services(make_context):
   context, _ = make_context({"taxi": load_fixture("taxi.json")})

   output = run_command(context, "plan-cab", {"city": "portvale", "from": INSIDE_START, "to": INSIDE_END})

   assert output["routes"] == [{"mode": "taxi", "duration_seconds": 780, "distance_meters": 4120}]
   assert output["services"] == [{"name": "Gull Standard", "category": "gullcabs"}, {"name": "Gull XL", "category": "gullcabs"}]


def test_plan_cab_limit_trims_routes_and_services(make_context):
   two_route_taxi = load_fixture("taxi.json")
   two_route_taxi["routes"].append({"mode": "taxi", "length_meters": 5300, "duration_seconds": 960})
   context, _ = make_context({"taxi": two_route_taxi})

   output = run_command(context, "plan-cab", {"city": "portvale", "from": INSIDE_START, "to": INSIDE_END, "limit": 1})

   assert output["routes"] == [{"mode": "taxi", "duration_seconds": 780, "distance_meters": 4120}]
   assert output["services"] == [{"name": "Gull Standard", "category": "gullcabs"}]


def test_journey_times_post_the_signatures(make_context):
   context, fake = make_context({"journeytimes": load_fixture("journeytimes.json")})

   output = run_command(context, "get-journey-times", {"city": "portvale", "signatures": [JOURNEY_SIGNATURE]})

   request = fake.only_request("journeytimes")
   assert request.endpoint.method == "POST"
   assert request.json_body == {"signatures": [JOURNEY_SIGNATURE]}
   assert [item["time"] for item in output["times"]] == ["2026-10-12T08:45:00+09:00", "2026-10-12T08:52:00+09:00"]


class TestSearchPlaces:
   def test_skips_heading_and_attribution_rows(self, make_context):
      context, _ = make_context({"searchpost": load_fixture("searchpost.json")})

      output = run_command(context, "search-places", {"city": "portvale", "query": "Harbour"})

      assert [place["name"] for place in output["results"]] == ["Harbour Sq", "Lantern Market", "Old Mill Hall"]
      assert output["results"][0]["coords"] == [10.512, 20.488]
      assert output["results"][1]["coords"] is None
      assert output["results"][1]["id"] == "google:ChIJFakePlaceAlpha"

   def test_near_coordinates_are_sent_as_location(self, make_context):
      context, fake = make_context({"searchpost": load_fixture("searchpost.json")})

      run_command(context, "search-places", {"city": "portvale", "query": "Harbour", "near": INSIDE_START})

      assert fake.only_request("searchpost").form_json["location"] == "10.5,20.5"

   def test_limit_trims_results(self, make_context):
      context, _ = make_context({"searchpost": load_fixture("searchpost.json")})

      output = run_command(context, "search-places", {"city": "portvale", "query": "Harbour", "limit": 2})

      assert len(output["results"]) == 2


def test_resolve_place_without_a_result_is_not_found(make_context):
   context, _ = make_context({"placeresolve": load_fixture("placeresolve_null.json")})

   with pytest.raises(NotFound):
      run_command(context, "resolve-place", {"city": "portvale", "id": "google:ChIJFakePlaceAlpha"})


def test_reverse_geocode_without_results_still_echoes_the_coordinates(make_context):
   context, _ = make_context({"geocode": {"results": []}})

   output = run_command(context, "reverse-geocode", {"lat": 10.5231, "lng": 20.6109})

   assert output == {"address": None, "name": None, "components": [], "coords": [10.5231, 20.6109]}
   assert_valid(output, SCHEMAS["reverse-geocode"]["output_schema"])


def test_reverse_geocode_reads_the_first_google_result(make_context):
   context, fake = make_context({"geocode": load_fixture("geocode.json")})

   output = run_command(context, "reverse-geocode", {"lat": 10.5231, "lng": 20.6109})

   assert fake.only_request("geocode").query == {"lat": 10.5231, "lng": 20.6109}
   assert output["address"] == "18 Quay Rd, Portvale 400-0001"
   assert output["name"] == "18 Quay Road"


class TestFindNearby:
   def nearby(self, make_context, mode):
      context, fake = make_context({"nearby3": load_fixture("nearby3.json")})
      output = run_command(context, "find-nearby", {"city": "portvale", "near": INSIDE_START, "mode": mode})
      return output, fake.only_request("nearby3").query

   def test_brand_mode_sends_brand_ids(self, make_context):
      output, query = self.nearby(make_context, "metro")

      assert query["brand_ids"] == "PortvaleMetro"
      assert query["mode_id"] == "zz-portvale-metro"
      assert query["location"] == "10.5,20.5"
      assert "kinds" not in query

   def test_mode_without_brands_sends_kinds(self, make_context):
      _, query = self.nearby(make_context, "ferry")

      assert query["kinds"] == "ferrystop"
      assert "brand_ids" not in query

   def test_mode_can_be_named_by_affinity(self, make_context):
      _, query = self.nearby(make_context, "cycle")

      assert query["mode_id"] == "zz-portvale-bikes"

   def test_stops_and_docks_are_parsed(self, make_context):
      output, _ = self.nearby(make_context, "metro")

      station, dock = output["elements"]
      assert station["kind"] == "transitstop"
      assert station["routes"] == ["A", "C"]
      assert dock["kind"] == "cycledock"
      assert dock["brand_ids"] == ["HarbourBikes"]
      assert (dock["bikes_available"], dock["spaces_available"], dock["electric_available"]) == (4, 11, 2)

   def test_unknown_mode_is_a_usage_error(self, make_context):
      with pytest.raises(UsageError) as caught:
         self.nearby(make_context, "zeppelin")

      assert caught.value.detail["modes"] == ["bike", "ferry", "metro"]


class TestGetDepartures:
   def departures(self, make_context, stop_fixture, feed_finding, feed_fixture, **arguments):
      context, fake = make_context({"stopinfo": load_fixture(stop_fixture), feed_finding: load_fixture(feed_fixture)})
      output = run_command(context, "get-departures", {"city": "portvale", "stop": "any-stop", **arguments})
      assert_valid(output, SCHEMAS["get-departures"]["output_schema"])
      return output, fake

   def test_metro_feed_is_dispatched_and_sorted_live_first(self, make_context):
      output, fake = self.departures(make_context, "stopinfo_metro.json", "departures-metro", "departures_metro.json")

      request = fake.only_request("departures-metro")
      rows = output["departures"]
      assert fake.findings == ["stopinfo", "departures-metro"]
      assert request.query == {"headways": "1", "ids": "MetroHarbourSq", "region_id": "zz-portvale"}
      assert output["feed"] == "metrodepartures"
      assert [row["seconds_away"] for row in rows[:2]] == [60, 300]
      assert [row["is_live"] for row in rows] == [True, True, False, False]
      assert rows[0]["route_name"] == "C"
      assert rows[0]["platform_or_direction"] == "Southbound"

   def test_metro_advisory_row_becomes_advisory_text(self, make_context):
      output, _ = self.departures(make_context, "stopinfo_metro.json", "departures-metro", "departures_metro.json")

      advisories = [row for row in output["departures"] if row["advisory"]]
      assert advisories == [{"route_id": "A", "is_live": False, "route_name": "A", "destination": None, "platform_or_direction": "Southbound", "seconds_away": None, "time": None, "scheduled_time": None, "advisory": "Platform 2 closed for repairs"}]

   def test_metro_scheduled_row_keeps_its_time(self, make_context):
      output, _ = self.departures(make_context, "stopinfo_metro.json", "departures-metro", "departures_metro.json")

      scheduled = [row for row in output["departures"] if row["scheduled_time"]]
      assert scheduled[0]["destination"] == "Airport"
      assert scheduled[0]["platform_or_direction"] == "Northbound"

   def test_bus_feed_is_dispatched_and_sorted_live_first(self, make_context):
      output, fake = self.departures(make_context, "stopinfo_bus.json", "departures-bus", "departures_bus.json")

      rows = output["departures"]
      assert fake.only_request("departures-bus").query["ids"] == "PVBus_4471"
      assert output["feed"] == "departures"
      assert [(row["route_name"], row["seconds_away"], row["is_live"]) for row in rows] == [("12", 95, True), ("12", 420, True), ("40", None, False), ("40", None, False)]
      assert [row["time"] for row in rows[2:]] == ["2026-10-12T08:50:00+09:00", "2026-10-12T09:20:00+09:00"]
      assert all(row["advisory"] is None for row in rows)
      assert rows[0]["destination"] == "Lighthouse"
      assert rows[0]["platform_or_direction"] == "NE"

   def test_bus_feed_without_an_update_time_reports_when_it_was_asked(self, make_context):
      output, fake = self.departures(make_context, "stopinfo_bus.json", "departures-bus", "departures_bus.json")

      assert output["updated"] is not None
      assert output["updated"] == fake.last_sent_at

   def test_bus_service_without_any_times_gets_an_advisory_row(self):
      response = {"stops": [{"bearing": "N", "services": [{"headsign": "Depot", "route_id": "PortvaleBus7"}]}]}

      departures, _ = bus_departures(response, {"PortvaleBus7": "7"})

      assert [(row.route_name, row.is_live, row.advisory) for row in departures] == [("7", False, "no live times")]

   def test_rail_feed_is_dispatched(self, make_context):
      output, fake = self.departures(make_context, "stopinfo_rail.json", "departures-rail", "departures_rail.json")

      rows = output["departures"]
      assert fake.only_request("departures-rail").query["ids"] == "RailPortvaleCentral"
      assert output["feed"] == "raildepartures"
      assert output["updated"] == "2026-10-12T08:30:20+09:00"
      assert {row["destination"]: row["platform_or_direction"] for row in rows} == {"Seagate": "3", "Inland Junction": None}

   def test_rail_live_rows_sort_before_sooner_timetabled_rows(self, make_context):
      output, _ = self.departures(make_context, "stopinfo_rail.json", "departures-rail", "departures_rail.json")

      rows = output["departures"]
      assert [(row["is_live"], row["seconds_away"]) for row in rows] == [(True, 540), (False, 180)]

   def test_route_filter_keeps_only_that_route(self, make_context):
      output, _ = self.departures(make_context, "stopinfo_metro.json", "departures-metro", "departures_metro.json", route="C")

      assert [row["route_id"] for row in output["departures"]] == ["C"]

   def test_limit_trims_after_sorting(self, make_context):
      output, _ = self.departures(make_context, "stopinfo_bus.json", "departures-bus", "departures_bus.json", limit=1)

      assert [row["seconds_away"] for row in output["departures"]] == [95]

   def test_unknown_feed_is_not_found_and_sends_no_feed_request(self, make_context):
      stop_info = load_fixture("stopinfo_metro.json")
      stop_info["stops"][0]["sharing_urls"][0]["departure_api"] = "ferrydepartures"
      context, fake = make_context({"stopinfo": stop_info})

      with pytest.raises(NotFound):
         run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})

      assert fake.findings == ["stopinfo"]

   def test_a_known_stop_is_not_looked_up_again(self, make_context):
      context, fake = make_context({"stopinfo": load_fixture("stopinfo_metro.json"), "departures-metro": load_fixture("departures_metro.json")})

      first = run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})
      by_alias_again = run_command(context, "get-departures", {"city": "portvale", "stop": " Harbour-Sq "})
      by_id = run_command(context, "get-departures", {"city": "portvale", "stop": "MetroHarbourSq"})

      assert fake.findings == ["stopinfo", "departures-metro", "departures-metro", "departures-metro"]
      assert by_alias_again == first
      assert by_id == first
      assert first["departures"][0]["route_name"] == "C"

   def test_stop_schedule_reuses_the_stop_that_get_stop_fetched(self, make_context):
      context, fake = make_context({"stopinfo": load_fixture("stopinfo_bus.json"), "schedules": load_fixture("schedules.json")})

      run_command(context, "get-stop", {"city": "portvale", "stop": "pier-st-mill-ln"})
      output = run_command(context, "get-stop-schedule", {"city": "portvale", "stop": "pier-st-mill-ln"})

      assert fake.findings == ["stopinfo", "schedules"]
      assert fake.only_request("schedules").query["id"] == "PVBus_4471"
      assert output["stop"] == "PVBus_4471"

   def test_a_feed_that_no_longer_knows_the_stop_drops_it_from_the_cache(self, make_context):
      feed_replies = iter([load_fixture("departures_metro.json"), NotFound("gone", {}), load_fixture("departures_metro.json")])
      context, fake = make_context({"stopinfo": load_fixture("stopinfo_metro.json"), "departures-metro": lambda request: next(feed_replies)})

      run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})

      with pytest.raises(NotFound):
         run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})

      run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})

      assert fake.findings == ["stopinfo", "departures-metro", "departures-metro", "stopinfo", "departures-metro"]

   def test_a_stop_older_than_its_lifetime_is_looked_up_again(self, make_context):
      context, fake = make_context({"stopinfo": load_fixture("stopinfo_metro.json"), "departures-metro": load_fixture("departures_metro.json")})
      run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})
      stop_cache_file = context.paths.cache_dir / "stops-zz-portvale.json"
      cached = json.loads(stop_cache_file.read_text())

      for entry in cached["entries"].values():
         entry["fetched_at"] = time.time() - STOP_CACHE_MAX_AGE_SECONDS - 1

      stop_cache_file.write_text(json.dumps(cached))
      run_command(context, "get-departures", {"city": "portvale", "stop": "harbour-sq"})

      assert fake.findings == ["stopinfo", "departures-metro", "stopinfo", "departures-metro"]


def test_get_stop_reads_routes_exits_and_feed(make_context):
   context, fake = make_context({"stopinfo": load_fixture("stopinfo_metro.json")})

   output = run_command(context, "get-stop", {"city": "portvale", "stop": "harbour-sq"})

   assert fake.only_request("stopinfo").query == {"ids": "harbour-sq", "region_id": "zz-portvale"}
   assert output["departure_api"] == "metrodepartures"
   assert [route["name"] for route in output["routes"]] == ["A", "C"]
   assert [exit_record["name"] for exit_record in output["exits"]] == ["Quay Rd exit", "Market St exit"]


def test_unknown_stop_is_not_found(make_context):
   context, _ = make_context({"stopinfo": {"stops": [], "routes": []}})

   with pytest.raises(NotFound):
      run_command(context, "get-stop", {"city": "portvale", "stop": "nowhere"})


class TestDisruptions:
   def disruptions(self, make_context, **arguments):
      context, fake = make_context({"routestatus": load_fixture("routestatus.json")})
      output = run_command(context, "get-disruptions", {"city": "portvale", **arguments})
      return output, fake

   def test_placeholders_are_filled_from_replacements(self, make_context):
      output, fake = self.disruptions(make_context)

      descriptions = [item["description"] for item in output["disruptions"]]
      assert "A trains suspended between Dock Rd and Harbour Sq. Use {2} instead." in descriptions
      assert "Minor delays near Saltmarsh." in descriptions
      assert fake.only_request("routestatus").query == {"region_id": "zz-portvale", "format": "rich"}

   def test_default_minimum_level_is_one_and_most_severe_comes_first(self, make_context):
      output, _ = self.disruptions(make_context)

      summary = [(item["level"], item["group"], item["line"]) for item in output["disruptions"]]
      assert summary == [(2, "Metro", "A"), (1, "Buses", "12"), (1, "Metro", "A")]

   def test_status_without_disruption_list_still_counts(self, make_context):
      output, _ = self.disruptions(make_context, line="bus-12")

      assert output["disruptions"] == [{"line": "12", "line_name": "Lighthouse - Old Town", "group": "Buses", "level": 1, "summary": "Diversion", "description": "Diverted via Pier St.", "stops": []}]

   def test_min_level_filters_lower_levels(self, make_context):
      output, _ = self.disruptions(make_context, min_level=2)

      assert [(item["line"], item["level"]) for item in output["disruptions"]] == [("A", 2)]

   def test_min_level_zero_includes_good_service_lines(self, make_context):
      output, _ = self.disruptions(make_context, min_level=0)

      assert "C" in [item["line"] for item in output["disruptions"]]

   def test_line_filter_matches_alias(self, make_context):
      output, _ = self.disruptions(make_context, line="metro-a")

      assert {item["line"] for item in output["disruptions"]} == {"A"}
      assert output["disruptions"][0]["stops"] == ["MetroDockRd", "MetroHarbourSq"]


def test_line_status_fills_placeholders_and_filters_by_mode(make_context):
   context, _ = make_context({"routestatus": load_fixture("routestatus.json")})

   output = run_command(context, "get-line-status", {"city": "portvale", "mode": "bus"})

   assert [group["name"] for group in output["groups"]] == ["Buses"]
   assert output["groups"][0]["lines"][0]["status"]["description"] == "Diverted via Pier St."


def test_line_status_and_disruptions_share_one_status_read(make_context):
   context, fake = make_context({"routestatus": load_fixture("routestatus.json")})

   status = run_command(context, "get-line-status", {"city": "portvale"})
   disruptions = run_command(context, "get-disruptions", {"city": "portvale"})

   assert fake.findings == ["routestatus"]
   assert disruptions["updated"] == status["updated"] == load_fixture("routestatus.json")["last_updated_time"]
   assert [(item["level"], item["line"]) for item in disruptions["disruptions"]] == [(2, "A"), (1, "12"), (1, "A")]


def test_a_status_read_older_than_a_minute_is_sent_again(make_context):
   context, fake = make_context({"routestatus": load_fixture("routestatus.json")})
   run_command(context, "get-line-status", {"city": "portvale"})
   status_cache_file = context.paths.cache_dir / "routestatus-zz-portvale.json"
   cached = json.loads(status_cache_file.read_text())
   cached["fetched_at"] = time.time() - ROUTE_STATUS_MAX_AGE_SECONDS - 1
   status_cache_file.write_text(json.dumps(cached))

   run_command(context, "get-disruptions", {"city": "portvale"})

   assert fake.findings == ["routestatus", "routestatus"]


def test_find_line_keeps_only_route_results(make_context):
   context, fake = make_context({"findtransport": load_fixture("findtransport.json")})

   output = run_command(context, "find-line", {"city": "portvale", "query": "12"})

   assert fake.only_request("findtransport").query == {"query": "12", "region_id": "zz-portvale"}
   assert [line["id"] for line in output["lines"]] == ["PortvaleBus12", "PortvaleBus12X"]
   assert [line["name"] for line in output["lines"]] == ["12", "12X"]
   assert output["lines"][0]["mode"] == "bus"


class TestGetLine:
   def line(self, make_context, **arguments):
      context, fake = make_context({"routeinfo1": load_fixture("routeinfo1.json")})
      output = run_command(context, "get-line", {"city": "portvale", "line": "metro-a", **arguments})
      return output, fake

   def test_stop_points_map_to_stop_names(self, make_context):
      output, fake = self.line(make_context)

      first_pattern = output["patterns"][0]
      assert fake.only_request("routeinfo1").query["route"] == "metro-a"
      assert [stop["name"] for stop in first_pattern["stops"]] == ["Airport", "Dock Rd", "Harbour Sq"]
      assert first_pattern["stops"][0] == {"id": "MetroAirport", "name": "Airport", "coords": [10.21, 20.11]}
      assert [stop["name"] for stop in output["patterns"][1]["stops"]] == ["Harbour Sq", "Dock Rd"]

   def test_line_summary_fills_status_placeholders(self, make_context):
      output, _ = self.line(make_context)

      assert output["line"]["id"] == "A"
      assert output["line"]["status"]["description"] == "A suspended near Dock Rd"

   def test_paths_only_when_asked(self, make_context):
      without_paths, _ = self.line(make_context)
      with_paths, _ = self.line(make_context, with_paths=True)

      assert without_paths["patterns"][0]["path"] == []
      assert with_paths["patterns"][0]["path"] == [[10.21, 20.11], [10.556, 20.531], [10.512, 20.488]]

   def test_unknown_line_is_not_found(self, make_context):
      context, _ = make_context({"routeinfo1": {"routes": [], "stops": {}}})

      with pytest.raises(NotFound):
         run_command(context, "get-line", {"city": "portvale", "line": "metro-z"})


def test_get_lines_and_route_paths_send_comma_joined_ids(make_context):
   context, fake = make_context({"routeinfo2": load_fixture("routeinfo2.json"), "routepaths": load_fixture("routepaths.json")})

   lines_output = run_command(context, "get-lines", {"city": "portvale", "lines": ["A", "C"]})
   paths_output = run_command(context, "get-route-paths", {"city": "portvale", "lines": ["A"]})

   assert fake.only_request("routeinfo2").query["route_ids"] == "A,C"
   assert [line["id"] for line in lines_output["lines"]] == ["A", "C"]
   assert paths_output["paths"][0]["patterns"][1]["path"] == [[10.512, 20.488], [10.556, 20.531]]


class TestCities:
   def test_list_cities_without_query_lists_every_region_with_its_cities(self, make_context):
      context, fake = make_context()

      output = run_command(context, "list-cities", {})

      by_id = {region["region_id"]: region for region in output["regions"]}
      assert sorted(by_id) == ["zz-lakeshore", "zz-portmoor", "zz-portvale"]
      assert [city["slug"] for city in by_id["zz-portvale"]["cities"]] == ["portvale-central", "east-quay"]
      assert fake.requests == []

   @pytest.mark.parametrize("query, expected_ids", [
      ("lake", ["zz-lakeshore"]),
      ("North Cove", ["zz-lakeshore"]),
      ("port", ["zz-portvale", "zz-portmoor"]),
      ("atlantis", []),
   ])
   def test_list_cities_filters_by_query(self, make_context, query, expected_ids):
      context, _ = make_context()

      output = run_command(context, "list-cities", {"query": query})

      assert [region["region_id"] for region in output["regions"]] == expected_ids

   @pytest.mark.parametrize("text", ["portvale", "zz-portvale", "Portvale", "PORT V", "Portvale Bay", "east-quay", "East Quay", "portvale-central"])
   def test_resolve_matches_slug_id_name_alias_and_city(self, make_context, text):
      context, _ = make_context()

      assert context.catalogue.resolve(text)["region_id"] == "zz-portvale"

   def test_resolve_matches_a_unique_partial_name(self, make_context):
      context, _ = make_context()

      assert context.catalogue.resolve("lakesh")["region_id"] == "zz-lakeshore"

   def test_resolve_ambiguous_partial_is_not_found_with_suggestions(self, make_context):
      context, _ = make_context()

      with pytest.raises(NotFound) as caught:
         context.catalogue.resolve("port")

      assert caught.value.detail["suggestions"] == ["portmoor", "portvale"]

   def test_resolve_unknown_city_is_not_found(self, make_context):
      context, _ = make_context()

      with pytest.raises(NotFound):
         context.catalogue.resolve("atlantis")

   def test_resolve_empty_text_is_a_usage_error(self, make_context):
      context, _ = make_context()

      with pytest.raises(UsageError):
         context.catalogue.resolve("")

   def test_city_in_an_unknown_region_is_dropped(self, make_context):
      context, _ = make_context()

      with pytest.raises(NotFound):
         context.catalogue.resolve("ghost-town")

   def test_catalogue_is_parsed_from_the_cities_page_and_cached(self, make_context):
      context, fake = make_context({"cities-html": load_text_fixture("cities.html")}, with_cached_catalogue=False)

      first = context.catalogue.load()
      reloaded = type(context.catalogue)(fake, context.paths.cache_dir).load()

      assert fake.findings == ["cities-html"]
      assert [region["slug"] for region in first["regions"]] == ["portvale", "lakeshore", "portmoor"]
      assert first["regions"][0]["bounding_box"] == {"northeast_corner_coords": [11.0, 21.0], "southwest_corner_coords": [10.0, 20.0]}
      assert reloaded["regions"] == first["regions"]

   @pytest.mark.parametrize("cached", [
      [],
      {"fetched_at": time.time()},
      {"fetched_at": "yesterday", "regions": []},
      {"fetched_at": time.time(), "regions": [{"region_id": "zz-portvale"}]},
   ])
   def test_a_corrupt_catalogue_cache_is_fetched_again(self, make_context, cached):
      context, fake = make_context({"cities-html": load_text_fixture("cities.html")}, with_cached_catalogue=False)
      context.paths.cache_dir.mkdir(parents=True, exist_ok=True)
      (context.paths.cache_dir / "catalogue.json").write_text(json.dumps(cached))

      region = context.catalogue.resolve("portvale")

      assert fake.findings == ["cities-html"]
      assert region["region_id"] == "zz-portvale"

   @pytest.mark.parametrize("cached", [[], {"fetched_at": time.time()}, {"fetched_at": None, "config": {}}])
   def test_a_corrupt_region_config_cache_is_fetched_again(self, make_context, cached):
      context, fake = make_context({"resource-region-info": load_fixture("region_info.json")}, with_cached_region=False)
      (context.paths.cache_dir / "region-zz-portvale.json").write_text(json.dumps(cached))

      output = run_command(context, "get-city", {"city": "portvale"})

      assert fake.findings == ["resource-region-info"]
      assert output["timezone"] == "Asia/Tokyo"

   def test_page_without_the_regions_global_is_contract_broken(self, make_context):
      context, _ = make_context({"cities-html": "<html><body>moved</body></html>"}, with_cached_catalogue=False)

      with pytest.raises(ContractBroken):
         context.catalogue.load()

   def test_get_city_reads_region_info(self, make_context):
      context, fake = make_context({"resource-region-info": load_fixture("region_info.json")}, with_cached_region=False)

      output = run_command(context, "get-city", {"city": "portvale"})

      assert fake.only_request("resource-region-info").path_values == {"region_id": "zz-portvale"}
      assert output["timezone"] == "Asia/Tokyo"
      assert [mode["slug"] for mode in output["nearby_modes"]] == ["metro", "bike", "ferry"]

   def test_get_city_without_timezone_is_contract_broken(self, make_context):
      config = load_fixture("region_info.json")
      del config["timezone"]
      context, _ = make_context(region_config=config)

      with pytest.raises(ContractBroken):
         run_command(context, "get-city", {"city": "portvale"})

   def test_region_info_for_another_region_is_contract_broken(self, make_context):
      wrong_region = {**load_fixture("region_info.json"), "region_id": "zz-lakeshore"}
      context, _ = make_context({"resource-region-info": wrong_region}, with_cached_region=False)

      with pytest.raises(ContractBroken):
         run_command(context, "get-city", {"city": "portvale"})


def test_list_brands_for_a_city_keeps_only_its_brands(make_context):
   context, _ = make_context({"resource-brand-directory": load_fixture("brand_directory.json")})

   output = run_command(context, "list-brands", {"city": "portvale"})

   assert [brand["id"] for brand in output["brands"]] == ["PortvaleMetro", "PortvaleBus"]


def test_list_brands_query_matches_name(make_context):
   context, _ = make_context({"resource-brand-directory": load_fixture("brand_directory.json")})

   output = run_command(context, "list-brands", {"query": "gull"})

   assert [brand["id"] for brand in output["brands"]] == ["GullCabs"]


def test_list_brands_downloads_the_directory_once(make_context):
   context, fake = make_context({"resource-brand-directory": load_fixture("brand_directory.json")})

   everything = run_command(context, "list-brands", {})
   in_city = run_command(context, "list-brands", {"city": "portvale"})
   everything_again = run_command(context, "list-brands", {})

   assert fake.findings == ["resource-brand-directory"]
   assert everything_again == everything
   assert in_city["brands"] and len(in_city["brands"]) < len(everything["brands"])


def test_list_news_reads_post_ids_from_urls(make_context):
   context, fake = make_context({"blog": load_fixture("blog.json")})

   output = run_command(context, "list-news", {"limit": 1})

   assert fake.only_request("blog").query == {}
   assert output["posts"] == [{"id": "3104", "title": "Harbour Festival 3 May 2026", "url": "https://content.citymapper.com/i/3104/harbour-festival-3-may-2026", "summary": "Road closures around the quay", "date": "2026-04-28T09:00:00+00:00"}]


def test_get_legal_strips_markup_scripts_and_styles(make_context):
   context, fake = make_context({"resources": load_text_fixture("legal_terms.html")})

   output = run_command(context, "get-legal", {"document": "terms"})

   assert fake.only_request("resources").query == {"id": "citymapper-terms-of-service"}
   assert output["title"] == "Terms of Service"
   assert "Use the app kindly & ride safely." in output["text"]
   assert "trackingDisabled" not in output["text"]
   assert "font-family" not in output["text"]


def test_open_go_link_reads_the_destination(make_context):
   context, _ = make_context({"getshorturl": GETSHORTURL_BODY})

   output = run_command(context, "open-go-link", {"slug": "k3x9"})

   assert output["name"] == "Lantern Market"
   assert output["coords"] == [10.523, 20.611]


def test_open_trip_link_without_city_only_reads_the_signature(make_context):
   context, fake = make_context({"gettrip": GETTRIP_BODY})

   output = run_command(context, "open-trip-link", {"slug": "Tq7xk2"})

   assert output == {"signature": JOURNEY_SIGNATURE, "journey": None}
   assert fake.findings == ["gettrip"]


def test_whoami_reports_signed_out_when_the_server_refuses(make_context):
   context, fake = make_context({"identity-user-data": SessionExpired("HTTP 403")})

   output = run_command(context, "whoami", {})

   assert output == {"signed_in": False, "user": {}}
   assert fake.findings == ["identity-user-data"]


def test_list_favourites_filters_by_city(make_context):
   context, _ = make_context({"identity-favorites-list": FAVOURITES_LIST_BODY}, session=signed_in_session())

   output = run_command(context, "list-favourites", {"city": "lakeshore"})

   assert output["favourites"] == [{"id": "10", "type": "3", "target_id": "L9", "name": "L9", "region_id": "zz-lakeshore"}]


def test_pass_reads_send_device_and_session_headers(make_context):
   session = signed_in_session()
   context, fake = make_context({"turnstile-userinfo": PASS_USER_INFO_BODY, "turnstile-sessionttl": PASS_SESSION_TTL_BODY}, session=session)

   run_command(context, "pass-account", {"use_web_session_id": True})
   ttl_output = run_command(context, "pass-session-time", {"use_web_session_id": True})

   for request in fake.requests:
      assert request.headers == {"User-Device": session.cookies["uid"], "Session-Id": session.cookies["sessionid"]}

   assert ttl_output["seconds"] == 3600


def test_adopt_session_help_and_session_reads_share_the_env_file_flag(capsys, tmp_path):
   cookie_file = tmp_path / "cookie.txt"
   cookie_file.write_text("Cookie: sessionid=abc123; csrftoken=tok456")
   custom_env_file = tmp_path / "elsewhere" / "citymapper.env"

   adopt_exit_code = cli.main(["--env-file", str(custom_env_file), "adopt-session", "--from-file", str(cookie_file)])
   adopt_output = json.loads(capsys.readouterr().out)

   assert adopt_exit_code == 0
   assert adopt_output["path"] == str(custom_env_file)
   assert "sessionid=" in read_env_file(custom_env_file)[COOKIE_KEY]
   assert not site_paths().env_file.exists()
   assert Context.build(env_file=str(custom_env_file)).session.signed_in

   help_exit_code = cli.main(["--env-file", str(custom_env_file), "help"])
   help_output = json.loads(capsys.readouterr().out)

   assert help_exit_code == 0
   assert help_output["session"]["env_file"] == str(custom_env_file)
   assert help_output["session"]["has_session_cookie"] is True


def test_session_expired_names_the_env_file_flag(capsys, tmp_path):
   empty_env_file = tmp_path / "empty.env"

   exit_code = cli.main(["--env-file", str(empty_env_file), "list-saved-places"])
   printed = json.loads(capsys.readouterr().err)

   assert exit_code == 10
   assert printed["detail"]["env_file"] == str(empty_env_file)


def test_adopt_session_reads_stdin_only_when_asked(make_context, monkeypatch):
   context, _ = make_context()
   monkeypatch.setattr("sys.stdin", io.StringIO("Cookie: sessionid=abc123"))

   with pytest.raises(UsageError):
      run_command(context, "adopt-session", {})

   output = run_command(context, "adopt-session", {"stdin": True})

   assert output["stored"] == ["sessionid"]


@pytest.mark.parametrize("bad_source", ["missing", "directory", "binary"])
def test_adopt_session_with_an_unreadable_file_exits_2_with_a_json_usage_error(capsys, tmp_path, bad_source):
   cookie_path = tmp_path / "cookie-source"

   if bad_source == "directory":
      cookie_path.mkdir()
   elif bad_source == "binary":
      cookie_path.write_bytes(b"\xff\xfe\x00sessionid")

   exit_code = cli.main(["--env-file", str(tmp_path / "out.env"), "adopt-session", "--from-file", str(cookie_path)])
   printed = json.loads(capsys.readouterr().err)

   assert exit_code == 2
   assert printed["detail"]["from_file"] == str(cookie_path)
   assert not (tmp_path / "out.env").exists()
