from .. import endpoints
from ..errors import ContractBroken, NotFound, UsageError
from ..models import Departure, NearbyElement, coords_of, require, require_list

FEEDS = {
   "departures": endpoints.BUS_DEPARTURES,
   "metrodepartures": endpoints.METRO_DEPARTURES,
   "raildepartures": endpoints.RAIL_DEPARTURES,
}
DEFAULT_FEED = "departures"


def nearby_mode(config, mode_text):
   modes = config.get("nearby_modes") or []
   wanted = (mode_text or "").lower()

   for mode in modes:
      names = {str(mode.get("mode_slug", "")).lower(), str(mode.get("mode_id", "")).lower(), str(mode.get("short_title", "")).lower()}
      if wanted in names:
         return mode

   for mode in modes:
      matches_affinity = wanted in [str(affinity).lower() for affinity in mode.get("affinities") or []]
      if matches_affinity:
         return mode

   available = sorted({str(mode.get("mode_slug")) for mode in modes if mode.get("mode_slug")})
   raise UsageError("No nearby mode '{0}' in this city. Modes: {1}.".format(mode_text, ", ".join(available)), {"modes": available})


def find_nearby(context, arguments):
   region = context.region(arguments.get("city"))
   near = context.place(region, arguments.get("near"), "near")
   mode = nearby_mode(context.region_config(region), arguments.get("mode"))
   limit = arguments.get("limit") or 50
   query = {"location": "{0},{1}".format(*near.coords), "region_id": region["region_id"], "mode_id": mode.get("mode_id"), "limit": str(limit), "extended": "1"}
   brand_ids = mode.get("request_brand_ids") or []

   if brand_ids:
      query["brand_ids"] = ",".join(brand_ids)
   else:
      query["kinds"] = ",".join(mode.get("kind_ids") or [])

   response = context.send(endpoints.NEARBY, query=query)
   elements = [NearbyElement.from_api(element).as_dict() for element in require_list(response, "elements", "nearby response")]
   return {"mode_id": mode.get("mode_id"), "near": near.as_dict(), "elements": elements[:limit]}


def stop_details(context, region, stop_text):
   if not stop_text:
      raise UsageError("Pass --stop (an alias such as times-sq-42-st or an id).")

   response = context.send(endpoints.STOP_INFO, query={"ids": stop_text, "region_id": region["region_id"]})
   stops = require_list(response, "stops", "stop info")

   if not stops:
      raise NotFound("No stop '{0}' in {1}.".format(stop_text, region["name"]), {"stop": stop_text})

   return stops[0], response.get("routes") or []


def stop_cache_key(text):
   return str(text).strip().lower()


def remember_stop(context, region, stop_text, stop, routes):
   stop_id = stop.get("id")

   if stop_id is None:
      return

   sharing = stop.get("sharing_urls") or []
   feed = sharing[0].get("departure_api") if sharing else None
   summary = {
      "stop": {"id": str(stop_id), "name": stop.get("name", ""), "sharing_urls": [{"departure_api": feed}] if feed else []},
      "routes": [{"id": str(route.get("id")), "name": route.get("name")} for route in routes],
   }
   context.stop_cache(region).put([stop_cache_key(stop_text), stop_cache_key(stop_id)], summary)


def cached_stop(cached):
   holds_stop = isinstance(cached, dict) and isinstance(cached.get("stop"), dict)
   has_id = holds_stop and cached["stop"].get("id") is not None
   has_routes = has_id and isinstance(cached.get("routes"), list)

   return (cached["stop"], cached["routes"]) if has_routes else None


def forget_stop(context, region, stop):
   stale_id = str(stop.get("id"))

   def is_stale(value):
      restored = cached_stop(value)
      return restored is None or restored[0]["id"] == stale_id

   context.stop_cache(region).discard(is_stale)


def known_stop_details(context, region, stop_text):
   if not stop_text:
      raise UsageError("Pass --stop (an alias such as times-sq-42-st or an id).")

   restored = cached_stop(context.stop_cache(region).get(stop_cache_key(stop_text)))

   if restored is not None:
      return restored

   stop, routes = stop_details(context, region, stop_text)
   remember_stop(context, region, stop_text, stop, routes)
   return stop, routes


def get_stop(context, arguments):
   region = context.region(arguments.get("city"))
   stop, routes = stop_details(context, region, arguments.get("stop"))
   remember_stop(context, region, arguments.get("stop"), stop, routes)
   sharing = stop.get("sharing_urls") or []
   exits = [{"id": str(item.get("id", "")), "name": item.get("name", ""), "coords": coords_of(item.get("coords")) or []} for item in stop.get("exits") or []]
   return {
      "id": str(require(stop, "id", "stop")),
      "alias": stop.get("alias"),
      "name": require(stop, "name", "stop"),
      "coords": coords_of(stop.get("coords")) or [],
      "routes": [{"id": str(route.get("id", "")), "name": route.get("name", ""), "brand_id": route.get("brand_id"), "color": route.get("color")} for route in routes],
      "exits": exits,
      "departure_api": sharing[0].get("departure_api") if sharing else None,
      "url": stop.get("url"),
   }


def bus_departures(response, route_names):
   departures = []

   for stop in require_list(response, "stops", "departures response"):
      for service in stop.get("services") or []:
         route_id = str(require(service, "route_id", "bus service"))
         live_seconds = service.get("live_departures_seconds") or []

         for seconds in live_seconds:
            departures.append(Departure(route_id=route_id, route_name=route_names.get(route_id), destination=service.get("headsign"), seconds_away=int(seconds), is_live=True, platform_or_direction=stop.get("bearing")))

         scheduled_times = [] if live_seconds else service.get("next_departures") or []

         for scheduled in scheduled_times:
            departures.append(Departure(route_id=route_id, route_name=route_names.get(route_id), destination=service.get("headsign"), time=str(scheduled), is_live=False, platform_or_direction=stop.get("bearing")))

         has_no_times = not live_seconds and not scheduled_times

         if has_no_times:
            departures.append(Departure(route_id=route_id, route_name=route_names.get(route_id), destination=service.get("headsign"), is_live=False, advisory="no live times", platform_or_direction=stop.get("bearing")))

   return departures, None


def metro_departures(response, route_names):
   departures = []
   updated = response.get("last_updated_time")

   for station in require_list(response, "stations", "metro departures response"):
      for section in station.get("sections") or []:
         for grouping in section.get("departure_groupings") or []:
            direction = grouping.get("direction_name") or section.get("name")

            for item in grouping.get("departures") or []:
               route_id = str(item.get("route_id", ""))
               is_advisory = bool(item.get("is_advisory_message"))
               seconds = item.get("time_seconds")
               departures.append(Departure(
                  route_id=route_id,
                  route_name=route_names.get(route_id),
                  destination=None if is_advisory else item.get("destination_name"),
                  platform_or_direction=direction,
                  seconds_away=int(seconds) if isinstance(seconds, (int, float)) else None,
                  scheduled_time=item.get("scheduled_time"),
                  is_live=isinstance(seconds, (int, float)),
                  advisory=item.get("destination_name") if is_advisory else None,
               ))

   return departures, updated


def rail_departures(response, route_names):
   departures = []
   updated = response.get("last_updated_time")

   for station in require_list(response, "stations", "rail departures response"):
      for item in station.get("departures") or []:
         route_id = str(item.get("route_id", ""))
         seconds = item.get("time_seconds")
         platform = item.get("platform_number")
         departures.append(Departure(
            route_id=route_id,
            route_name=route_names.get(route_id),
            destination=item.get("destination"),
            platform_or_direction=str(platform) if platform is not None else None,
            seconds_away=int(seconds) if isinstance(seconds, (int, float)) else None,
            time=item.get("expected_departure_time"),
            scheduled_time=item.get("scheduled_time"),
            is_live=bool(item.get("is_live")),
         ))

   return departures, updated


def departure_order(item):
   has_seconds = item.seconds_away is not None
   return (not item.is_live, not has_seconds, item.seconds_away if has_seconds else 0, item.time or "")


PARSERS = {"departures": bus_departures, "metrodepartures": metro_departures, "raildepartures": rail_departures}


def get_departures(context, arguments):
   region = context.region(arguments.get("city"))
   stop, routes = known_stop_details(context, region, arguments.get("stop"))
   sharing = stop.get("sharing_urls") or []
   feed = (sharing[0].get("departure_api") if sharing else None) or DEFAULT_FEED
   route_names = {str(route.get("id")): route.get("name") for route in routes}

   try:
      if feed not in FEEDS:
         raise NotFound("Stop '{0}' uses departures feed '{1}', which the program does not know.".format(stop.get("name"), feed), {"feed": feed})

      response = context.send(FEEDS[feed], query={"headways": "1", "ids": stop["id"], "region_id": region["region_id"]})
      departures, feed_updated = PARSERS[feed](response, route_names)
   except (NotFound, ContractBroken):
      forget_stop(context, region, stop)
      raise

   updated = feed_updated or context.transport.last_sent_at
   wanted_route = arguments.get("route")

   if wanted_route:
      wanted = wanted_route.lower()
      departures = [item for item in departures if item.route_id.lower() == wanted or (item.route_name or "").lower() == wanted]

   live_first = sorted(departures, key=departure_order)
   limit = arguments.get("limit")
   kept = live_first[:limit] if limit else live_first
   return {"stop": {"id": str(stop["id"]), "name": stop.get("name", "")}, "feed": feed, "updated": updated, "departures": [item.as_dict() for item in kept]}


def get_stop_schedule(context, arguments):
   region = context.region(arguments.get("city"))
   stop, _ = known_stop_details(context, region, arguments.get("stop"))
   query = {"id": stop["id"], "region_id": region["region_id"], "time": context.to_utc_iso(region, arguments.get("time"))}

   try:
      response = context.send(endpoints.SCHEDULES, query=query)
   except (NotFound, ContractBroken):
      forget_stop(context, region, stop)
      raise

   return {"stop": str(stop["id"]), "raw": response}
