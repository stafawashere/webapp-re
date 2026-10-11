from .. import endpoints
from ..catalogue import normalise
from ..config import BRAND_DIRECTORY_MAX_AGE_SECONDS
from ..errors import ContractBroken
from ..models import require_list

BRAND_DIRECTORY_CACHE_FILE = "brand-directory.json"
BRAND_FIELDS = ("brand_id", "brand_name", "affinities", "departure_apis")


def list_cities(context, arguments):
   data = context.catalogue.load(refresh=bool(arguments.get("refresh")))
   wanted = normalise(arguments.get("query") or "")
   regions = []

   for region in data["regions"]:
      names = [region["name"], region["slug"], region["region_id"]] + list(region["aliases"]) + [city["name"] for city in region["cities"]]
      matches = not wanted or any(wanted in normalise(name) for name in names)

      if not matches:
         continue

      regions.append({
         "region_id": region["region_id"],
         "slug": region["slug"],
         "name": region["name"],
         "aliases": region["aliases"],
         "api_enabled": region["api_enabled"],
         "bounding_box": region["bounding_box"],
         "cities": [{"city_id": city["city_id"], "slug": city["slug"], "name": city["name"]} for city in region["cities"]],
      })

   return {"fetched_at": data.get("fetched_at"), "regions": regions}


def get_city(context, arguments):
   region = context.region(arguments.get("city"))
   config = context.region_config(region)
   modes = []

   for mode in config.get("nearby_modes") or []:
      modes.append({"mode_id": mode.get("mode_id", ""), "slug": mode.get("mode_slug", ""), "title": mode.get("short_title", ""), "brand_ids": list(mode.get("request_brand_ids") or []), "kinds": list(mode.get("kind_ids") or [])})

   if not config.get("timezone"):
      raise ContractBroken("region-info has no timezone.", {"region_id": region["region_id"]})

   return {
      "region_id": region["region_id"],
      "slug": region["slug"],
      "name": region["name"],
      "timezone": config["timezone"],
      "bounding_box": config.get("bounding_box") or region["bounding_box"],
      "default_place": config.get("default_place") or {},
      "nearby_modes": modes,
      "core_brand_ids": list(config.get("core_brand_ids") or []),
      "distance_units": config.get("distance_units"),
      "api_enabled": bool(config.get("api_enabled")),
   }


def brand_directory(context):
   brand_cache = context.cached_value(BRAND_DIRECTORY_CACHE_FILE, BRAND_DIRECTORY_MAX_AGE_SECONDS)
   cached = brand_cache.get()

   if isinstance(cached, list):
      return cached

   response = context.send(endpoints.BRAND_DIRECTORY)
   brands = [{field: brand.get(field) for field in BRAND_FIELDS} for brand in require_list(response, "brands", "brand directory")]
   brand_cache.put(brands)
   return brands


def list_brands(context, arguments):
   brands = brand_directory(context)
   wanted = normalise(arguments.get("query") or "")
   allowed_ids = None

   if arguments.get("city"):
      region = context.region(arguments["city"])
      config = context.region_config(region)
      allowed_ids = set(config.get("core_brand_ids") or [])

      for mode in config.get("nearby_modes") or []:
         allowed_ids.update(mode.get("request_brand_ids") or [])

   records = []
   for brand in brands:
      brand_id = str(brand.get("brand_id", ""))
      name = brand.get("brand_name")
      in_city = allowed_ids is None or brand_id in allowed_ids
      matches = not wanted or wanted in normalise(brand_id) or wanted in normalise(name or "")

      if in_city and matches:
         records.append({"id": brand_id, "name": name, "affinities": list(brand.get("affinities") or []), "departure_apis": list(brand.get("departure_apis") or [])})

   return {"brands": records}
