from .. import endpoints
from ..context import resolve_place as resolve_search_result
from ..context import place_query_key, search
from ..errors import ContractBroken, NotFound, UsageError
from ..models import Journey, Place, coords_of, require, require_list

RETIRED_VEHICLE_HIRE = "Citymapper retired /api/7/vehiclehire: it answers 404 {\"error\": \"This API is no longer supported\"} for London and Paris (replay 2026-10-10)."
RETIRED_ETA = "Citymapper's /api/1/eta answers 404 with its 'Page Not Found' HTML for a fresh journey signature (replay 2026-10-10); shared ETAs exist only in the app."


def journey_query(context, region, arguments):
   depart_at = arguments.get("depart_at")
   arrive_by = arguments.get("arrive_by")

   if depart_at and arrive_by:
      raise UsageError("Pass --depart-at or --arrive-by, not both.")

   departure_time = context.to_utc_iso(region, depart_at)
   arrival_time = context.to_utc_iso(region, arrive_by)
   start = context.place(region, arguments.get("from"), "from")
   end = context.place(region, arguments.get("to"), "to")

   query = {
      "start": "{0},{1}".format(*start.coords),
      "end": "{0},{1}".format(*end.coords),
      "sname": start.name,
      "ename": end.name,
      "saddr": start.address,
      "eaddr": end.address,
      "region_id": region["region_id"],
      "departure_time": departure_time,
      "arrival_time": arrival_time,
      "include_stepfree": "1",
      "include_via_microtransit": "1",
      "status_format": "html",
   }
   time_mode = "arrive_by" if arrive_by else ("depart_at" if depart_at else "now")
   requested_time = query["arrival_time"] or query["departure_time"]
   return query, start, end, time_mode, requested_time


def journeys_output(region, start, end, time_mode, requested_time, response, arguments):
   journeys = [Journey.from_api(index, journey, include_path=bool(arguments.get("with_paths"))) for index, journey in enumerate(require_list(response, "journeys", "journeys response"))]
   wants_step_free = bool(arguments.get("step_free"))

   if wants_step_free:
      journeys = [journey for journey in journeys if journey.step_free]

   limit = arguments.get("limit")
   kept = journeys[:limit] if limit else journeys
   kept_indexes = {journey.index for journey in kept}
   sections = []

   for section in response.get("sections") or []:
      indexes = [index for index in section.get("journeys") or [] if index in kept_indexes]
      sections.append({"id": section.get("id", ""), "name": section.get("name", ""), "journey_indexes": indexes})

   return {
      "city": region["slug"],
      "region_id": region["region_id"],
      "from": start.as_dict(),
      "to": end.as_dict(),
      "time_mode": time_mode,
      "requested_time": requested_time,
      "sections": sections,
      "journeys": [journey.as_dict() for journey in kept],
   }


def plan_with(endpoint, context, arguments, extra_query=None):
   region = context.region(arguments.get("city"))
   query, start, end, time_mode, requested_time = journey_query(context, region, arguments)
   query.update(extra_query or {})
   response = context.send(endpoint, query=query)
   return journeys_output(region, start, end, time_mode, requested_time, response, arguments)


def plan_journey(context, arguments):
   return plan_with(endpoints.JOURNEYS, context, arguments)


def plan_walk(context, arguments):
   return plan_with(endpoints.WALK, context, arguments, {"limit": "2"})


def plan_cycle(context, arguments):
   return plan_with(endpoints.CYCLE, context, arguments)


def plan_cab(context, arguments):
   region = context.region(arguments.get("city"))
   query, start, end, time_mode, requested_time = journey_query(context, region, arguments)
   response = context.send(endpoints.TAXI, query=query)
   routes = []

   for route in require_list(response, "routes", "cab response"):
      routes.append({"mode": route.get("mode", "taxi"), "duration_seconds": int(require(route, "duration_seconds", "cab route")), "distance_meters": route.get("length_meters")})

   services = []
   for category in (response.get("on_demand_model") or {}).get("categories") or []:
      for entry in category.get("entries") or []:
         services.append({"name": entry.get("title") or entry.get("service_id", ""), "category": entry.get("parent_service_id")})

   limit = arguments.get("limit")

   if limit:
      routes = routes[:limit]
      services = services[:limit]

   return {"region_id": region["region_id"], "from": start.as_dict(), "to": end.as_dict(), "time_mode": time_mode, "routes": routes, "services": services}


def plan_vehicle_hire(context, arguments):
   raise NotFound(RETIRED_VEHICLE_HIRE, {"blocked": "retired upstream"})


def get_journey_times(context, arguments):
   region = context.region(arguments.get("city"))
   signatures = arguments.get("signatures") or []

   if not signatures:
      raise UsageError("Pass --signatures from a plan-journey result.")

   response = context.send(endpoints.JOURNEY_TIMES, query={"region_id": region["region_id"]}, json_body={"signatures": signatures})
   times = []

   for index, item in enumerate(require_list(response, "journey_times", "journey times response")):
      entry = item if isinstance(item, dict) else {}
      times.append({"signature_index": index, "time": entry.get("time"), "time_mode": entry.get("time_mode", ""), "price": entry.get("formatted_price"), "leg_times": entry.get("leg_times") or [], "error": entry.get("error") or (None if entry.get("time") else "Citymapper returned no time for this journey")})

   return {"times": times}


def get_journey(context, arguments):
   region = context.region(arguments.get("city"))
   signature = arguments.get("signature")

   if not signature:
      raise UsageError("Pass --signature from a plan-journey result.")

   time_mode = "SIGNATURE_EXACT" if arguments.get("exact") else "SIGNATURE"
   body = {"signatures": [signature], "time_mode": time_mode, "region_id": region["region_id"], "status_format": "html"}
   response = context.send(endpoints.REFRESH_JOURNEYS, query={"region_id": region["region_id"]}, json_body=body)
   refreshed = require_list(response, "refreshed_journeys", "refresh response")

   if not refreshed:
      raise ContractBroken("refreshjourneys returned no journey.", {})

   first = refreshed[0]
   journey = first.get("journey")

   if not journey:
      return {"journey": None, "error": str(first.get("error") or "no journey")}

   return {"journey": Journey.from_api(0, journey, include_path=bool(arguments.get("with_paths"))).as_dict(), "error": None}


def open_trip_link(context, arguments):
   slug = arguments.get("slug")

   if not slug:
      raise UsageError("Pass --slug (the part after citymapper.com/trip/).")

   response = context.send(endpoints.GET_TRIP, query={"slug": slug})
   signature = require(response, "signature", "trip link")
   result = {"signature": signature, "journey": None}

   if arguments.get("city"):
      detail = get_journey(context, {"city": arguments["city"], "signature": signature})
      result["journey"] = detail["journey"]

   return result


def get_travel_time(context, arguments):
   region = context.region(arguments.get("city"))
   start = context.place(region, arguments.get("from"), "from")
   end = context.place(region, arguments.get("to"), "to")
   query = {"startcoord": "{0},{1}".format(*start.coords), "endcoord": "{0},{1}".format(*end.coords), "region_id": region["region_id"]}
   response = context.send(endpoints.TRAVEL_TIME, query=query)
   minutes = response.get("travel_time_minutes") if isinstance(response, dict) else None
   seconds = int(minutes * 60) if isinstance(minutes, (int, float)) else None
   return {"seconds": seconds, "minutes": minutes, "from": start.as_dict(), "to": end.as_dict()}


def get_shared_eta(context, arguments):
   raise NotFound(RETIRED_ETA, {"blocked": "not served on the web"})


def search_places(context, arguments):
   region = context.region(arguments.get("city"))
   query = arguments.get("query")

   if not query:
      raise UsageError("Pass --query.")

   near = None
   if arguments.get("near"):
      near = context.place(region, arguments["near"], "near").coords

   results = search(context, region, query, near)
   first_result = results[0] if results else None
   can_cache_first_result = context.cache_text_places and not near and first_result and first_result.coords

   if can_cache_first_result:
      context.place_cache(region).put([place_query_key(query)], first_result.as_dict())

   limit = arguments.get("limit")
   kept = results[:limit] if limit else results
   return {"query": query, "results": [place.as_dict() for place in kept]}


def resolve_place(context, arguments):
   region = context.region(arguments.get("city"))
   identifier = arguments.get("id")

   if not identifier:
      raise UsageError("Pass --id (a search result id such as google:ChIJ...).")

   resolved = resolve_search_result(context, region, Place(name="", id=identifier))

   if not resolved.coords:
      raise NotFound("Citymapper could not resolve '{0}'.".format(identifier), {"id": identifier})

   return {"place": resolved.as_dict()}


def reverse_geocode(context, arguments):
   latitude = arguments.get("lat")
   longitude = arguments.get("lng")

   if latitude is None or longitude is None:
      raise UsageError("Pass --lat and --lng.")

   response = context.send(endpoints.GEOCODE, query={"lat": latitude, "lng": longitude})
   results = require_list(response, "results", "geocode response")
   coords = coords_of([latitude, longitude])

   if not results:
      return {"address": None, "name": None, "components": [], "coords": coords}

   first = results[0]
   components = [component.get("long_name", "") for component in first.get("address_components") or []]
   name = " ".join(components[:2]).strip() or None
   return {"address": first.get("formatted_address"), "name": name, "components": components, "coords": coords}
