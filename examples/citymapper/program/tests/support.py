import json
import time
from pathlib import Path

from citymapper_client.catalogue import Catalogue, RegionConfigs, build_catalogue
from citymapper_client.config import Paths
from citymapper_client.context import Context
from citymapper_client.session import Session
from citymapper_client.transport import utc_now_iso

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
PORTVALE_REGION_ID = "zz-portvale"
SIGNED_IN_COOKIES = {"sessionid": "fake-session-value-0001", "csrftoken": "fake-csrf-value-0002", "uid": "fake-device-value-0003"}

JSON_TYPE_CHECKS = {
   "object": lambda value: isinstance(value, dict),
   "array": lambda value: isinstance(value, list),
   "string": lambda value: isinstance(value, str),
   "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
   "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
   "boolean": lambda value: isinstance(value, bool),
   "null": lambda value: value is None,
}


def load_fixture(name):
   return json.loads((FIXTURE_DIR / name).read_text())


def load_text_fixture(name):
   return (FIXTURE_DIR / name).read_text()


def schema_errors(instance, schema, location="$"):
   errors = []
   allowed_types = schema.get("type")

   if allowed_types is not None:
      type_names = allowed_types if isinstance(allowed_types, list) else [allowed_types]
      matches_a_type = any(JSON_TYPE_CHECKS[type_name](instance) for type_name in type_names)

      if not matches_a_type:
         errors.append("{0}: expected {1}, got {2!r}".format(location, type_names, instance))
         return errors

   has_enum = "enum" in schema
   if has_enum and instance not in schema["enum"]:
      errors.append("{0}: {1!r} is not one of {2}".format(location, instance, schema["enum"]))

   if isinstance(instance, dict):
      for required_key in schema.get("required") or []:
         if required_key not in instance:
            errors.append("{0}: missing required '{1}'".format(location, required_key))

      declared_properties = schema.get("properties")

      for key, property_schema in (declared_properties or {}).items():
         if key in instance:
            errors.extend(schema_errors(instance[key], property_schema, "{0}.{1}".format(location, key)))

      if declared_properties is not None:
         for undeclared_key in sorted(set(instance) - set(declared_properties)):
            errors.append("{0}: '{1}' is not declared in the schema".format(location, undeclared_key))

   if isinstance(instance, list):
      minimum_items = schema.get("minItems")
      maximum_items = schema.get("maxItems")
      is_too_short = minimum_items is not None and len(instance) < minimum_items
      is_too_long = maximum_items is not None and len(instance) > maximum_items

      if is_too_short:
         errors.append("{0}: {1} items, fewer than {2}".format(location, len(instance), minimum_items))

      if is_too_long:
         errors.append("{0}: {1} items, more than {2}".format(location, len(instance), maximum_items))

      item_schema = schema.get("items")
      if item_schema:
         for index, item in enumerate(instance):
            errors.extend(schema_errors(item, item_schema, "{0}[{1}]".format(location, index)))

   return errors


def assert_valid(instance, schema):
   errors = schema_errors(instance, schema)
   assert not errors, "\n".join(errors)


class FakeTransport:
   def __init__(self, responses=None):
      self.responses = dict(responses or {})
      self.requests = []
      self.first_sent_at = None
      self.last_sent_at = None

   def send(self, request):
      self.requests.append(request)
      self.last_sent_at = utc_now_iso()

      if self.first_sent_at is None:
         self.first_sent_at = self.last_sent_at

      finding = request.endpoint.finding
      assert finding in self.responses, "unexpected request to {0} ({1})".format(finding, request.url)
      body = self.responses[finding]

      if callable(body):
         body = body(request)

      if isinstance(body, Exception):
         raise body

      return body

   @property
   def findings(self):
      return [request.endpoint.finding for request in self.requests]

   def only_request(self, finding):
      matching = [request for request in self.requests if request.endpoint.finding == finding]
      assert len(matching) == 1, "expected one {0} request, got {1}".format(finding, self.findings)
      return matching[0]


def seed_catalogue(cache_dir):
   data = build_catalogue(load_text_fixture("cities.html"))
   data["fetched_at"] = time.time()
   cache_dir.mkdir(parents=True, exist_ok=True)
   (cache_dir / "catalogue.json").write_text(json.dumps(data))


def seed_region_config(cache_dir, config):
   cache_dir.mkdir(parents=True, exist_ok=True)
   cache_file = cache_dir / "region-{0}.json".format(config["region_id"])
   cache_file.write_text(json.dumps({"fetched_at": time.time(), "config": config}))


def signed_in_session():
   return Session(cookies=dict(SIGNED_IN_COOKIES))


def build_context(site_root, responses=None, session=None, region_config=None, with_cached_catalogue=True, with_cached_region=True):
   paths = Paths(site_root)
   fake = FakeTransport(responses)

   if with_cached_catalogue:
      seed_catalogue(paths.cache_dir)

   if with_cached_region:
      seed_region_config(paths.cache_dir, region_config or load_fixture("region_info.json"))

   context = Context(
      transport=fake,
      catalogue=Catalogue(fake, paths.cache_dir),
      region_configs=RegionConfigs(fake, paths.cache_dir),
      session=session or Session(),
      paths=paths,
   )
   return context, fake
