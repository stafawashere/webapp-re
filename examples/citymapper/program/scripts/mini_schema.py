"""A small JSON Schema subset validator: type (single or list), required, properties, items, enum, minItems, maxItems."""

TYPE_CHECKS = {
   "object": lambda value: isinstance(value, dict),
   "array": lambda value: isinstance(value, list),
   "string": lambda value: isinstance(value, str),
   "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
   "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
   "boolean": lambda value: isinstance(value, bool),
   "null": lambda value: value is None,
}


def validate(value, schema, path="$"):
   problems = []
   expected = schema.get("type")

   if expected:
      allowed = expected if isinstance(expected, list) else [expected]
      matches_type = any(TYPE_CHECKS[name](value) for name in allowed)

      if not matches_type:
         return ["{0}: expected {1}, got {2}".format(path, "/".join(allowed), type(value).__name__)]

   if "enum" in schema and value not in schema["enum"]:
      problems.append("{0}: {1!r} not in enum".format(path, value))

   if isinstance(value, dict):
      for key in schema.get("required") or []:
         if key not in value:
            problems.append("{0}: missing {1}".format(path, key))

      for key, child_schema in (schema.get("properties") or {}).items():
         if key in value:
            problems.extend(validate(value[key], child_schema, path + "." + key))

   if isinstance(value, list):
      too_short = "minItems" in schema and len(value) < schema["minItems"]
      too_long = "maxItems" in schema and len(value) > schema["maxItems"]

      if too_short or too_long:
         problems.append("{0}: {1} items outside the allowed count".format(path, len(value)))

      for index, item in enumerate(value):
         if "items" in schema:
            problems.extend(validate(item, schema["items"], "{0}[{1}]".format(path, index)))

   return problems
