"""Typed records for Citymapper responses. Parsers fail with ContractBroken on missing required fields."""
from dataclasses import asdict, dataclass, field
from typing import Optional

from .errors import ContractBroken


def require(record, key, context):
   if not isinstance(record, dict) or key not in record or record[key] is None:
      raise ContractBroken("Citymapper's {0} lacks '{1}'.".format(context, key), {"context": context, "field": key})

   return record[key]


def require_list(record, key, context):
   value = require(record, key, context)

   if not isinstance(value, list):
      raise ContractBroken("Citymapper's {0} field '{1}' is not a list.".format(context, key), {"context": context, "field": key})

   return value


def coords_of(value):
   is_pair = isinstance(value, (list, tuple)) and len(value) == 2
   if is_pair:
      return [float(value[0]), float(value[1])]

   if isinstance(value, str) and "," in value:
      latitude, longitude = value.split(",", 1)
      return [float(latitude), float(longitude)]

   return None


class Record:
   def as_dict(self):
      return asdict(self)


@dataclass(frozen=True)
class Place(Record):
   name: str
   id: Optional[str] = None
   address: Optional[str] = None
   coords: Optional[list] = None
   type: Optional[str] = None
   source: Optional[str] = None
   brands: list = field(default_factory=list)
   lines: list = field(default_factory=list)

   @classmethod
   def from_search(cls, item):
      return cls(
         name=require(item, "name", "search result"),
         id=item.get("id"),
         address=item.get("address"),
         coords=coords_of(item.get("coords")),
         type=item.get("type"),
         source=item.get("source"),
         brands=list(item.get("brands") or []),
         lines=list(item.get("lines") or []),
      )


@dataclass(frozen=True)
class RouteRef(Record):
   id: str
   name: str
   brand_id: Optional[str] = None
   color: Optional[str] = None

   @classmethod
   def from_leg_route(cls, route):
      return cls(id=str(require(route, "id", "leg route")), name=route.get("display_name") or route.get("name") or str(route["id"]), brand_id=route.get("brand_id"), color=route.get("color"))


@dataclass(frozen=True)
class Leg(Record):
   mode: str
   duration_seconds: Optional[int] = None
   distance_meters: Optional[int] = None
   departure_time: Optional[str] = None
   arrival_time: Optional[str] = None
   routes: list = field(default_factory=list)
   stops: list = field(default_factory=list)
   path: list = field(default_factory=list)

   @classmethod
   def from_api(cls, leg, include_path):
      stops = []

      for stop in leg.get("stops") or []:
         stops.append({"id": str(stop.get("id", "")), "name": stop.get("name", ""), "coords": coords_of(stop.get("coords")) or []})

      path = [coords_of(point) for point in (leg.get("shape") or leg.get("path") or [])] if include_path else []
      return cls(
         mode=require(leg, "mode", "journey leg"),
         duration_seconds=leg.get("duration_seconds", leg.get("duration")),
         distance_meters=leg.get("distance_meters", leg.get("distance")),
         departure_time=leg.get("departure_time"),
         arrival_time=leg.get("arrival_time"),
         routes=[RouteRef.from_leg_route(route).as_dict() for route in leg.get("routes") or []],
         stops=stops,
         path=[point for point in path if point],
      )


@dataclass(frozen=True)
class Journey(Record):
   index: int
   duration_seconds: int
   legs: list
   signature: str
   walk_seconds: Optional[int] = None
   distance_meters: Optional[int] = None
   calories: Optional[int] = None
   price: Optional[str] = None
   currency: Optional[str] = None
   departure_time: Optional[str] = None
   arrival_time: Optional[str] = None
   step_free: Optional[bool] = None
   profile: Optional[str] = None

   @classmethod
   def from_api(cls, index, journey, include_path=False):
      legs = [Leg.from_api(leg, include_path) for leg in require_list(journey, "legs", "journey")]
      timed_legs = [leg for leg in legs if leg.departure_time or leg.arrival_time]
      first_departure = next((leg.departure_time for leg in timed_legs if leg.departure_time), None)
      last_arrival = next((leg.arrival_time for leg in reversed(timed_legs) if leg.arrival_time), None)
      return cls(
         index=index,
         duration_seconds=int(require(journey, "duration_seconds", "journey")),
         legs=[leg.as_dict() for leg in legs],
         signature=require(journey, "signature", "journey"),
         walk_seconds=journey.get("walk_seconds"),
         distance_meters=journey.get("distance_meters"),
         calories=journey.get("calories"),
         price=journey.get("formatted_price"),
         currency=journey.get("currency_code"),
         departure_time=first_departure,
         arrival_time=last_arrival,
         step_free=journey.get("step_free"),
         profile=journey.get("profile_localized_name") or journey.get("profile_id") or journey.get("journey_kind"),
      )


@dataclass(frozen=True)
class Status(Record):
   level: int
   summary: str
   description: Optional[str] = None

   @classmethod
   def from_api(cls, status):
      status = status or {}
      return cls(level=int(status.get("level", 0)), summary=status.get("summary") or "", description=status.get("description") or None)


@dataclass(frozen=True)
class LineSummary(Record):
   id: str
   name: str
   status: dict
   long_name: Optional[str] = None
   brand: Optional[str] = None
   mode: Optional[str] = None
   aliases: list = field(default_factory=list)
   color: Optional[str] = None

   @classmethod
   def from_api(cls, route):
      identifier = route.get("id") or route.get("live_line_code") or (route.get("aliases") or [None])[0] or require(route, "name", "line")
      return cls(
         id=str(identifier),
         name=require(route, "name", "line"),
         status=Status.from_api(route.get("status")).as_dict(),
         long_name=route.get("long_name"),
         brand=route.get("brand") or route.get("brand_id"),
         mode=route.get("mode"),
         aliases=list(route.get("aliases") or []),
         color=route.get("color"),
      )


@dataclass(frozen=True)
class NearbyElement(Record):
   id: str
   name: str
   kind: str
   coords: list
   alias: Optional[str] = None
   walk_time_seconds: Optional[int] = None
   routes: list = field(default_factory=list)
   brand_ids: list = field(default_factory=list)
   bikes_available: Optional[int] = None
   spaces_available: Optional[int] = None
   electric_available: Optional[int] = None

   @classmethod
   def from_api(cls, element):
      coords = coords_of(require(element, "coords", "nearby element"))

      if coords is None:
         raise ContractBroken("A nearby element has unreadable coordinates.", {"id": element.get("id")})

      return cls(
         id=str(require(element, "id", "nearby element")),
         name=require(element, "name", "nearby element"),
         kind=require(element, "kind", "nearby element"),
         coords=coords,
         alias=element.get("alias"),
         walk_time_seconds=element.get("walk_time_seconds"),
         routes=list(element.get("route_names") or element.get("route_ids") or []),
         brand_ids=list(element.get("brand_ids") or ([element["brand_id"]] if element.get("brand_id") else [])),
         bikes_available=element.get("cycles_available"),
         spaces_available=element.get("cycles_spaces"),
         electric_available=element.get("cycles_electric_available"),
      )


@dataclass(frozen=True)
class Departure(Record):
   route_id: str
   is_live: bool
   route_name: Optional[str] = None
   destination: Optional[str] = None
   platform_or_direction: Optional[str] = None
   seconds_away: Optional[int] = None
   time: Optional[str] = None
   scheduled_time: Optional[str] = None
   advisory: Optional[str] = None
