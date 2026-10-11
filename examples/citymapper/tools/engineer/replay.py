#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""Paced replays of citymapper endpoints for knowledge base verification.

Each step is one request. Bodies go to var/captures/replay-<stamp>.jsonl, one result line per step to
var/logs/replay-<stamp>.json. A 429 or a challenge page stops the run.

   uv run --script tools/engineer/replay.py [--only id,id] [--gap 3.5]
"""

import argparse
import base64
import json
import random
import time
import zlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "https://citymapper.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"

NYC_FROM = "40.752852,-73.977142"
NYC_TO = "40.706086,-73.996864"
LONDON_FROM = "51.503324,-0.119543"
LONDON_TO = "51.531683,-0.124518"
PARIS_FROM = "48.858370,2.347000"
PARIS_TO = "48.880930,2.355330"


def journey_query(start, end, region_id, **extra):
   query = {"start": start, "end": end, "region_id": region_id, "include_stepfree": "1", "include_via_microtransit": "1", "status_format": "html"}
   query.update(extra)
   return query


def hashify(signature):
   return base64.b64encode(zlib.compress(signature.encode("utf-8"))).decode("ascii")


def has_keys(*keys):
   def check(body):
      missing = [key for key in keys if key not in body]
      return (not missing, "missing " + ",".join(missing) if missing else "keys present")

   return check


def non_empty_list(key, *item_keys):
   def check(body):
      items = body.get(key) if isinstance(body, dict) else None
      if not isinstance(items, list) or not items:
         return (False, "{0} empty or absent".format(key))

      missing = [item_key for item_key in item_keys if item_key not in items[0]]
      if missing:
         return (False, "first {0} item lacks {1}".format(key, ",".join(missing)))

      return (True, "{0} {1} items".format(len(items), key))

   return check


def html_with(marker):
   def check(text):
      present = marker in text
      return (present, "marker {0}".format("found" if present else "absent"))

   return check


def first_signature(results, key):
   body = results[key]["json"]
   return body["journeys"][0]["signature"]


def first_signatures(results, key, count):
   body = results[key]["json"]
   return [journey["signature"] for journey in body["journeys"][:count]]


def element_id(results, key, kind_prefix=""):
   body = results[key]["json"]
   for element in body["elements"]:
      if element["id"].startswith(kind_prefix):
         return element["id"]

   return body["elements"][0]["id"]


def search_place_id(results, key):
   for item in results[key]["json"]["results"]:
      is_item = item.get("result_type") != "heading" and item.get("id")
      if is_item:
         return item["id"]

   return None


def stop_id(results, key):
   return results[key]["json"]["stops"][0]["id"]


STEPS = [
   {"key": "cities-html-1", "finding": "cities-html", "method": "GET", "path": "/cities", "html": True, "check": html_with("window.citymapper.regions")},
   {"key": "city-html-1", "finding": "city-html", "method": "GET", "path": "/boston", "html": True, "check": html_with("window.citymapper.region =")},
   {"key": "region-info-1", "finding": "resource-region-info", "method": "GET", "path": "/resource/region-info/us-nyc", "check": has_keys("region_id", "nearby_modes", "bounding_box", "timezone")},
   {"key": "region-info-2", "finding": "resource-region-info", "method": "GET", "path": "/resource/region-info/uk-london", "check": has_keys("region_id", "nearby_modes", "bounding_box", "timezone")},
   {"key": "brand-directory-1", "finding": "resource-brand-directory", "method": "GET", "path": "/resource/brand-directory", "check": lambda body: (bool(body), "type " + type(body).__name__)},
   {"key": "search-1", "finding": "searchpost", "method": "POST", "path": "/api/4/searchpost", "form_json": {"query": "Times Square", "region_id": "us-nyc", "is_refinement": True, "refinement_data": {"is_chain": True}, "powersearch": False}, "headers": {"Citymapper-Client": "Web Search", "Citymapper-Region": "us-nyc"}, "check": non_empty_list("results", "name")},
   {"key": "search-2", "finding": "searchpost", "method": "POST", "path": "/api/4/searchpost", "form_json": {"query": "Kings Cross", "region_id": "uk-london", "is_refinement": True, "refinement_data": {"is_chain": True}, "powersearch": False}, "headers": {"Citymapper-Client": "Web Search", "Citymapper-Region": "uk-london"}, "check": non_empty_list("results", "name")},
   {"key": "placeresolve-1", "finding": "placeresolve", "method": "GET", "path": "/api/1/placeresolve", "query": lambda results: {"id": search_place_id(results, "search-1"), "region_id": "us-nyc"}, "check": lambda body: (bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "type " + type(body).__name__)},
   {"key": "geocode-1", "finding": "geocode", "method": "GET", "path": "/geocode", "query": {"lat": "40.748441", "lng": "-73.985664"}, "check": non_empty_list("results")},
   {"key": "geocode-2", "finding": "geocode", "method": "GET", "path": "/geocode", "query": {"lat": "51.507351", "lng": "-0.127758"}, "check": non_empty_list("results")},
   {"key": "journeys-1", "finding": "journeys", "method": "GET", "path": "/api/7/journeys", "query": journey_query(NYC_FROM, NYC_TO, "us-nyc", sname="Grand Central", ename="Brooklyn Bridge"), "check": non_empty_list("journeys", "legs", "duration_seconds", "signature")},
   {"key": "journeys-2", "finding": "journeys", "method": "GET", "path": "/api/7/journeys", "query": journey_query(LONDON_FROM, LONDON_TO, "uk-london", arrival_time="2026-10-11T09:00:00.000Z"), "check": non_empty_list("journeys", "legs", "duration_seconds", "signature")},
   {"key": "walk7-1", "finding": "walk7", "method": "GET", "path": "/api/7/walk", "query": journey_query(NYC_FROM, NYC_TO, "us-nyc", limit="2"), "check": non_empty_list("journeys", "legs", "duration_seconds")},
   {"key": "walk7-2", "finding": "walk7", "method": "GET", "path": "/api/7/walk", "query": journey_query(PARIS_FROM, PARIS_TO, "fr-paris", limit="2"), "check": non_empty_list("journeys", "legs", "duration_seconds")},
   {"key": "walk1-1", "finding": "walk1", "method": "GET", "path": "/api/1/walk", "query": journey_query(NYC_FROM, NYC_TO, "us-nyc"), "check": non_empty_list("journeys", "legs")},
   {"key": "cycle-1", "finding": "cycle", "method": "GET", "path": "/api/6/cycle", "query": journey_query(NYC_FROM, NYC_TO, "us-nyc"), "check": non_empty_list("journeys", "legs", "duration_seconds")},
   {"key": "cycle-2", "finding": "cycle", "method": "GET", "path": "/api/6/cycle", "query": journey_query(LONDON_FROM, LONDON_TO, "uk-london"), "check": non_empty_list("journeys", "legs", "duration_seconds")},
   {"key": "taxi-1", "finding": "taxi", "method": "GET", "path": "/api/2/taxi", "query": journey_query(NYC_FROM, NYC_TO, "us-nyc"), "check": has_keys("routes")},
   {"key": "taxi-2", "finding": "taxi", "method": "GET", "path": "/api/2/taxi", "query": journey_query(LONDON_FROM, LONDON_TO, "uk-london"), "check": has_keys("routes")},
   {"key": "vehiclehire-1", "finding": "vehiclehire", "method": "GET", "path": "/api/7/vehiclehire", "query": journey_query(LONDON_FROM, LONDON_TO, "uk-london"), "check": has_keys("journeys")},
   {"key": "vehiclehire-2", "finding": "vehiclehire", "method": "GET", "path": "/api/7/vehiclehire", "query": journey_query(PARIS_FROM, PARIS_TO, "fr-paris"), "check": has_keys("journeys")},
   {"key": "journeytimes-1", "finding": "journeytimes", "method": "POST", "path": "/api/1/journeytimes", "query": {"region_id": "us-nyc"}, "json": lambda results: {"signatures": first_signatures(results, "journeys-1", 3)}, "check": non_empty_list("journey_times", "time")},
   {"key": "journeytimes-2", "finding": "journeytimes", "method": "POST", "path": "/api/1/journeytimes", "query": {"region_id": "uk-london"}, "json": lambda results: {"signatures": first_signatures(results, "journeys-2", 2)}, "check": non_empty_list("journey_times", "time")},
   {"key": "refresh-1", "finding": "refreshjourneys", "method": "POST", "path": "/api/1/refreshjourneys", "query": {"region_id": "us-nyc"}, "json": lambda results: {"signatures": [first_signature(results, "journeys-1")], "time_mode": "SIGNATURE", "region_id": "us-nyc", "status_format": "html"}, "check": non_empty_list("refreshed_journeys")},
   {"key": "refresh-2", "finding": "refreshjourneys", "method": "POST", "path": "/api/1/refreshjourneys", "query": {"region_id": "uk-london"}, "json": lambda results: {"signatures": [first_signature(results, "journeys-2")], "time_mode": "SIGNATURE_EXACT", "region_id": "uk-london", "status_format": "html"}, "check": non_empty_list("refreshed_journeys")},
   {"key": "trip-meta-1", "finding": "trip-meta", "method": "GET", "path": "/trip/signature", "query": lambda results: {"signature": hashify(first_signature(results, "journeys-1")), "meta_only": "true"}, "check": lambda body: (bool(body), "type " + type(body).__name__)},
   {"key": "traveltime-1", "finding": "traveltime", "method": "GET", "path": "/api/1/traveltime", "query": {"startcoord": NYC_FROM, "endcoord": NYC_TO, "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "eta-1", "finding": "eta", "method": "POST", "path": "/api/1/eta", "query": {"region_id": "us-nyc"}, "json": lambda results: {"signature": first_signature(results, "journeys-1")}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "nearby3-1", "finding": "nearby3", "method": "GET", "path": "/api/3/nearby", "query": {"brand_ids": "NewYorkSubway,RooseveltTramNYC", "location": "40.75773,-73.985708", "region_id": "us-nyc", "mode_id": "us-nyc-subway", "limit": "50", "extended": "1"}, "check": non_empty_list("elements", "id", "name", "coords", "kind")},
   {"key": "nearby3-2", "finding": "nearby3", "method": "GET", "path": "/api/3/nearby", "query": {"kinds": "cycledock", "brand_ids": "CitiBike", "location": "40.75773,-73.985708", "region_id": "us-nyc", "mode_id": "us-nyc-citibike", "limit": "20", "extended": "1"}, "check": non_empty_list("elements", "id", "name", "coords", "kind")},
   {"key": "nearby2-1", "finding": "nearby2", "method": "GET", "path": "/api/2/nearby", "query": {"brand_ids": "NewYorkSubway", "location": "40.755986,-73.986328", "limit": "50", "region_id": "us-nyc"}, "check": non_empty_list("elements", "id", "name")},
   {"key": "nearby2-2", "finding": "nearby2", "method": "GET", "path": "/api/2/nearby", "query": {"kinds": "transitstop", "location": "51.503324,-0.119543", "limit": "20", "region_id": "uk-london"}, "check": non_empty_list("elements", "id", "name")},
   {"key": "stopinfo-1", "finding": "stopinfo", "method": "GET", "path": "/api/3/stopinfo", "query": {"ids": "times-sq-42-st", "region_id": "us-nyc"}, "check": non_empty_list("stops", "id", "name", "coords")},
   {"key": "stopinfo-2", "finding": "stopinfo", "method": "GET", "path": "/api/3/stopinfo", "query": {"ids": "chatelet", "region_id": "fr-paris"}, "check": non_empty_list("stops", "id", "name", "coords")},
   {"key": "metro-1", "finding": "departures-metro", "method": "GET", "path": "/api/2/metrodepartures", "query": {"headways": "1", "ids": "SubwayTimesSq42St", "region_id": "us-nyc"}, "check": non_empty_list("stations", "station", "sections")},
   {"key": "metro-2", "finding": "departures-metro", "method": "GET", "path": "/api/2/metrodepartures", "query": lambda results: {"headways": "1", "ids": stop_id(results, "stopinfo-2"), "region_id": "fr-paris"}, "check": non_empty_list("stations", "station", "sections")},
   {"key": "bus-1", "finding": "departures-bus", "method": "GET", "path": "/api/1/departures", "query": {"headways": "1", "ids": "405297_1", "region_id": "us-nyc"}, "check": non_empty_list("stops", "id", "services")},
   {"key": "bus-2", "finding": "departures-bus", "method": "GET", "path": "/api/1/departures", "query": lambda results: {"headways": "1", "ids": element_id(results, "nearby2-2"), "region_id": "uk-london"}, "check": non_empty_list("stops", "id", "services")},
   {"key": "rail-1", "finding": "departures-rail", "method": "GET", "path": "/api/1/raildepartures", "query": {"headways": "1", "ids": "RailStationGrandCentral", "region_id": "us-nyc"}, "check": non_empty_list("stations", "station", "departures")},
   {"key": "rail-2", "finding": "departures-rail", "method": "GET", "path": "/api/1/raildepartures", "query": {"headways": "1", "ids": "RailStationNewYorkPenn", "region_id": "us-nyc"}, "check": non_empty_list("stations", "station")},
   {"key": "schedules-1", "finding": "schedules", "method": "GET", "path": "/api/1/schedules", "query": {"id": "405297_1", "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "routestatus-1", "finding": "routestatus", "method": "GET", "path": "/api/1/routestatus", "query": {"region_id": "us-nyc", "format": "rich"}, "headers": {"Citymapper-Region": "us-nyc"}, "check": non_empty_list("groupings", "id", "name")},
   {"key": "routestatus-2", "finding": "routestatus", "method": "GET", "path": "/api/1/routestatus", "query": {"region_id": "uk-london", "format": "rich"}, "headers": {"Citymapper-Region": "uk-london"}, "check": non_empty_list("groupings", "id", "name")},
   {"key": "routeinfo2-1", "finding": "routeinfo2", "method": "GET", "path": "/api/2/routeinfo", "query": {"route_ids": "1,2,3,A,L", "region_id": "us-nyc", "weekend": "1", "status_format": "rich"}, "check": non_empty_list("routes", "name", "status")},
   {"key": "routeinfo2-2", "finding": "routeinfo2", "method": "GET", "path": "/api/2/routeinfo", "query": {"route_ids": "Bakerloo,Victoria", "region_id": "uk-london", "weekend": "1", "status_format": "rich"}, "check": non_empty_list("routes", "name", "status")},
   {"key": "message-1", "finding": "message", "method": "GET", "path": "/api/2/message", "query": {"had_previous_versions": "0"}, "headers": {"Citymapper-Region": "us-nyc"}, "check": has_keys("messages")},
   {"key": "message-2", "finding": "message", "method": "GET", "path": "/api/2/message", "query": {"had_previous_versions": "0"}, "headers": {"Citymapper-Region": "uk-london"}, "check": has_keys("messages")},
   {"key": "findtransport-1", "finding": "findtransport", "method": "GET", "path": "/api/2/findtransport", "query": {"query": "M15", "region_id": "us-nyc"}, "check": lambda body: (bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "type " + type(body).__name__)},
   {"key": "findtransport-2", "finding": "findtransport", "method": "GET", "path": "/api/2/findtransport", "query": {"query": "Victoria", "region_id": "uk-london"}, "check": lambda body: (bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "type " + type(body).__name__)},
   {"key": "routeinfo1-1", "finding": "routeinfo1", "method": "GET", "path": "/api/1/routeinfo", "query": {"route": "subway-6", "region_id": "us-nyc", "weekend": "1", "status_format": "rich", "extended": "1"}, "check": non_empty_list("routes", "name", "patterns")},
   {"key": "routeinfo1-2", "finding": "routeinfo1", "method": "GET", "path": "/api/1/routeinfo", "query": {"route": "bakerloo", "region_id": "uk-london", "weekend": "1", "status_format": "rich", "extended": "1"}, "check": non_empty_list("routes", "name", "patterns")},
   {"key": "vehicles-1", "finding": "vehiclelocations", "method": "GET", "path": "/api/1/vehiclelocations", "query": {"route": "6", "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "routepaths-1", "finding": "routepaths", "method": "GET", "path": "/api/1/routepaths", "query": {"route_ids": "6", "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "everything-1", "finding": "everythingmap", "method": "GET", "path": "/api/1/everythingmap", "query": {"location": "40.75773,-73.985708", "size": "500", "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "weather-1", "finding": "weather", "method": "GET", "path": "/api/1/weather", "query": {"location": "40.75773,-73.985708", "units": "f", "term": "now"}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "transitscore-1", "finding": "transitscore", "method": "GET", "path": "/api/1/transitscore", "query": {"startcoord": "40.75773,-73.985708"}, "check": lambda body: (isinstance(body, dict) and bool(body), "keys " + ",".join(list(body)[:8]) if isinstance(body, dict) else "not an object")},
   {"key": "blog-1", "finding": "blog", "method": "GET", "path": "/api/1/blog", "check": lambda body: (bool(body), "type " + type(body).__name__)},
   {"key": "news-1", "finding": "news-html", "method": "GET", "path": "/news", "html": True, "check": html_with("/news/")},
   {"key": "resources-1", "finding": "resources", "method": "GET", "path": "/api/1/resources", "query": {"id": "citymapper-terms-of-service"}, "html": True, "check": lambda text: (len(text) > 500, "length {0}".format(len(text)))},
   {"key": "user-data-1", "finding": "identity-user-data", "method": "GET", "path": "/api/1/identity/user_data", "expect_status": 403, "check": lambda body: (True, "signed-out 403")},
]


def google_id(results, key):
   for item in results[key]["json"]["results"]:
      if str(item.get("id", "")).startswith("google:"):
         return item["id"]

   return None


def route_result_check(body):
   items = [item for item in body.get("results", []) if item.get("result_type") == "route"] if isinstance(body, dict) else []
   return (bool(items), "{0} route results".format(len(items)))


SECOND_ROUND = [
   {"key": "cities-html-2", "finding": "cities-html", "method": "GET", "path": "/cities", "html": True, "check": html_with("window.citymapper.citiesInRegions")},
   {"key": "city-html-2", "finding": "city-html", "method": "GET", "path": "/dublin", "html": True, "check": html_with("window.citymapper.region =")},
   {"key": "brand-directory-2", "finding": "resource-brand-directory", "method": "GET", "path": "/resource/brand-directory", "check": non_empty_list("brands", "brand_id")},
   {"key": "search-3", "finding": "searchpost", "method": "POST", "path": "/api/4/searchpost", "form_json": {"query": "British Museum", "region_id": "uk-london", "is_refinement": True, "refinement_data": {"is_chain": True}, "powersearch": False}, "headers": {"Citymapper-Client": "Web Search", "Citymapper-Region": "uk-london"}, "check": non_empty_list("results", "name")},
   {"key": "placeresolve-2", "finding": "placeresolve", "method": "GET", "path": "/api/1/placeresolve", "query": {"id": "google:ChIJmQJIxlVYwokRLgeuocVOGVU", "region_id": "us-nyc"}, "check": lambda body: (bool((body or {}).get("place_result", {}) and body["place_result"].get("coords")), "place_result coords")},
   {"key": "placeresolve-3", "finding": "placeresolve", "method": "GET", "path": "/api/1/placeresolve", "query": lambda results: {"id": google_id(results, "search-3"), "region_id": "uk-london"}, "check": lambda body: (bool((body or {}).get("place_result", {}) and body["place_result"].get("coords")), "place_result coords")},
   {"key": "walk1-2", "finding": "walk1", "method": "GET", "path": "/api/1/walk", "query": journey_query(NYC_FROM, NYC_TO, "us-nyc"), "check": non_empty_list("routes", "legs", "duration_seconds")},
   {"key": "walk1-3", "finding": "walk1", "method": "GET", "path": "/api/1/walk", "query": journey_query(LONDON_FROM, LONDON_TO, "uk-london"), "check": non_empty_list("routes", "legs", "duration_seconds")},
   {"key": "journeys-3", "finding": "journeys", "method": "GET", "path": "/api/7/journeys", "query": journey_query(PARIS_FROM, PARIS_TO, "fr-paris", departure_time="2026-10-11T08:00:00.000Z"), "check": non_empty_list("journeys", "legs", "duration_seconds", "signature")},
   {"key": "trip-meta-2", "finding": "trip-meta", "method": "GET", "path": "/trip/signature", "html": True, "query": lambda results: {"signature": hashify(first_signature(results, "journeys-3")), "meta_only": "true"}, "check": html_with("hreflang")},
   {"key": "trip-meta-3", "finding": "trip-meta", "method": "GET", "path": "/trip/signature", "html": True, "query": lambda results: {"signature": hashify(results["journeys-3"]["json"]["journeys"][1]["signature"]), "meta_only": "true"}, "check": html_with("hreflang")},
   {"key": "eta-2", "finding": "eta", "method": "POST", "path": "/api/1/eta", "query": {"region_id": "fr-paris"}, "json": lambda results: {"signature": first_signature(results, "journeys-3")}, "check": lambda body: (isinstance(body, dict) and bool(body), "object")},
   {"key": "traveltime-2", "finding": "traveltime", "method": "GET", "path": "/api/1/traveltime", "query": {"startcoord": LONDON_FROM, "endcoord": LONDON_TO, "region_id": "uk-london"}, "check": has_keys("travel_time_minutes")},
   {"key": "nearby2-3", "finding": "nearby2", "method": "GET", "path": "/api/2/nearby", "query": {"brand_ids": "LondonBus", "location": LONDON_FROM, "limit": "20", "region_id": "uk-london"}, "check": non_empty_list("elements", "id", "name")},
   {"key": "bus-3", "finding": "departures-bus", "method": "GET", "path": "/api/1/departures", "query": lambda results: {"headways": "1", "ids": element_id(results, "nearby2-3"), "region_id": "uk-london"}, "check": non_empty_list("stops", "id", "services")},
   {"key": "rail-3", "finding": "departures-rail", "method": "GET", "path": "/api/1/raildepartures", "query": {"headways": "1", "ids": "RailStationPennStation", "region_id": "us-nyc"}, "check": non_empty_list("stations", "station", "departures")},
   {"key": "schedules-2", "finding": "schedules", "method": "GET", "path": "/api/1/schedules", "query": {"id": "SubwayTimesSq42St", "region_id": "us-nyc"}, "check": has_keys("id", "services")},
   {"key": "vehicles-2", "finding": "vehiclelocations", "method": "GET", "path": "/api/1/vehiclelocations", "query": {"route": "Bakerloo", "region_id": "uk-london"}, "check": has_keys("route", "vehicle_locations")},
   {"key": "routepaths-2", "finding": "routepaths", "method": "GET", "path": "/api/1/routepaths", "query": {"route_ids": "Bakerloo", "region_id": "uk-london"}, "check": non_empty_list("routes", "id")},
   {"key": "everything-2", "finding": "everythingmap", "method": "GET", "path": "/api/1/everythingmap", "query": {"location": "40.75773,-73.985708", "size": "small", "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict) and bool(body), "object")},
   {"key": "everything-3", "finding": "everythingmap", "method": "GET", "path": "/api/1/everythingmap", "query": {"location": "40.75773,-73.985708", "size": "large", "region_id": "us-nyc"}, "check": lambda body: (isinstance(body, dict) and bool(body), "object")},
   {"key": "weather-2", "finding": "weather", "method": "GET", "path": "/api/1/weather", "query": {"location": LONDON_FROM, "units": "c", "term": "now"}, "check": lambda body: (isinstance(body, dict) and bool(body), "object")},
   {"key": "transitscore-2", "finding": "transitscore", "method": "GET", "path": "/api/1/transitscore", "query": {"startcoord": LONDON_FROM}, "check": lambda body: (isinstance(body, dict) and bool(body), "object")},
   {"key": "blog-2", "finding": "blog", "method": "GET", "path": "/api/1/blog", "query": {"id": "2941"}, "check": lambda body: (bool(body), "object")},
   {"key": "news-2", "finding": "news-html", "method": "GET", "path": "/news", "html": True, "check": html_with("<title")},
   {"key": "news-3", "finding": "news-html", "method": "GET", "path": "/news", "html": True, "check": html_with("<title")},
   {"key": "resources-2", "finding": "resources", "method": "GET", "path": "/api/1/resources", "query": {"id": "citymapper-privacy-policy"}, "html": True, "check": lambda text: (len(text) > 500, "length {0}".format(len(text)))},
   {"key": "findtransport-3", "finding": "findtransport", "method": "GET", "path": "/api/2/findtransport", "query": {"query": "73", "region_id": "uk-london"}, "check": route_result_check},
   {"key": "user-data-2", "finding": "identity-user-data", "method": "GET", "path": "/api/1/identity/user_data", "expect_status": 403, "check": lambda body: (True, "signed-out 403")},
]


def resolve(value, results):
   return value(results) if callable(value) else value


def classify(response):
   content_type = response.headers.get("content-type", "")
   text = response.text
   looks_like_challenge = "cf-chl" in text or "challenge-platform" in text or "Just a moment" in text[:2000]

   if response.status_code == 429:
      return "RateLimited"

   if looks_like_challenge:
      return "ChallengeRequired"

   if response.status_code == 404:
      return "NotFound"

   if response.status_code >= 400:
      return "ApiError"

   if "json" not in content_type:
      return "html"

   return "json"


def main():
   parser = argparse.ArgumentParser()
   parser.add_argument("--only", default="")
   parser.add_argument("--gap", type=float, default=3.5)
   parser.add_argument("--round", type=int, default=1)
   args = parser.parse_args()

   wanted = {item for item in args.only.split(",") if item}
   stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
   capture_path = ROOT / "var/captures" / "replay-{0}.jsonl".format(stamp)
   log_path = ROOT / "var/logs" / "replay-{0}.json".format(stamp)
   results = {}
   last_sent = 0.0
   counts = {"sent": 0, "pass": 0, "fail": 0, "skipped": 0}

   client = httpx.Client(headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}, timeout=40.0, follow_redirects=True)

   with capture_path.open("a") as captures, log_path.open("a") as log:
      steps = SECOND_ROUND if args.round == 2 else STEPS

      for step in steps:
         selected = not wanted or step["key"] in wanted or step["finding"] in wanted
         if not selected:
            continue

         try:
            query = resolve(step.get("query"), results)
            json_body = resolve(step.get("json"), results)
            form_json = step.get("form_json")
         except (KeyError, IndexError, TypeError) as error:
            counts["skipped"] += 1
            line = {"key": step["key"], "finding": step["finding"], "skipped": "input unavailable: {0}".format(type(error).__name__)}
            log.write(json.dumps(line) + "\n")
            print(json.dumps(line), flush=True)
            continue

         wait = args.gap * random.uniform(1.2, 1.4) - (time.monotonic() - last_sent)
         if wait > 0:
            time.sleep(wait)

         url = ORIGIN + step["path"]
         if query:
            url += "?" + urlencode(query)

         headers = {"Referer": ORIGIN + "/", "Content-Type": "application/json; charset=utf-8"}
         headers.update(step.get("headers", {}))
         content = None

         if form_json is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            headers["Origin"] = ORIGIN
            content = json.dumps(form_json)
         elif json_body is not None:
            headers["Origin"] = ORIGIN
            content = json.dumps(json_body)

         started = time.monotonic()
         try:
            response = client.request(step["method"], url, headers=headers, content=content)
         except httpx.HTTPError as error:
            last_sent = time.monotonic()
            counts["sent"] += 1
            counts["fail"] += 1
            line = {"key": step["key"], "finding": step["finding"], "class": "TransportError", "detail": type(error).__name__}
            log.write(json.dumps(line) + "\n")
            print(json.dumps(line), flush=True)
            continue

         last_sent = time.monotonic()
         counts["sent"] += 1
         kind = classify(response)
         record = {"key": step["key"], "finding": step["finding"], "method": step["method"], "url": url, "request_body": content, "status": response.status_code, "content_type": response.headers.get("content-type"), "x_version": response.headers.get("x-version"), "body": response.text[:3000000]}
         captures.write(json.dumps(record) + "\n")

         expected_status = step.get("expect_status", 200)
         passed = False
         detail = kind

         if response.status_code == expected_status and kind in ("json", "html", "ApiError"):
            if step.get("html") or kind == "html":
               passed, detail = step["check"](response.text) if step.get("html") else (False, "html where json expected")
            elif kind == "json":
               body = response.json()
               results[step["key"]] = {"json": body}
               passed, detail = step["check"](body)
            else:
               passed, detail = step["check"](None)

         counts["pass" if passed else "fail"] += 1
         line = {"key": step["key"], "finding": step["finding"], "status": response.status_code, "class": kind, "pass": passed, "detail": detail, "ms": int((time.monotonic() - started) * 1000), "bytes": len(response.content)}
         log.write(json.dumps(line) + "\n")
         print(json.dumps(line), flush=True)

         if kind in ("RateLimited", "ChallengeRequired"):
            print(json.dumps({"stopped": kind}), flush=True)
            break

   print(json.dumps({"summary": counts, "log": str(log_path.relative_to(ROOT)), "captures": str(capture_path.relative_to(ROOT))}), flush=True)


if __name__ == "__main__":
   main()
