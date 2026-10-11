import json
import re
from dataclasses import dataclass

from .capabilities import account, cities, departures, journeys, lines, local, misc, sharing
from .config import PACKAGE_DIR

FUNCTIONS = {
   "adopt-session": local.adopt_session,
   "list-cities": cities.list_cities,
   "get-city": cities.get_city,
   "list-brands": cities.list_brands,
   "search-places": journeys.search_places,
   "resolve-place": journeys.resolve_place,
   "reverse-geocode": journeys.reverse_geocode,
   "plan-journey": journeys.plan_journey,
   "plan-walk": journeys.plan_walk,
   "plan-cycle": journeys.plan_cycle,
   "plan-cab": journeys.plan_cab,
   "plan-vehicle-hire": journeys.plan_vehicle_hire,
   "get-journey-times": journeys.get_journey_times,
   "get-journey": journeys.get_journey,
   "open-trip-link": journeys.open_trip_link,
   "get-travel-time": journeys.get_travel_time,
   "get-shared-eta": journeys.get_shared_eta,
   "find-nearby": departures.find_nearby,
   "get-stop": departures.get_stop,
   "get-departures": departures.get_departures,
   "get-stop-schedule": departures.get_stop_schedule,
   "get-line-status": lines.get_line_status,
   "get-disruptions": lines.get_disruptions,
   "get-service-message": lines.get_service_message,
   "find-line": lines.find_line,
   "get-line": lines.get_line,
   "get-lines": lines.get_lines,
   "get-vehicles": lines.get_vehicles,
   "get-route-paths": lines.get_route_paths,
   "get-map-around": misc.get_map_around,
   "get-weather": misc.get_weather,
   "get-transit-score": misc.get_transit_score,
   "open-go-link": misc.open_go_link,
   "list-news": misc.list_news,
   "get-legal": misc.get_legal,
   "whoami": account.whoami,
   "list-saved-places": account.list_saved_places,
   "list-favourites": account.list_favourites,
   "pass-account": account.pass_account,
   "pass-session-time": account.pass_session_time,
   "save-place": account.save_place,
   "update-place": account.update_place,
   "remove-place": account.remove_place,
   "add-favourite": account.add_favourite,
   "remove-favourite": account.remove_favourite,
   "save-journey": account.save_journey,
   "remove-saved-journey": account.remove_saved_journey,
   "update-profile": account.update_profile,
   "sign-out": account.sign_out,
   "share-journey": sharing.share_journey,
   "create-go-link": sharing.create_go_link,
   "vote-for-city": sharing.vote_for_city,
   "pass-set-default-payment": account.pass_set_default_payment,
   "pass-add-payment-method": account.pass_add_payment_method,
   "pass-remove-payment-method": account.pass_remove_payment_method,
   "pass-remove-all-payment-methods": account.pass_remove_all_payment_methods,
}

DEFAULT_READINESS = "built, not verified"
NEEDS_SESSION = "needs session"
NOT_VERIFIED_YET = "not yet verified live"
SESSION_STATUS_PREFIXES = (NEEDS_SESSION, "blocked: needs your Citymapper session")
SIGNED_OUT_REMARK = re.compile(r" ?\(you are signed out[^)]*\)")


@dataclass(frozen=True)
class Command:
   name: str
   purpose: str
   kind: str
   tier: str
   live_policy: str
   input_schema: dict
   output_schema: dict
   confirmation: object
   function: object


def load_schemas():
   return json.loads((PACKAGE_DIR / "schemas.json").read_text())["commands"]


def build_registry():
   schemas = load_schemas()
   registry = {}

   for name, record in schemas.items():
      function = FUNCTIONS.get(name)
      registry[name] = Command(
         name=name,
         purpose=record["purpose"],
         kind=record["kind"],
         tier=record["tier"],
         live_policy=record["live_policy"],
         input_schema=record["input_schema"],
         output_schema=record["output_schema"],
         confirmation=record.get("confirmation"),
         function=function,
      )

   return registry


def load_readiness(paths):
   try:
      return json.loads(paths.readiness_file.read_text())
   except (FileNotFoundError, ValueError):
      return {}


def readiness_of(name, readiness, command, has_session=None):
   if command.live_policy == "local":
      return "local"

   record = readiness.get(name)
   status = record.get("status", DEFAULT_READINESS) if isinstance(record, dict) else DEFAULT_READINESS
   is_session_command = command.live_policy == "session"
   is_session_status = status.startswith(SESSION_STATUS_PREFIXES)
   waits_for_session = is_session_command and is_session_status

   if not waits_for_session:
      return status

   return session_status(name, command, session_status_detail(status), has_session)


def session_status_detail(status):
   detail = status

   for prefix in SESSION_STATUS_PREFIXES:
      if detail.startswith(prefix):
         detail = detail[len(prefix):]
         break

   detail = SIGNED_OUT_REMARK.sub("", detail).replace(NOT_VERIFIED_YET, "")
   return detail.strip(" :;,")


def session_status(name, command, detail, has_session):
   separator = ", " if detail.startswith("then ") else "; "
   suffix = separator + detail if detail else ""

   if has_session is None:
      return "needs your Citymapper session" + suffix

   if not has_session:
      return "blocked: needs your Citymapper session (sign in, then adopt-session)" + suffix

   if command.kind == "read":
      return "session present, not verified live yet (run scripts/live_check.py --only {0})".format(name) + suffix

   return "session present, not verified live yet" + suffix
