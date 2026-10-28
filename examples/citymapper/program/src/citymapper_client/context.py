from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import endpoints
from .catalogue import CachedValue, Catalogue, KeyedCache, RegionConfigs
from .config import PLACE_CACHE_MAX_AGE_SECONDS, STOP_CACHE_MAX_AGE_SECONDS, site_paths
from .errors import ContractBroken, NotFound, UsageError
from .models import Place, coords_of, require_list
from .pacing import Pacer
from .session import Session
from .transport import Request, Transport

NON_PLACE_RESULT_TYPES = ("heading", "attribution")
PAST_CLOCK_TIME_GRACE = timedelta(minutes=15)
SEARCH_CACHE_MAX_AGE_SECONDS = 10 * 60


@dataclass
class Context:
   transport: object
   catalogue: object
   region_configs: object
   session: object
   paths: object
   cache_text_places: bool = False
   env_file: object = None

   def __post_init__(self):
      if self.env_file is None:
         self.env_file = self.paths.env_file

   @classmethod
   def build(cls, env_file=None, paths=None, transport=None, run_id=None, command=None):
      paths = paths or site_paths()
      cookie_file = Path(env_file).expanduser() if env_file else paths.env_file
      session = Session.from_env(cookie_file)
      pacer = Pacer(paths.pacer_state)
      transport = transport or Transport(session, pacer, paths.logs_dir, run_id=run_id, command=command)
      return cls(transport=transport, catalogue=Catalogue(transport, paths.cache_dir), region_configs=RegionConfigs(transport, paths.cache_dir), session=session, paths=paths, env_file=cookie_file)

   def send(self, endpoint, **request_options):
      return self.transport.send(Request(endpoint, **request_options))

   def region_cache(self, prefix, region, max_age_seconds):
      return KeyedCache(self.paths.cache_dir / "{0}-{1}.json".format(prefix, region["region_id"]), max_age_seconds)

   def stop_cache(self, region):
      return self.region_cache("stops", region, STOP_CACHE_MAX_AGE_SECONDS)

   def place_cache(self, region):
      return self.region_cache("places", region, PLACE_CACHE_MAX_AGE_SECONDS)

   def search_cache(self, region):
      return self.region_cache("searches", region, SEARCH_CACHE_MAX_AGE_SECONDS)

   def resolved_place_cache(self, region):
      return self.region_cache("placeids", region, PLACE_CACHE_MAX_AGE_SECONDS)

   def cached_value(self, file_name, max_age_seconds):
      return CachedValue(self.paths.cache_dir / file_name, max_age_seconds)

   def region(self, city_text):
      return self.catalogue.resolve(city_text)

   def region_config(self, region):
      return self.region_configs.get(region["region_id"])

   def timezone_for(self, region):
      config = self.region_config(region)
      return ZoneInfo(config.get("timezone") or "UTC")

   def check_in_region(self, region, coords):
      box = region.get("bounding_box") or {}
      southwest = box.get("southwest_corner_coords")
      northeast = box.get("northeast_corner_coords")

      if not southwest or not northeast:
         return

      inside_latitude = southwest[0] <= coords[0] <= northeast[0]
      inside_longitude = southwest[1] <= coords[1] <= northeast[1]
      is_inside = inside_latitude and inside_longitude

      if not is_inside:
         raise UsageError("{0},{1} is outside {2}. Citymapper only plans inside the city's area.".format(coords[0], coords[1], region["name"]), {"region_id": region["region_id"]})

   def place(self, region, text, label):
      if text is None:
         raise UsageError("Pass --{0}.".format(label))

      coords = parse_coords(text)
      if coords is not None:
         self.check_in_region(region, coords)
         return Place(name=text, coords=coords)

      place_cache = self.place_cache(region) if self.cache_text_places else None
      query_key = place_query_key(text)
      cached_place = place_from_cache(place_cache.get(query_key)) if place_cache is not None else None

      if cached_place:
         self.check_in_region(region, cached_place.coords)
         return cached_place

      results = search(self, region, text)
      for place in results:
         if not place.coords and place.id:
            place = resolve_place(self, region, place)

         if place.coords:
            self.check_in_region(region, place.coords)

            if place_cache is not None:
               place_cache.put([query_key], place.as_dict())

            return place

      raise NotFound("No place with coordinates matches '{0}' in {1}.".format(text, region["name"]), {"query": text})

   def to_utc_iso(self, region, text, now=None):
      if not text:
         return None

      cleaned = text.strip()
      is_clock_time = len(cleaned) <= 5 and ":" in cleaned

      try:
         if is_clock_time:
            zone = self.timezone_for(region)
            local_now = (now or datetime.now(timezone.utc)).astimezone(zone)
            hour, minute = (int(part) for part in cleaned.split(":"))
            local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            has_already_passed = local < local_now - PAST_CLOCK_TIME_GRACE
            if has_already_passed:
               local = local + timedelta(days=1)
         else:
            local = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            if local.tzinfo is None:
               local = local.replace(tzinfo=self.timezone_for(region))
      except ValueError as error:
         raise UsageError("Times are HH:MM in the city's timezone (today, or tomorrow once that time is more than 15 minutes past) or ISO 8601 for any other day, got '{0}'.".format(text)) from error

      return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_coords(text):
   if not isinstance(text, str) or "," not in text:
      return None

   try:
      return coords_of(text.replace(" ", ""))
   except ValueError:
      return None


def place_query_key(text):
   return " ".join(text.lower().split())


def place_from_cache(cached):
   if not isinstance(cached, dict):
      return None

   try:
      place = Place.from_search(cached)
   except (ContractBroken, TypeError, ValueError):
      return None

   return place if place.coords else None


def search_cache_key(query, near):
   near_part = "{0},{1}".format(near[0], near[1]) if near else ""
   return "{0}|{1}".format(place_query_key(query), near_part)


def places_from_cache(cached):
   is_usable_list = isinstance(cached, list) and len(cached) > 0
   if not is_usable_list:
      return None

   try:
      return [Place.from_search(item) for item in cached]
   except (ContractBroken, TypeError, ValueError, AttributeError):
      return None


def search(context, region, query, near=None):
   search_cache = context.search_cache(region) if context.cache_text_places else None
   cache_key = search_cache_key(query, near)
   cached_places = places_from_cache(search_cache.get(cache_key)) if search_cache is not None else None

   if cached_places is not None:
      return cached_places

   body = {"query": query, "region_id": region["region_id"], "is_refinement": True, "refinement_data": {"is_chain": True}, "powersearch": False}

   if near:
      body["location"] = "{0},{1}".format(near[0], near[1])

   headers = {"Citymapper-Client": "Web Search", "Citymapper-Region": region["region_id"]}
   response = context.send(endpoints.SEARCH, form_json=body, headers=headers)
   items = [item for item in require_list(response, "results", "search response") if item.get("result_type") not in NON_PLACE_RESULT_TYPES]
   places = [Place.from_search(item) for item in items]

   should_cache = search_cache is not None and len(places) > 0
   if should_cache:
      search_cache.put([cache_key], [place.as_dict() for place in places])

   return places


def resolve_place(context, region, place):
   resolved_cache = context.resolved_place_cache(region) if context.cache_text_places and place.id else None
   cached_place = place_from_cache(resolved_cache.get(place.id)) if resolved_cache is not None else None

   if cached_place:
      return cached_place

   response = context.send(endpoints.PLACE_RESOLVE, query={"id": place.id, "region_id": region["region_id"]})
   resolved = response.get("place_result") if isinstance(response, dict) else None

   if not resolved:
      return place

   merged = {**place.as_dict(), **{key: value for key, value in resolved.items() if value is not None}}
   merged.setdefault("name", place.name)
   merged_place = Place.from_search(merged)

   if resolved_cache is not None and merged_place.coords:
      resolved_cache.put([place.id], merged_place.as_dict())

   return merged_place
