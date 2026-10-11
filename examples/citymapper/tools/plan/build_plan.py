"""Build plan/plan.json and plan/plan.md for citymapper from scope/scope.json and the knowledge base.

Refuses to write when a scope capability has neither a command nor a not-planned reason.
   python3 tools/plan/build_plan.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = json.loads((ROOT / "scope/scope.json").read_text())
GENERATED = "2026-10-10"
FAILURES_PUBLIC = ["TransportError", "ChallengeRequired", "RateLimited", "ApiError", "ContractBroken", "NotFound"]
FAILURES_SIGNED_IN = ["TransportError", "SessionExpired", "ChallengeRequired", "RateLimited", "ApiError", "ContractBroken", "NotFound", "NotPermitted"]

COMMANDS = []


def finding_state(finding_id):
   path = ROOT / "knowledge/endpoints" / (finding_id + ".md")

   if not path.exists():
      return {"state": "unknown", "verify_count": 0}

   text = path.read_text()
   status = re.search(r"^status:\s*(\S+)", text, re.M)
   count = re.search(r"^verify_count:\s*(\d+)", text, re.M)
   return {"state": status.group(1) if status else "unknown", "verify_count": int(count.group(1)) if count else 0}


def depends(*endpoint_ids):
   records = []

   for endpoint_id in endpoint_ids:
      state = finding_state(endpoint_id)
      records.append({"endpoint": endpoint_id, "finding": endpoint_id, "state": state["state"], "verify_count": state["verify_count"]})

   return records


def obj(properties, required=None):
   schema = {"type": "object", "properties": properties}

   if required:
      schema["required"] = required

   return schema


def arr(items):
   return {"type": "array", "items": items}


STRING = {"type": "string"}
NULLABLE_STRING = {"type": ["string", "null"]}
NUMBER = {"type": "number"}
NULLABLE_NUMBER = {"type": ["number", "null"]}
INTEGER = {"type": "integer"}
NULLABLE_INTEGER = {"type": ["integer", "null"]}
BOOLEAN = {"type": "boolean"}
ANY_OBJECT = {"type": "object"}
COORDS = {"type": "array", "items": NUMBER, "minItems": 2, "maxItems": 2, "description": "[lat, lng]"}
NULLABLE_COORDS = {"type": ["array", "null"], "items": NUMBER}

CITY = {"type": "string", "description": "City or region: slug (nyc), region id (us-nyc), city slug (jersey-city) or name (New York)"}
PLACE_INPUT = {"type": "string", "description": "'lat,lng', or text that is resolved with search-places in the same city (first item result)"}
LIMIT = {"type": "integer", "minimum": 1}
STOP = {"type": "string", "description": "Stop alias (times-sq-42-st) or id (SubwayTimesSq42St)"}
LINE = {"type": "string", "description": "Line alias (subway-6, new-york-city-bus-m15) or route id"}

PLACE = obj({"id": NULLABLE_STRING, "name": STRING, "address": NULLABLE_STRING, "coords": NULLABLE_COORDS, "type": NULLABLE_STRING, "source": NULLABLE_STRING, "brands": arr(STRING), "lines": arr(STRING)}, ["name"])
ROUTE_REF = obj({"id": STRING, "name": STRING, "brand_id": NULLABLE_STRING, "color": NULLABLE_STRING}, ["id", "name"])
LEG = obj({"mode": STRING, "duration_seconds": NULLABLE_INTEGER, "distance_meters": NULLABLE_INTEGER, "departure_time": NULLABLE_STRING, "arrival_time": NULLABLE_STRING, "routes": arr(ROUTE_REF), "stops": arr(obj({"id": STRING, "name": STRING, "coords": COORDS})), "path": arr(COORDS)}, ["mode"])
JOURNEY = obj({
   "index": INTEGER,
   "duration_seconds": INTEGER,
   "walk_seconds": NULLABLE_INTEGER,
   "distance_meters": NULLABLE_INTEGER,
   "calories": NULLABLE_INTEGER,
   "price": NULLABLE_STRING,
   "currency": NULLABLE_STRING,
   "departure_time": NULLABLE_STRING,
   "arrival_time": NULLABLE_STRING,
   "step_free": {"type": ["boolean", "null"]},
   "profile": NULLABLE_STRING,
   "legs": arr(LEG),
   "signature": STRING,
}, ["index", "duration_seconds", "legs", "signature"])
JOURNEY_OUT = obj({"city": STRING, "region_id": STRING, "from": PLACE, "to": PLACE, "time_mode": STRING, "requested_time": NULLABLE_STRING, "sections": arr(obj({"id": STRING, "name": STRING, "journey_indexes": arr(INTEGER)})), "journeys": arr(JOURNEY)}, ["region_id", "journeys"])
JOURNEY_IN = obj({
   "city": CITY,
   "from": PLACE_INPUT,
   "to": PLACE_INPUT,
   "depart_at": {"type": "string", "description": "HH:MM in the city's timezone (today, or tomorrow once more than 15 minutes past) or ISO 8601 for any other day; sets departure_time"},
   "arrive_by": {"type": "string", "description": "HH:MM in the city's timezone (today, or tomorrow once more than 15 minutes past) or ISO 8601 for any other day; sets arrival_time"},
   "step_free": BOOLEAN,
   "limit": LIMIT,
   "with_paths": {"type": "boolean", "description": "include each leg's map path (large)"},
}, ["city", "from", "to"])
CAB_IN = obj({key: value for key, value in JOURNEY_IN["properties"].items() if key not in ("step_free", "with_paths")}, JOURNEY_IN["required"])
STATUS = obj({"level": INTEGER, "summary": STRING, "description": NULLABLE_STRING}, ["level", "summary"])
LINE_SUMMARY = obj({"id": STRING, "name": STRING, "long_name": NULLABLE_STRING, "brand": NULLABLE_STRING, "mode": NULLABLE_STRING, "aliases": arr(STRING), "color": NULLABLE_STRING, "status": STATUS}, ["id", "name"])
LINE_SEARCH_RESULT = obj({**LINE_SUMMARY["properties"], "description": NULLABLE_STRING}, LINE_SUMMARY["required"])
DEPARTURE = obj({"route_id": STRING, "route_name": NULLABLE_STRING, "destination": NULLABLE_STRING, "platform_or_direction": NULLABLE_STRING, "seconds_away": NULLABLE_INTEGER, "time": NULLABLE_STRING, "scheduled_time": NULLABLE_STRING, "is_live": BOOLEAN, "advisory": {"type": ["string", "null"]}}, ["route_id", "is_live"])
NEARBY_ELEMENT = obj({"id": STRING, "name": STRING, "alias": NULLABLE_STRING, "kind": STRING, "coords": COORDS, "walk_time_seconds": NULLABLE_INTEGER, "routes": arr(STRING), "brand_ids": arr(STRING), "bikes_available": NULLABLE_INTEGER, "spaces_available": NULLABLE_INTEGER, "electric_available": NULLABLE_INTEGER}, ["id", "name", "kind", "coords"])
DRY_RUN = obj({"dry_run": BOOLEAN, "request": obj({"method": STRING, "url": STRING, "body": ANY_OBJECT, "finding": STRING}), "confirm": {"type": "string", "description": "digest of the exact request; pass it back with --confirm together with --yes"}})
WRITE_IN_YES = {"yes": BOOLEAN, "dry_run": BOOLEAN, "confirm": {"type": "string", "description": "the confirm value printed by the approved --dry-run; required with --yes, and nothing is sent when the request differs"}}
USE_WEB_SESSION_ID = {"type": "boolean", "description": "send your web sessionid cookie as the Pass Session-Id; an unproven guess, since the real Session-Id comes from the Citymapper app"}
PASS_NOTE = "Paid feature, blocked: the Pass Session-Id comes from the Citymapper app and the web shows no source for it. --use-web-session-id sends your web sessionid as Session-Id (a hypothesis, never observed live); your citymapper.com cookies are never sent to turnstile-api."
FETCHED_AT = {"type": "string", "description": "UTC time (ISO 8601) the first request behind this answer was sent; absent when the answer came only from the local cache"}


def command(name, purpose, kind, capabilities, input_schema, output_schema, depends_on, requests, open_steps, live_policy, tier, pagination="none", confirmation=None, notes=""):
   failure_classes = {"public": FAILURES_PUBLIC, "local": [], "session": FAILURES_SIGNED_IN}[live_policy]
   is_remote_read = kind == "read" and live_policy != "local"
   declares_fetch_time = "fetched_at" in output_schema["properties"]

   if is_remote_read and not declares_fetch_time:
      output_schema = {**output_schema, "properties": {**output_schema["properties"], "fetched_at": FETCHED_AT}}

   record = {
      "name": name,
      "purpose": purpose,
      "kind": kind,
      "capabilities": capabilities,
      "input_schema": input_schema,
      "output_schema": output_schema,
      "depends_on": depends_on,
      "pagination": pagination,
      "requests": requests,
      "failure_classes": failure_classes,
      "confirmation": confirmation,
      "open_steps": open_steps,
      "live_policy": live_policy,
      "tier": tier,
      "readiness": "planned",
   }

   if notes:
      record["notes"] = notes

   COMMANDS.append(record)


def replay(endpoint_id, budget=2):
   return {"step": "replay {0} twice and record two kb verify passes".format(endpoint_id), "budget": budget, "endpoint": endpoint_id}


def discover(endpoint_id, what, budget=2):
   return {"step": "observe {0} live for the first time: {1}".format(endpoint_id, what), "budget": budget, "endpoint": endpoint_id}


ROUND_TRIP = "Round-trip write: read state, write, read back, run the exact inverse, read back to the starting state. Runs live only under the standing overnight grant; otherwise ask in chat for the exact call, then --yes --confirm <digest from the dry run>."
APPROVAL = "Approval write: never sent without your approval of the exact --dry-run call in chat, then --yes --confirm <digest from that dry run>; listed in PENDING-APPROVALS.md."
SESSION_NOTE = "Needs your Citymapper session (sessionid in .env via adopt-session). You are signed out, so this is blocked until you sign in yourself."

# Local and catalogue

command("help", "List every command with inputs, outputs, kind, readiness and the session status", "read", [], obj({}), obj({"commands": arr(obj({"name": STRING, "kind": STRING, "readiness": STRING})), "session": ANY_OBJECT}, ["commands"]), [], 0, [], "local", "base")
command("adopt-session", "Store your Citymapper session cookies from stdin or a file into .env (mode 600); never from argv", "write", ["cap-user-data"], obj({"from_file": STRING, "stdin": BOOLEAN}), obj({"stored": arr(STRING), "path": STRING, "lengths": {"type": "object", "description": "cookie name to value length; never the value"}}, ["stored"]), [], 0, [], "local", "base", confirmation="local only: writes .env, sends nothing; prints cookie names and lengths, never values", notes="Reads a Cookie header or document.cookie string; keeps sessionid, csrftoken, uid.")
command("list-cities", "List every supported region and city, with ids, slugs and whether routing is enabled", "read", ["cap-list-cities", "cap-switch-city"], obj({"refresh": BOOLEAN, "query": STRING}), obj({"fetched_at": {"type": ["number", "null"], "description": "when the cached catalogue was fetched, in Unix seconds"}, "regions": arr(obj({"region_id": STRING, "slug": STRING, "name": STRING, "aliases": arr(STRING), "api_enabled": BOOLEAN, "bounding_box": ANY_OBJECT, "cities": arr(obj({"city_id": STRING, "slug": STRING, "name": STRING}))}, ["region_id", "slug", "name"]))}, ["regions"]), depends("cities-html", "city-html"), 1, [replay("cities-html")], "public", "base", notes="Parses window.citymapper.regions and citiesInRegions from one page; cached under var/cache for 7 days; --refresh refetches.")
command("get-city", "Get one region's configuration: nearby modes, brands, bounding box, timezone, default place", "read", ["cap-city-info"], obj({"city": CITY}, ["city"]), obj({"region_id": STRING, "slug": STRING, "name": STRING, "timezone": STRING, "bounding_box": ANY_OBJECT, "default_place": ANY_OBJECT, "nearby_modes": arr(obj({"mode_id": STRING, "slug": STRING, "title": STRING, "brand_ids": arr(STRING), "kinds": arr(STRING)})), "core_brand_ids": arr(STRING), "distance_units": NULLABLE_STRING, "api_enabled": BOOLEAN}, ["region_id", "nearby_modes"]), depends("resource-region-info", "city-html"), 1, [replay("resource-region-info")], "public", "base", notes="Every other command resolves --city through the cached catalogue and this config.")
command("list-brands", "List transport brands (operators) from the brand directory, optionally for one city", "read", ["cap-brand-directory"], obj({"city": CITY, "query": STRING}), obj({"brands": arr(obj({"id": STRING, "name": NULLABLE_STRING, "affinities": arr(STRING), "departure_apis": arr(STRING)}, ["id"]))}, ["brands"]), depends("resource-brand-directory"), 1, [replay("resource-brand-directory")], "public", "rest")

# Tier 1: journey planning

command("search-places", "Search places, addresses, stations and stops in a city (autocomplete)", "read", ["cap-search-places"], obj({"city": CITY, "query": STRING, "near": PLACE_INPUT, "limit": LIMIT}, ["city", "query"]), obj({"query": STRING, "results": arr(PLACE)}, ["results"]), depends("searchpost"), 1, [replay("searchpost")], "public", "journey")
command("resolve-place", "Resolve a search result id to coordinates and an address", "read", ["cap-resolve-place"], obj({"city": CITY, "id": STRING}, ["city", "id"]), obj({"place": PLACE}, ["place"]), depends("placeresolve"), 1, [discover("placeresolve", "id format of a Google result without coords")], "public", "journey")
command("reverse-geocode", "Name the address at a coordinate", "read", ["cap-reverse-geocode"], obj({"lat": NUMBER, "lng": NUMBER}, ["lat", "lng"]), obj({"address": NULLABLE_STRING, "name": NULLABLE_STRING, "components": arr(STRING), "coords": COORDS}, ["address", "coords"]), depends("geocode"), 1, [discover("geocode", "response shape")], "public", "journey")
command("plan-journey", "Plan transit journeys between two places, leaving now, at a time, or arriving by a time", "read", ["cap-plan-journey"], JOURNEY_IN, JOURNEY_OUT, depends("journeys", "searchpost"), 1, [replay("journeys")], "public", "journey", pagination="time-window-journeys", notes="Text places cost one searchpost each. Output keeps the journey signature for get-journey-times, get-journey and share-journey.")
command("plan-walk", "Plan walking routes between two places", "read", ["cap-plan-walk"], JOURNEY_IN, JOURNEY_OUT, depends("walk7", "walk1"), 1, [replay("walk7")], "public", "journey", notes="Uses /api/7/walk; /api/1/walk is the older form kept as a fallback dependency.")
command("plan-cycle", "Plan cycling routes with your own bike or bike share", "read", ["cap-plan-cycle"], JOURNEY_IN, JOURNEY_OUT, depends("cycle"), 1, [replay("cycle")], "public", "journey")
command("plan-cab", "Estimate cab and on-demand rides between two places", "read", ["cap-plan-cab"], CAB_IN, obj({"region_id": STRING, "from": PLACE, "to": PLACE, "time_mode": STRING, "routes": arr(obj({"mode": STRING, "duration_seconds": INTEGER, "distance_meters": NULLABLE_INTEGER})), "services": arr(obj({"name": STRING, "category": NULLABLE_STRING}))}, ["routes"]), depends("taxi"), 1, [replay("taxi")], "public", "journey")
command("plan-vehicle-hire", "Plan journeys with hire vehicles (scooters, bikes, car share)", "read", ["cap-plan-vehicle-hire"], JOURNEY_IN, JOURNEY_OUT, depends("vehiclehire"), 1, [discover("vehiclehire", "does it answer for a region with scooters (London)")], "public", "journey")
command("get-journey-times", "Get live departure and arrival times for journeys from a previous plan", "read", ["cap-journey-times"], obj({"city": CITY, "signatures": arr(STRING)}, ["city", "signatures"]), obj({"times": arr(obj({"signature_index": INTEGER, "time": NULLABLE_STRING, "time_mode": STRING, "price": NULLABLE_STRING, "leg_times": arr(ANY_OBJECT), "error": NULLABLE_STRING}, ["signature_index", "time"]))}, ["times"]), depends("journeytimes"), 1, [replay("journeytimes")], "public", "journey", pagination="poll-30s", notes="One call per invocation; never polls.")
command("get-journey", "Re-fetch one journey's full detail from its signature (journey detail page)", "read", ["cap-journey-detail"], obj({"city": CITY, "signature": STRING, "exact": BOOLEAN, "with_paths": BOOLEAN}, ["city", "signature"]), obj({"journey": JOURNEY, "error": NULLABLE_STRING}, ["journey"]), depends("refreshjourneys", "trip-meta"), 1, [discover("refreshjourneys", "body {signatures, time_mode, region_id, status_format}")], "public", "journey")
command("open-trip-link", "Open a shared trip link (citymapper.com/trip/<slug>) as a journey", "read", ["cap-open-shared-trip"], obj({"slug": STRING, "city": CITY}, ["slug"]), obj({"signature": STRING, "journey": JOURNEY}, ["signature"]), depends("gettrip", "refreshjourneys"), 2, [discover("gettrip", "needs a real trip slug; one comes from an approved share-journey, otherwise unverifiable")], "public", "journey")
command("get-travel-time", "Get the travel time between two points", "read", ["cap-travel-time"], obj({"city": CITY, "from": PLACE_INPUT, "to": PLACE_INPUT}, ["city", "from", "to"]), obj({"seconds": NULLABLE_INTEGER, "minutes": NULLABLE_NUMBER, "from": PLACE, "to": PLACE}), depends("traveltime"), 1, [discover("traveltime", "response shape")], "public", "journey")
command("get-shared-eta", "Get the ETA for a journey signature (shared ETA)", "read", ["cap-shared-eta"], obj({"city": CITY, "signature": STRING}, ["city", "signature"]), obj({"eta": NULLABLE_STRING, "raw": ANY_OBJECT}), depends("eta"), 1, [discover("eta", "response shape")], "public", "journey")

# Tier 2: live departures and stops

command("find-nearby", "List nearby stops, stations, piers or bike docks for one mode around a place", "read", ["cap-nearby"], obj({"city": CITY, "near": PLACE_INPUT, "mode": {"type": "string", "description": "mode slug from get-city (subway, bus, bike, rail, ferry, tube, metro, ...)"}, "limit": LIMIT}, ["city", "near", "mode"]), obj({"mode_id": STRING, "near": PLACE, "elements": arr(NEARBY_ELEMENT)}, ["elements"]), depends("nearby3", "nearby2"), 1, [replay("nearby3")], "public", "departures", pagination="limit-50")
command("get-stop", "Get a stop or station's details: routes, exits and which departures feed it uses", "read", ["cap-stop-info"], obj({"city": CITY, "stop": STOP}, ["city", "stop"]), obj({"id": STRING, "alias": NULLABLE_STRING, "name": STRING, "coords": COORDS, "routes": arr(ROUTE_REF), "exits": arr(obj({"id": STRING, "name": STRING, "coords": COORDS})), "departure_api": NULLABLE_STRING, "url": NULLABLE_STRING}, ["id", "name"]), depends("stopinfo"), 1, [replay("stopinfo")], "public", "departures")
command("get-departures", "Get live departures at a stop or station (bus, metro, rail, ferry)", "read", ["cap-live-departures"], obj({"city": CITY, "stop": STOP, "route": STRING, "limit": LIMIT}, ["city", "stop"]), obj({"stop": obj({"id": STRING, "name": STRING}), "feed": STRING, "updated": {"type": ["string", "null"], "description": "the feed's last update time, or when the departures request was sent if the feed gives none (bus feeds)"}, "departures": arr(DEPARTURE)}, ["stop", "feed", "departures"]), depends("stopinfo", "departures-bus", "departures-metro", "departures-rail"), 2, [replay("departures-metro"), replay("departures-bus"), replay("departures-rail")], "public", "departures", pagination="poll-30s", notes="stopinfo picks the feed from sharing_urls[].departure_api; one snapshot per call, never polled.")
command("get-stop-schedule", "Get a stop's timetable for a time", "read", ["cap-stop-schedule"], obj({"city": CITY, "stop": STOP, "time": {"type": "string", "description": "HH:MM in the city's timezone (today, or tomorrow once more than 15 minutes past) or ISO 8601 for any other day"}}, ["city", "stop"]), obj({"stop": STRING, "raw": ANY_OBJECT}), depends("schedules"), 1, [discover("schedules", "id format and response shape")], "public", "departures")

# Tier 3: disruptions and status

command("get-line-status", "Get the status of every line in a city, grouped by mode", "read", ["cap-line-status"], obj({"city": CITY, "mode": STRING}, ["city"]), obj({"updated": NULLABLE_STRING, "groups": arr(obj({"id": STRING, "name": STRING, "lines": arr(LINE_SUMMARY)}))}, ["groups"]), depends("routestatus"), 1, [replay("routestatus")], "public", "disruptions", pagination="poll-2min")
command("get-disruptions", "List current disruptions in a city with readable descriptions and affected stops", "read", ["cap-disruptions"], obj({"city": CITY, "min_level": INTEGER, "line": LINE}, ["city"]), obj({"updated": NULLABLE_STRING, "disruptions": arr(obj({"line": STRING, "line_name": NULLABLE_STRING, "group": STRING, "level": INTEGER, "summary": STRING, "description": STRING, "stops": arr(STRING)}, ["line", "level", "summary", "description"]))}, ["disruptions"]), depends("routestatus", "routeinfo2"), 1, [replay("routestatus")], "public", "disruptions", notes="Fills {n} placeholders from replacements.")
command("get-service-message", "Read the site-wide service message for a city", "read", ["cap-message"], obj({"city": CITY}, ["city"]), obj({"messages": arr(ANY_OBJECT)}, ["messages"]), depends("message"), 1, [replay("message")], "public", "disruptions")

# Tier 4: lines, maps and the rest

command("find-line", "Find a bus or line by name or number in a city", "read", ["cap-find-line"], obj({"city": CITY, "query": STRING}, ["city", "query"]), obj({"lines": arr(LINE_SEARCH_RESULT)}, ["lines"]), depends("findtransport"), 1, [discover("findtransport", "response body (only the URL was seen)")], "public", "rest")
command("get-line", "Get a line's branches, ordered stops, path and status", "read", ["cap-line-info"], obj({"city": CITY, "line": LINE, "with_paths": BOOLEAN}, ["city", "line"]), obj({"line": LINE_SUMMARY, "patterns": arr(obj({"id": STRING, "name": STRING, "stops": arr(obj({"id": STRING, "name": STRING, "coords": COORDS})), "path": arr(COORDS)})), "stops": arr(obj({"id": STRING, "name": STRING, "coords": COORDS}))}, ["line", "patterns"]), depends("routeinfo1"), 1, [replay("routeinfo1")], "public", "rest")
command("get-lines", "Get several lines at once with status", "read", ["cap-lines-info"], obj({"city": CITY, "lines": arr(STRING)}, ["city", "lines"]), obj({"lines": arr(LINE_SUMMARY)}, ["lines"]), depends("routeinfo2"), 1, [replay("routeinfo2")], "public", "rest")
command("get-vehicles", "Get live vehicle positions on a line where the city publishes them", "read", ["cap-vehicle-locations"], obj({"city": CITY, "line": LINE}, ["city", "line"]), obj({"line": obj({"id": STRING, "name": STRING}), "vehicles": arr(ANY_OBJECT)}, ["vehicles"]), depends("vehiclelocations"), 1, [discover("vehiclelocations", "a line with live_availability > 0")], "public", "rest", pagination="poll-10s")
command("get-route-paths", "Get map paths for lines", "read", ["cap-route-paths"], obj({"city": CITY, "lines": arr(STRING)}, ["city", "lines"]), obj({"paths": arr(ANY_OBJECT)}, ["paths"]), depends("routepaths"), 1, [discover("routepaths", "response shape")], "public", "rest")
command("get-map-around", "Get everything Citymapper draws on the map around a point", "read", ["cap-everything-map"], obj({"city": CITY, "near": PLACE_INPUT, "size": {"type": "string", "enum": ["small", "large"], "description": "tile size; small is the area around the point, large the wider network"}}, ["city", "near", "size"]), obj({"elements": arr(ANY_OBJECT)}, ["elements"]), depends("everythingmap"), 1, [discover("everythingmap", "response shape")], "public", "rest", notes="size must be a name: small and large answer 200; 500 answers 400 Unknown tile size (replay 2026-10-10).")
command("get-weather", "Get the weather at a place", "read", ["cap-weather"], obj({"city": CITY, "near": PLACE_INPUT, "units": STRING}, ["city"]), obj({"raw": ANY_OBJECT}), depends("weather"), 1, [discover("weather", "response shape")], "public", "rest")
command("get-transit-score", "Get Citymapper's transit score for a place", "read", ["cap-transit-score"], obj({"city": CITY, "near": PLACE_INPUT}, ["near"]), obj({"score": NULLABLE_NUMBER, "raw": ANY_OBJECT}), depends("transitscore"), 1, [discover("transitscore", "response shape")], "public", "rest")
command("open-go-link", "Open a Meet Me Somewhere link (citymapper.com/go/<slug>)", "read", ["cap-open-go-link"], obj({"slug": STRING}, ["slug"]), obj({"name": NULLABLE_STRING, "coords": NULLABLE_COORDS, "address": NULLABLE_STRING, "raw": ANY_OBJECT}), depends("getshorturl"), 1, [discover("getshorturl", "needs a real go slug; one comes from an approved create-go-link")], "public", "rest")
command("list-news", "List Citymapper news posts, or read one", "read", ["cap-news"], obj({"id": STRING, "limit": LIMIT}), obj({"posts": arr(obj({"id": STRING, "title": STRING, "url": STRING, "summary": NULLABLE_STRING, "date": NULLABLE_STRING}))}, ["posts"]), depends("news-html", "blog"), 1, [replay("news-html"), discover("blog", "does /api/1/blog still answer")], "public", "rest")
command("get-legal", "Read the terms of service or the privacy policy", "read", ["cap-legal"], obj({"document": {"type": "string", "enum": ["terms", "privacy"]}}, ["document"]), obj({"title": STRING, "text": STRING, "url": STRING}, ["text"]), depends("resources"), 1, [discover("resources", "content type and redirect")], "public", "rest")

# Account reads (blocked until you sign in)

command("whoami", "Show the signed-in Citymapper user, or that you are signed out", "read", ["cap-user-data"], obj({}), obj({"signed_in": BOOLEAN, "user": ANY_OBJECT}, ["signed_in"]), depends("identity-user-data"), 1, [replay("identity-user-data")], "session", "account", notes="Signed out it returns signed_in false from the 403 (verifiable now).")
command("list-saved-places", "List your saved places (home, work and others)", "read", ["cap-saved-places"], obj({}), obj({"places": arr(obj({"id": STRING, "name": STRING, "role": NULLABLE_STRING, "address": NULLABLE_STRING, "coords": NULLABLE_COORDS, "region": NULLABLE_STRING}))}, ["places"]), depends("identity-places-list"), 1, [replay("identity-places-list")], "session", "account", notes=SESSION_NOTE)
command("list-favourites", "List your favourite stops, stations and lines", "read", ["cap-favourites"], obj({"city": CITY}), obj({"favourites": arr(obj({"id": STRING, "type": STRING, "target_id": STRING, "name": NULLABLE_STRING, "region_id": NULLABLE_STRING}))}, ["favourites"]), depends("identity-favorites-list"), 1, [replay("identity-favorites-list")], "session", "account", notes=SESSION_NOTE)
command("pass-account", "Show your Citymapper Pass payment account (payment methods)", "read", ["cap-pass-payments"], obj({"provider": STRING, "use_web_session_id": USE_WEB_SESSION_ID}), obj({"raw": ANY_OBJECT}), depends("turnstile-userinfo"), 1, [discover("turnstile-userinfo", "needs a Pass session id from the app")], "session", "account", notes=PASS_NOTE)
command("pass-session-time", "Show how long the Pass session has left", "read", ["cap-pass-payments"], obj({"use_web_session_id": USE_WEB_SESSION_ID}), obj({"seconds": NULLABLE_INTEGER, "raw": ANY_OBJECT}), depends("turnstile-sessionttl"), 1, [discover("turnstile-sessionttl", "needs a Pass session id from the app")], "session", "account", notes=PASS_NOTE)

# Account round-trip writes

command("save-place", "Save a place to your account (optionally as home or work)", "write", ["cap-save-place"], obj({"name": STRING, "near": PLACE_INPUT, "city": CITY, "role": {"type": "string", "enum": ["home", "work"]}, **WRITE_IN_YES}, ["name", "near", "city"]), obj({"place": ANY_OBJECT, **DRY_RUN["properties"]}), depends("identity-places-create", "identity-places-list"), 2, [discover("identity-places-create", "body shape and returned place_id")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: remove-place with the returned id.", notes=SESSION_NOTE)
command("update-place", "Rename or move a saved place", "write", ["cap-update-place"], obj({"id": STRING, "name": STRING, "near": PLACE_INPUT, "city": CITY, **WRITE_IN_YES}, ["id"]), obj({"place": ANY_OBJECT, **DRY_RUN["properties"]}), depends("identity-places-update", "identity-places-list"), 2, [discover("identity-places-update", "PUT body")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: update-place with the values read before.", notes=SESSION_NOTE)
command("remove-place", "Remove a saved place", "write", ["cap-remove-place"], obj({"id": STRING, **WRITE_IN_YES}, ["id"]), obj({"removed": BOOLEAN, **DRY_RUN["properties"]}), depends("identity-places-delete", "identity-places-list"), 2, [discover("identity-places-delete", "status of a DELETE")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: save-place with the fields read before (the id changes).", notes=SESSION_NOTE)
command("add-favourite", "Favourite a stop, station or line", "write", ["cap-favourite-stop", "cap-favourite-line"], obj({"city": CITY, "stop": STOP, "line": LINE, **WRITE_IN_YES}, ["city"]), obj({"favourite": ANY_OBJECT, **DRY_RUN["properties"]}), depends("identity-favorites-create", "identity-favorites-list"), 2, [discover("identity-favorites-create", "body {target_type, target_id, region_id}")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: remove-favourite with the returned id.", notes=SESSION_NOTE)
command("remove-favourite", "Remove a favourite stop, station or line", "write", ["cap-favourite-stop", "cap-favourite-line"], obj({"id": STRING, **WRITE_IN_YES}, ["id"]), obj({"removed": BOOLEAN, **DRY_RUN["properties"]}), depends("identity-favorites-delete", "identity-favorites-list"), 2, [discover("identity-favorites-delete", "status of a DELETE")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: add-favourite with the same target.", notes=SESSION_NOTE)
command("save-journey", "Send a journey to your phone (save it to your account)", "write", ["cap-save-journey"], obj({"city": CITY, "signature": STRING, **WRITE_IN_YES}, ["city", "signature"]), obj({"document_id": STRING, "raw": ANY_OBJECT, **DRY_RUN["properties"]}), depends("identity-save-journey"), 1, [discover("identity-save-journey", "document_data shape and returned document_id")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: remove-saved-journey with the returned document_id (no list endpoint, so the id must come from the save response).", notes=SESSION_NOTE + " The app may notify your phone, which is a side effect the inverse cannot undo; treat as approval if the save sends a push.")
command("remove-saved-journey", "Remove a journey you sent to your phone", "write", ["cap-save-journey"], obj({"document_id": STRING, **WRITE_IN_YES}, ["document_id"]), obj({"removed": BOOLEAN, **DRY_RUN["properties"]}), depends("identity-delete-journey"), 1, [discover("identity-delete-journey", "status of a DELETE")], "session", "account-writes", confirmation=ROUND_TRIP + " Only for a document this program saved; otherwise a delete without inverse needs approval.", notes=SESSION_NOTE)
command("update-profile", "Update your first name, last name, mobile or Pass interest", "write", ["cap-update-user"], obj({"first_name": STRING, "last_name": STRING, "mobile": STRING, "interested_in_pass": BOOLEAN, **WRITE_IN_YES}), obj({"user": ANY_OBJECT, **DRY_RUN["properties"]}), depends("identity-update-user", "identity-user-data"), 2, [discover("identity-update-user", "fields echoed back")], "session", "account-writes", confirmation=ROUND_TRIP + " Inverse: update-profile with the values read from whoami.", notes=SESSION_NOTE)

# Approval writes

command("share-journey", "Create a public share link for a journey", "write", ["cap-share-trip"], obj({"city": CITY, "signature": STRING, **WRITE_IN_YES}, ["city", "signature"]), obj({"url": STRING, **DRY_RUN["properties"]}), depends("createtripurl"), 1, [discover("createtripurl", "only after your approval")], "public", "approval", confirmation=APPROVAL + " Visible to anyone with the link; no delete exists.")
command("create-go-link", "Create a public Meet Me Somewhere link to a place (title and message unverified)", "write", ["cap-create-go-link"], obj({"city": CITY, "place": PLACE_INPUT, "title": {"type": "string", "description": "unverified: the web client always sends an empty title, so Citymapper may drop it"}, "message": {"type": "string", "description": "unverified: the web client always sends an empty message, so Citymapper may drop it"}, **WRITE_IN_YES}, ["city", "place", "title"]), obj({"url": STRING, "slug": STRING, "title": {"type": ["string", "null"], "description": "the title as Citymapper echoed it back, or null"}, "message": {"type": ["string", "null"], "description": "the message as Citymapper echoed it back, or null"}, "warning": {"type": ["string", "null"], "description": "set when a title or message you sent was not echoed back"}, **DRY_RUN["properties"]}), depends("createshorturl"), 1, [discover("createshorturl", "only after your approval")], "public", "approval", confirmation=APPROVAL + " Visible to anyone with the link; no delete exists.")
command("vote-for-city", "Vote for Citymapper to launch in a new city (sends your e-mail)", "write", ["cap-city-vote"], obj({"city_slug": STRING, "email": STRING, **WRITE_IN_YES}, ["city_slug", "email"]), obj({"ok": BOOLEAN, **DRY_RUN["properties"]}), depends("city-vote"), 1, [discover("city-vote", "only after your approval; needs the csrftoken cookie")], "session", "approval", confirmation=APPROVAL + " Sends personal data (e-mail) to Citymapper.", notes=SESSION_NOTE + " The vote also needs the csrftoken cookie: the bundle requires X-CSRFToken and the web gives no other source for it, so the program sends your stored csrftoken as both the cookie and the header.")
command("sign-out", "Sign this program's Citymapper session out", "write", ["cap-sign-out"], obj(WRITE_IN_YES), obj({"signed_out": BOOLEAN, **DRY_RUN["properties"]}), depends("identity-sessions-delete"), 1, [discover("identity-sessions-delete", "only after your approval")], "session", "approval", confirmation=APPROVAL + " No inverse: signing back in is yours to do.", notes=SESSION_NOTE)
command("pass-set-default-payment", "Set the default Citymapper Pass payment method", "write", ["cap-pass-payments"], obj({"payment_method_id": STRING, "provider": STRING, "use_web_session_id": USE_WEB_SESSION_ID, **WRITE_IN_YES}, ["payment_method_id", "provider"]), obj({"raw": ANY_OBJECT, **DRY_RUN["properties"]}), depends("turnstile-setdefaultpaymentmethod"), 1, [discover("turnstile-setdefaultpaymentmethod", "blocked: Pass session id is app-only")], "session", "approval", confirmation=APPROVAL + " Payment setting.", notes=PASS_NOTE + " Approval only.")
command("pass-add-payment-method", "Attach a payment method to Citymapper Pass", "write", ["cap-pass-payments"], obj({"payment_method_id": STRING, "provider": STRING, "use_web_session_id": USE_WEB_SESSION_ID, **WRITE_IN_YES}, ["payment_method_id", "provider"]), obj({"raw": ANY_OBJECT, **DRY_RUN["properties"]}), depends("turnstile-addpaymentmethod"), 1, [discover("turnstile-addpaymentmethod", "blocked: Pass session id is app-only")], "session", "approval", confirmation=APPROVAL + " Payment setting; the payment method token must come from the provider, never typed here.", notes=PASS_NOTE + " Approval only.")
command("pass-remove-payment-method", "Remove a Citymapper Pass payment method", "write", ["cap-pass-payments"], obj({"payment_method_id": STRING, "provider": STRING, "use_web_session_id": USE_WEB_SESSION_ID, **WRITE_IN_YES}, ["payment_method_id", "provider"]), obj({"raw": ANY_OBJECT, **DRY_RUN["properties"]}), depends("turnstile-deletepaymentmethod"), 1, [discover("turnstile-deletepaymentmethod", "blocked: Pass session id is app-only")], "session", "approval", confirmation=APPROVAL + " Delete without inverse.", notes=PASS_NOTE + " Approval only.")
command("pass-remove-all-payment-methods", "Remove every Citymapper Pass payment method for a provider", "write", ["cap-pass-payments"], obj({"provider": STRING, "use_web_session_id": USE_WEB_SESSION_ID, **WRITE_IN_YES}, ["provider"]), obj({"raw": ANY_OBJECT, **DRY_RUN["properties"]}), depends("turnstile-deleteallpaymentmethods"), 1, [discover("turnstile-deleteallpaymentmethods", "blocked: Pass session id is app-only")], "session", "approval", confirmation=APPROVAL + " Delete without inverse.", notes=PASS_NOTE + " Approval only.")

NOT_PLANNED = [
   {"capability": "cap-sign-in", "reason": "Signing in or up (magic link, Google or Facebook) can create an account and grants OAuth; the brief's hard limits forbid it. You sign in yourself, then adopt-session stores the cookie."},
   {"capability": "cap-password-reset", "reason": "Password reset and sign-up confirmation are account-security e-mail flows; the hard limits forbid changing account security, and the web has no password sign-in."},
   {"capability": "cap-telemetry", "reason": "Analytics (POST /api/2/logevents) is noise; the program never sends it."},
]

TIER_ORDER = [
   ("base", "transport, pacer, classifier, session store, city catalogue and resolver", "help lists every command; list-cities returns 115 regions live; get-city returns nearby_modes for nyc and london"),
   ("journey", "tier 1 reads: journey planning, search and journey times", "plan-journey live in at least 3 cities (now, depart-at, arrive-by) with times in order and legs typed; search-places live"),
   ("departures", "tier 2 reads: nearby, stops and live departures for bus, metro and rail", "get-departures live for a bus stop, a metro station and a rail station; departures typed, seconds non-negative"),
   ("disruptions", "tier 3 reads: line status, disruptions, service message", "get-disruptions live in nyc and london with placeholders filled"),
   ("rest", "remaining public reads: lines, maps, weather, news, legal, brands", "each command live once and its schema checked; bundle-only endpoints that no longer answer are recorded as blocked with the response"),
   ("account", "account reads, blocked until you sign in", "whoami signed-out path live; the rest built, offline tested, blocked on session"),
   ("account-writes", "round-trip writes with exact inverses", "dry-run and offline tests; live round trip only with a session"),
   ("approval", "approval writes: public links, city vote, sign-out, Pass payments", "dry-run prints the exact request; PENDING-APPROVALS.md lists each"),
]


def apply_readiness(commands):
   readiness_file = ROOT / "var/state/readiness.json"

   try:
      states = json.loads(readiness_file.read_text())
   except (FileNotFoundError, ValueError):
      states = {}

   for record in commands:
      still_open = []

      for step in record["open_steps"]:
         finding = finding_state(step.get("endpoint", ""))
         is_closed = (finding["state"] == "verified" and finding["verify_count"] >= 2) or finding["state"] == "dead"
         if not is_closed:
            still_open.append(step)

      record["open_steps"] = still_open
      state = states.get(record["name"])
      if record["live_policy"] == "local":
         record["readiness"] = "local"
      elif state:
         record["readiness"] = state["status"]
         if state.get("log"):
            record["evidence"] = state["log"]


def capability_coverage():
   covered = {capability for command_record in COMMANDS for capability in command_record["capabilities"]}
   skipped = {item["capability"] for item in NOT_PLANNED}
   missing = [capability["id"] for capability in SCOPE["capabilities"] if capability["id"] not in covered | skipped]
   return missing


def table(headers, rows):
   lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]

   for row in rows:
      cells = [str(cell).replace("|", "/").replace("\n", " ") for cell in row]
      lines.append("| " + " | ".join(cells) + " |")

   return "\n".join(lines)


def render_markdown(plan):
   parts = [
      "# Citymapper plan",
      "",
      "Generated {0} from scope/scope.json ({1}). Program `{2}` (package `{3}`), CLI `{4}`, central skill `/{5}`.".format(plan["generated"], plan["scope_generated"], "program/", plan["program"]["package"], plan["program"]["cli"], plan["skill_name"]),
      "",
      "## Defaults",
      "",
      "- Output: JSON on stdout by default, `--format table` for people; errors as JSON on stderr with a class and an exit code.",
      "- City: every command takes `--city` (slug, region id, city slug or name), resolved from the cached catalogue.",
      "- Pacing: {0}.".format(plan["program"]["pacing"]),
      "- Session: {0}.".format(plan["program"]["session"]),
      "- Writes: `--dry-run` prints the exact request and its `confirm` digest; `--yes --confirm <digest>` is required to send, and a request that differs from the approved dry run is refused. Round-trip writes have an implemented inverse; approval writes go to PENDING-APPROVALS.md.",
      "",
      "## Commands",
      "",
      table(["Command", "Kind", "Tier", "Live policy", "Readiness", "Endpoints (state)", "Requests", "Purpose"], [(item["name"], item["kind"], item["tier"], item["live_policy"], item["readiness"], ", ".join("{0} ({1})".format(dep["endpoint"], dep["state"]) for dep in item["depends_on"]), item["requests"], item["purpose"]) for item in plan["commands"]]),
      "",
      "## Build order",
      "",
      table(["Step", "Do", "Commands", "Exit check"], [(step["step"], step["do"], ", ".join(step["commands"]), step["exit_check"]) for step in plan["build_order"]]),
      "",
      "## Not planned",
      "",
      table(["Capability", "Reason"], [(item["capability"], item["reason"]) for item in plan["not_planned"]]),
      "",
      "## Open reverse-engineering steps",
      "",
      table(["Command", "Step", "Budget"], [(item["name"], step["step"], step["budget"]) for item in plan["commands"] for step in item["open_steps"]]),
      "",
      "## Risks",
      "",
   ]
   parts += ["- " + risk for risk in plan["risks"]]
   parts.append("")
   return "\n".join(parts)


def build():
   missing = capability_coverage()

   if missing:
      sys.exit("refusing to write: capabilities with no command and no reason: " + ", ".join(missing))

   apply_readiness(COMMANDS)
   build_order = []
   for position, (tier, description, exit_check) in enumerate(TIER_ORDER, start=1):
      names = [item["name"] for item in COMMANDS if item["tier"] == tier]
      build_order.append({"step": position, "do": description, "commands": names, "exit_check": exit_check})

   plan = {
      "site": "citymapper",
      "skill_name": "citymapper",
      "generated": GENERATED,
      "scope_generated": SCOPE["generated"],
      "program": {
         "language": "python",
         "package": "citymapper_client",
         "cli": "citymapper",
         "session": "optional; cookies (sessionid, csrftoken, uid) adopted from your browser into <root>/.env by adopt-session; public commands send no session",
         "pacing": "one request in flight, 3 s minimum gap per origin with 20 to 40 percent jitter, no automatic retry except transport errors (2, backoff from 5 s), stop on 429 or challenge",
         "output": "json",
      },
      "sub_skills": [],
      "commands": COMMANDS,
      "build_order": build_order,
      "not_planned": NOT_PLANNED,
      "risks": [
         "You are signed out of citymapper.com; {0} session commands stay blocked until you sign in yourself and run adopt-session (whoami still answers signed out).".format(sum(1 for item in COMMANDS if item["live_policy"] == "session")),
         "Citymapper Pass and Club are paid and app-only; the six pass-* commands are blocked even with a web session.",
         "15 endpoints were read from the bundle and never observed; some may be retired upstream (each is replayed once in engineer).",
         "Live transit values change every request; checks are on schemas and invariants only.",
         "Cloudflare fronts the site; unknown rate thresholds; the pacer stops the client on any 429 or challenge.",
         "City pages are 2 to 15 MB of HTML; the catalogue must be cached, never fetched per command.",
      ],
   }

   (ROOT / "plan").mkdir(exist_ok=True)
   (ROOT / "plan/plan.json").write_text(json.dumps(plan, indent=3) + "\n")
   (ROOT / "plan/plan.md").write_text(render_markdown(plan))
   print("wrote plan.json and plan.md: {0} commands, {1} not planned".format(len(COMMANDS), len(NOT_PLANNED)))


if __name__ == "__main__":
   build()
