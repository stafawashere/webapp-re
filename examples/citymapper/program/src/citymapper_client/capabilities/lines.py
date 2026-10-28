import re

from .. import endpoints
from ..config import ROUTE_STATUS_MAX_AGE_SECONDS
from ..errors import NotFound, UsageError
from ..models import LineSummary, Status, coords_of, require_list, whole_number

PLACEHOLDER = re.compile(r"\{(\d+)\}")


def fill_placeholders(text, replacements):
   replacements = replacements or {}

   def replace(match):
      replacement = replacements.get(match.group(1)) or {}
      return str(replacement.get("text", match.group(0))).replace("<", "").replace(">", "")

   return PLACEHOLDER.sub(replace, text or "")


def route_status_groups(context, region):
   status_cache = context.cached_value("routestatus-{0}.json".format(region["region_id"]), ROUTE_STATUS_MAX_AGE_SECONDS)
   cached = status_cache.get()

   if isinstance(cached, dict):
      return cached

   response = context.send(endpoints.ROUTE_STATUS, query={"region_id": region["region_id"], "format": "rich"}, headers={"Citymapper-Region": region["region_id"]})
   holds_groupings = isinstance(response, dict) and isinstance(response.get("groupings"), list)

   if holds_groupings:
      status_cache.put(response)

   return response


def get_line_status(context, arguments):
   region = context.region(arguments.get("city"))
   response = route_status_groups(context, region)
   wanted_mode = (arguments.get("mode") or "").lower()
   groups = []

   for grouping in require_list(response, "groupings", "route status"):
      name = grouping.get("name", "")
      matches_mode = not wanted_mode or wanted_mode in name.lower() or wanted_mode in str(grouping.get("id", "")).lower()

      if not matches_mode:
         continue

      lines = []
      for route in grouping.get("routes") or []:
         summary = LineSummary.from_api(route).as_dict()
         summary["status"]["description"] = fill_placeholders(summary["status"]["description"], (route.get("status") or {}).get("replacements")) or None
         lines.append(summary)

      groups.append({"id": str(grouping.get("id", "")), "name": name, "lines": lines})

   return {"updated": response.get("last_updated_time"), "groups": groups}


def get_disruptions(context, arguments):
   region = context.region(arguments.get("city"))
   response = route_status_groups(context, region)
   minimum_level = arguments.get("min_level") if arguments.get("min_level") is not None else 1
   wanted_line = (arguments.get("line") or "").lower()
   disruptions = []

   for grouping in require_list(response, "groupings", "route status"):
      for route in grouping.get("routes") or []:
         line = LineSummary.from_api(route)
         names = {line.id.lower(), line.name.lower()} | {alias.lower() for alias in line.aliases}
         is_other_line = wanted_line and wanted_line not in names

         if is_other_line:
            continue

         status = route.get("status") or {}
         items = status.get("disruptions") or []
         has_status_only = not items and whole_number(status.get("level", 0), "level", "line status") >= minimum_level

         if has_status_only:
            items = [{"level": status.get("level", 0), "summary": status.get("summary", ""), "description": status.get("description", ""), "replacements": status.get("replacements"), "stops": []}]

         for item in items:
            level = whole_number(item.get("level", 0), "level", "disruption")

            if level < minimum_level:
               continue

            disruptions.append({
               "line": line.id,
               "line_name": line.long_name or line.name,
               "group": grouping.get("name", ""),
               "level": level,
               "summary": item.get("summary", ""),
               "description": fill_placeholders(item.get("description"), item.get("replacements")),
               "stops": [str(stop) for stop in item.get("stops") or []],
            })

   disruptions.sort(key=lambda item: (-item["level"], item["group"], item["line"]))
   return {"updated": response.get("last_updated_time"), "disruptions": disruptions}


def get_service_message(context, arguments):
   region = context.region(arguments.get("city"))
   response = context.send(endpoints.MESSAGE, query={"had_previous_versions": "0"}, headers={"Citymapper-Region": region["region_id"]})
   return {"messages": require_list(response, "messages", "service message")}


def find_line(context, arguments):
   region = context.region(arguments.get("city"))
   query = arguments.get("query")

   if not query:
      raise UsageError("Pass --query (a line name or number).")

   response = context.send(endpoints.FIND_TRANSPORT, query={"query": query, "region_id": region["region_id"]})
   lines = []

   for item in require_list(response, "results", "line search"):
      if item.get("result_type") != "route":
         continue

      lines.append({
         "id": str(item.get("id", "")),
         "name": item.get("display_name") or item.get("name") or str(item.get("id", "")),
         "long_name": item.get("long_name"),
         "brand": item.get("brand_id"),
         "mode": (item.get("affinities") or [None])[0],
         "aliases": [],
         "color": item.get("color"),
         "description": item.get("description"),
         "status": Status.from_api(item.get("status")).as_dict(),
      })

   return {"lines": lines}


def route_info(context, region, line_text):
   if not line_text:
      raise UsageError("Pass --line (an alias such as subway-6 or a route id).")

   response = context.send(endpoints.ROUTE_INFO, query={"route": line_text, "region_id": region["region_id"], "weekend": "1", "status_format": "rich", "extended": "1"})
   routes = require_list(response, "routes", "line info")

   if not routes:
      raise NotFound("No line '{0}' in {1}.".format(line_text, region["name"]), {"line": line_text})

   return routes[0], response.get("stops") or {}


def get_line(context, arguments):
   region = context.region(arguments.get("city"))
   route, stops = route_info(context, region, arguments.get("line"))
   with_paths = bool(arguments.get("with_paths"))

   def stop_record(stop_id):
      stop = stops.get(stop_id) or {}
      return {"id": str(stop_id), "name": stop.get("name", ""), "coords": coords_of(stop.get("coords")) or []}

   patterns = []
   for pattern in route.get("patterns") or []:
      stop_ids = []

      for point in pattern.get("stop_points") or []:
         stop_id = point.get("id") or point.get("stop_id") if isinstance(point, dict) else point
         if stop_id:
            stop_ids.append(stop_id)

      path = [coords_of(point) for point in pattern.get("path") or []] if with_paths else []
      patterns.append({"id": str(pattern.get("id", "")), "name": pattern.get("name", ""), "stops": [stop_record(stop_id) for stop_id in stop_ids], "path": [point for point in path if point]})

   summary = LineSummary.from_api(route).as_dict()
   summary["status"]["description"] = fill_placeholders(summary["status"]["description"], (route.get("status") or {}).get("replacements")) or None
   return {"line": summary, "patterns": patterns, "stops": [stop_record(stop_id) for stop_id in stops]}


def get_lines(context, arguments):
   region = context.region(arguments.get("city"))
   wanted = arguments.get("lines") or []

   if not wanted:
      raise UsageError("Pass --lines (comma separated route ids).")

   response = context.send(endpoints.ROUTE_INFO_MANY, query={"route_ids": ",".join(wanted), "region_id": region["region_id"], "weekend": "1", "status_format": "rich"})
   return {"lines": [LineSummary.from_api(route).as_dict() for route in require_list(response, "routes", "lines info")]}


def get_vehicles(context, arguments):
   region = context.region(arguments.get("city"))
   line_text = arguments.get("line")

   if not line_text:
      raise UsageError("Pass --line.")

   response = context.send(endpoints.VEHICLE_LOCATIONS, query={"route": line_text, "region_id": region["region_id"]})
   vehicles = require_list(response, "vehicle_locations", "vehicle locations")
   route = response.get("route") or {}
   return {"line": {"id": str(route.get("id", line_text)), "name": route.get("display_name") or route.get("name") or line_text}, "vehicles": vehicles}


def get_route_paths(context, arguments):
   region = context.region(arguments.get("city"))
   wanted = arguments.get("lines") or []

   if not wanted:
      raise UsageError("Pass --lines (comma separated route ids).")

   response = context.send(endpoints.ROUTE_PATHS, query={"route_ids": ",".join(wanted), "region_id": region["region_id"]})
   paths = []

   for route in require_list(response, "routes", "route paths"):
      patterns = [{"id": str(pattern.get("id", "")), "name": pattern.get("name", ""), "path": [coords_of(point) for point in pattern.get("path") or []]} for pattern in route.get("patterns") or []]
      paths.append({"id": str(route.get("id", "")), "name": route.get("name", ""), "patterns": patterns})

   return {"paths": paths}
