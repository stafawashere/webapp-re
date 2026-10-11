"""The region and city catalogue, parsed from the window.citymapper globals in a server-rendered page."""
import json
import re
import time
import unicodedata

from . import endpoints
from .config import CATALOGUE_MAX_AGE_SECONDS, REGION_CONFIG_MAX_AGE_SECONDS
from .errors import ContractBroken, NotFound, UsageError
from .transport import Request

GLOBAL_PATTERN = r"\n\s*window\.citymapper\.{0}\s*=\s*"
CATALOGUE_REGION_KEYS = {"region_id", "slug", "name", "aliases", "cities"}


def read_page_global(html, name):
   match = re.search(GLOBAL_PATTERN.format(re.escape(name)), html)

   if not match:
      raise ContractBroken("The page no longer sets window.citymapper.{0}.".format(name), {"global": name})

   line_end = html.find("\n", match.end())
   raw = html[match.end():line_end if line_end != -1 else None].strip().rstrip(";")

   try:
      return json.loads(raw)
   except ValueError as error:
      raise ContractBroken("window.citymapper.{0} is not JSON any more.".format(name), {"global": name}) from error


def normalise(text):
   decomposed = unicodedata.normalize("NFKD", text or "")
   ascii_only = "".join(character for character in decomposed if not unicodedata.combining(character))
   return re.sub(r"[^a-z0-9]+", "", ascii_only.lower())


def read_cache_file(cache_file):
   try:
      cached = json.loads(cache_file.read_text())
   except (OSError, ValueError):
      return None

   return cached if isinstance(cached, dict) else None


def write_cache_file(cache_file, data):
   cache_file.parent.mkdir(parents=True, exist_ok=True)
   cache_file.write_text(json.dumps(data))


def is_fresh(stamped, max_age_seconds, now):
   fetched_at = stamped.get("fetched_at") if isinstance(stamped, dict) else None
   has_numeric_stamp = isinstance(fetched_at, (int, float)) and not isinstance(fetched_at, bool)
   return has_numeric_stamp and now - fetched_at < max_age_seconds


def is_usable_catalogue(cached):
   regions = cached.get("regions") if isinstance(cached, dict) else None

   if not isinstance(regions, list):
      return False

   return all(isinstance(region, dict) and CATALOGUE_REGION_KEYS <= set(region) for region in regions)


def build_catalogue(html):
   region_pairs = read_page_global(html, "regions")
   cities = read_page_global(html, "citiesInRegions")
   regions = []

   for pair in region_pairs:
      region = pair[0] if isinstance(pair, list) else pair
      has_id = isinstance(region, dict) and region.get("region_id")

      if not has_id:
         raise ContractBroken("A region entry has no region_id.", {})

      regions.append({
         "region_id": region["region_id"],
         "slug": region.get("region_slug") or region["region_id"],
         "name": region.get("region_name") or region["region_id"],
         "aliases": region.get("region_name_aliases") or [],
         "api_enabled": bool(region.get("api_enabled")),
         "web_enabled": bool(region.get("web_enabled")),
         "bounding_box": region.get("bounding_box") or {},
         "default_coords": (region.get("default_place") or {}).get("coords"),
         "cities": [],
      })

   by_id = {region["region_id"]: region for region in regions}

   for city_slug, city in cities.items():
      region = by_id.get(city.get("region_id"))

      if region is None:
         continue

      region["cities"].append({"city_id": city.get("city_id", ""), "slug": city_slug, "name": city.get("city_name", city_slug), "show_in_switcher": bool(city.get("show_in_city_switcher"))})

   return {"fetched_at": time.time(), "regions": regions}


class Catalogue:
   def __init__(self, transport, cache_dir, clock=time.time):
      self.transport = transport
      self.cache_dir = cache_dir
      self.clock = clock
      self._data = None

   @property
   def cache_file(self):
      return self.cache_dir / "catalogue.json"

   def load(self, refresh=False):
      if self._data is not None and not refresh:
         return self._data

      cached = None if refresh else read_cache_file(self.cache_file)
      can_reuse = is_fresh(cached, CATALOGUE_MAX_AGE_SECONDS, self.clock()) and is_usable_catalogue(cached)

      if can_reuse:
         self._data = cached
         return cached

      html = self.transport.send(Request(endpoints.CITIES_PAGE))
      data = build_catalogue(html)
      write_cache_file(self.cache_file, data)
      self._data = data
      return data

   def resolve(self, text):
      if not text:
         raise UsageError("Pass --city (a slug like nyc, a region id like us-nyc, or a city name).")

      wanted = normalise(text)
      regions = self.load()["regions"]
      exact_checks = (
         lambda region: normalise(region["region_id"]) == wanted,
         lambda region: normalise(region["slug"]) == wanted,
         lambda region: normalise(region["name"]) == wanted,
         lambda region: any(normalise(alias) == wanted for alias in region["aliases"]),
         lambda region: any(normalise(city["slug"]) == wanted or normalise(city["name"]) == wanted for city in region["cities"]),
      )

      for check in exact_checks:
         for region in regions:
            if check(region):
               return region

      partial = [region for region in regions if wanted and wanted in normalise(region["name"])]
      if len(partial) == 1:
         return partial[0]

      suggestions = sorted(region["slug"] for region in partial)[:10]
      raise NotFound("No Citymapper city matches '{0}'. Run list-cities to see them.".format(text), {"suggestions": suggestions})


class RegionConfigs:
   def __init__(self, transport, cache_dir, clock=time.time):
      self.transport = transport
      self.cache_dir = cache_dir
      self.clock = clock

   def get(self, region_id, refresh=False):
      cache_file = self.cache_dir / "region-{0}.json".format(region_id)

      cached = None if refresh else read_cache_file(cache_file)
      has_config = cached is not None and isinstance(cached.get("config"), dict)
      can_reuse = has_config and is_fresh(cached, REGION_CONFIG_MAX_AGE_SECONDS, self.clock())

      if can_reuse:
         return cached["config"]

      config = self.transport.send(Request(endpoints.REGION_INFO, path_values={"region_id": region_id}))
      has_region = isinstance(config, dict) and config.get("region_id") == region_id

      if not has_region:
         raise ContractBroken("region-info did not return the region asked for.", {"region_id": region_id})

      write_cache_file(cache_file, {"fetched_at": self.clock(), "config": config})
      return config


class CachedValue:
   """One cached response body that expires as a whole."""

   def __init__(self, cache_file, max_age_seconds, clock=time.time):
      self.cache_file = cache_file
      self.max_age_seconds = max_age_seconds
      self.clock = clock

   def get(self):
      cached = read_cache_file(self.cache_file)
      can_reuse = is_fresh(cached, self.max_age_seconds, self.clock()) and "value" in cached

      return cached["value"] if can_reuse else None

   def put(self, value):
      write_cache_file(self.cache_file, {"fetched_at": self.clock(), "value": value})


class KeyedCache:
   """Lookups cached by key, where each entry expires on its own."""

   def __init__(self, cache_file, max_age_seconds, clock=time.time):
      self.cache_file = cache_file
      self.max_age_seconds = max_age_seconds
      self.clock = clock

   def fresh_entries(self):
      cached = read_cache_file(self.cache_file) or {}
      entries = cached.get("entries")

      if not isinstance(entries, dict):
         return {}

      now = self.clock()
      fresh = {}

      for key, entry in entries.items():
         holds_value = isinstance(entry, dict) and "value" in entry
         is_current = holds_value and is_fresh(entry, self.max_age_seconds, now)

         if is_current:
            fresh[key] = entry

      return fresh

   def get(self, key):
      entry = self.fresh_entries().get(key)
      return entry["value"] if entry else None

   def put(self, keys, value):
      entries = self.fresh_entries()
      now = self.clock()

      for key in keys:
         entries[key] = {"fetched_at": now, "value": value}

      write_cache_file(self.cache_file, {"entries": entries})

   def discard(self, should_discard):
      entries = self.fresh_entries()
      kept = {key: entry for key, entry in entries.items() if not should_discard(entry["value"])}

      if len(kept) != len(entries):
         write_cache_file(self.cache_file, {"entries": kept})
