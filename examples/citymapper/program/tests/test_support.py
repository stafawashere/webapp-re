import httpx
import pytest

from conftest import RealNetworkBlocked
from support import schema_errors

POINT_SCHEMA = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
RECORD_SCHEMA = {
   "type": "object",
   "properties": {
      "id": {"type": "string"},
      "count": {"type": "integer"},
      "note": {"type": ["string", "null"]},
      "size": {"type": "string", "enum": ["small", "large"]},
      "point": POINT_SCHEMA,
      "tags": {"type": "array", "items": {"type": "string"}},
   },
   "required": ["id"],
}


def test_checker_accepts_a_matching_record():
   record = {"id": "x1", "count": 3, "note": None, "size": "small", "point": [1.5, 2], "tags": ["a"]}

   assert schema_errors(record, RECORD_SCHEMA) == []


@pytest.mark.parametrize("record, expected_fragment", [
   ({"count": 1}, "missing required 'id'"),
   ({"id": 5}, "$.id: expected ['string']"),
   ({"id": "x", "count": 2.5}, "$.count: expected ['integer']"),
   ({"id": "x", "count": True}, "$.count: expected ['integer']"),
   ({"id": "x", "note": 7}, "$.note: expected ['string', 'null']"),
   ({"id": "x", "size": "medium"}, "is not one of"),
   ({"id": "x", "point": [1.0]}, "fewer than 2"),
   ({"id": "x", "point": [1.0, 2.0, 3.0]}, "more than 2"),
   ({"id": "x", "point": [1.0, "2"]}, "$.point[1]: expected ['number']"),
   ({"id": "x", "tags": ["ok", None]}, "$.tags[1]: expected ['string']"),
   (["not", "an", "object"], "$: expected ['object']"),
])
def test_checker_rejects_each_kind_of_mismatch(record, expected_fragment):
   errors = schema_errors(record, RECORD_SCHEMA)

   assert any(expected_fragment in error for error in errors), errors


def test_real_network_is_blocked_for_every_test():
   with httpx.Client() as client:
      with pytest.raises(RealNetworkBlocked):
         client.get("https://citymapper.invalid/api/1/traveltime")
