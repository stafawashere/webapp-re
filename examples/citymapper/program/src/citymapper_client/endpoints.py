"""Every URL and path the program sends. Each literal cites the knowledge base finding it comes from."""
from dataclasses import dataclass


ORIGIN = "https://citymapper.com"  # finding: journeys


@dataclass(frozen=True)
class Endpoint:
   finding: str
   method: str
   path: str
   host: str = ORIGIN
   expect: str = "json"
   signed_in: bool = False
   sends_cookies: bool = False
   csrf: bool = False
   # A GET that changes state on the site, so it is never resent after a timeout.
   writes: bool = False

   def url(self, **path_values):
      return self.host + self.path.format(**path_values)


@dataclass(frozen=True)
class PendingEndpoint(Endpoint):
   """A contract read from the web bundle that cannot be replayed without your session or approval."""

   pending: bool = True


CITIES_PAGE = Endpoint("cities-html", "GET", "/cities", expect="html")  # finding: cities-html
CITY_PAGE = Endpoint("city-html", "GET", "/{region_slug}", expect="html")  # finding: city-html
REGION_INFO = Endpoint("resource-region-info", "GET", "/resource/region-info/{region_id}")  # finding: resource-region-info
BRAND_DIRECTORY = Endpoint("resource-brand-directory", "GET", "/resource/brand-directory")  # finding: resource-brand-directory

SEARCH = Endpoint("searchpost", "POST", "/api/4/searchpost")  # finding: searchpost
PLACE_RESOLVE = Endpoint("placeresolve", "GET", "/api/1/placeresolve")  # finding: placeresolve
GEOCODE = Endpoint("geocode", "GET", "/geocode")  # finding: geocode

JOURNEYS = Endpoint("journeys", "GET", "/api/7/journeys")  # finding: journeys
WALK = Endpoint("walk7", "GET", "/api/7/walk")  # finding: walk7
WALK_V1 = Endpoint("walk1", "GET", "/api/1/walk")  # finding: walk1
CYCLE = Endpoint("cycle", "GET", "/api/6/cycle")  # finding: cycle
TAXI = Endpoint("taxi", "GET", "/api/2/taxi")  # finding: taxi
JOURNEY_TIMES = Endpoint("journeytimes", "POST", "/api/1/journeytimes")  # finding: journeytimes
REFRESH_JOURNEYS = Endpoint("refreshjourneys", "POST", "/api/1/refreshjourneys")  # finding: refreshjourneys
TRIP_META = Endpoint("trip-meta", "GET", "/trip/signature", expect="html")  # finding: trip-meta
GET_TRIP = PendingEndpoint("gettrip", "GET", "/api/1/gettrip")  # finding: gettrip
TRAVEL_TIME = Endpoint("traveltime", "GET", "/api/1/traveltime")  # finding: traveltime

NEARBY = Endpoint("nearby3", "GET", "/api/3/nearby")  # finding: nearby3
NEARBY_V2 = Endpoint("nearby2", "GET", "/api/2/nearby")  # finding: nearby2
STOP_INFO = Endpoint("stopinfo", "GET", "/api/3/stopinfo")  # finding: stopinfo
BUS_DEPARTURES = Endpoint("departures-bus", "GET", "/api/1/departures")  # finding: departures-bus
METRO_DEPARTURES = Endpoint("departures-metro", "GET", "/api/2/metrodepartures")  # finding: departures-metro
RAIL_DEPARTURES = Endpoint("departures-rail", "GET", "/api/1/raildepartures")  # finding: departures-rail
SCHEDULES = Endpoint("schedules", "GET", "/api/1/schedules")  # finding: schedules

ROUTE_STATUS = Endpoint("routestatus", "GET", "/api/1/routestatus")  # finding: routestatus
ROUTE_INFO = Endpoint("routeinfo1", "GET", "/api/1/routeinfo")  # finding: routeinfo1
ROUTE_INFO_MANY = Endpoint("routeinfo2", "GET", "/api/2/routeinfo")  # finding: routeinfo2
MESSAGE = Endpoint("message", "GET", "/api/2/message")  # finding: message
FIND_TRANSPORT = Endpoint("findtransport", "GET", "/api/2/findtransport")  # finding: findtransport
VEHICLE_LOCATIONS = Endpoint("vehiclelocations", "GET", "/api/1/vehiclelocations")  # finding: vehiclelocations
ROUTE_PATHS = Endpoint("routepaths", "GET", "/api/1/routepaths")  # finding: routepaths
EVERYTHING_MAP = Endpoint("everythingmap", "GET", "/api/1/everythingmap")  # finding: everythingmap
GET_SHORT_URL = PendingEndpoint("getshorturl", "GET", "/api/1/getshorturl")  # finding: getshorturl
NEWS_PAGE = Endpoint("news-html", "GET", "/news", expect="html")  # finding: news-html
BLOG = Endpoint("blog", "GET", "/api/1/blog")  # finding: blog
RESOURCES = Endpoint("resources", "GET", "/api/1/resources", expect="html")  # finding: resources

USER_DATA = Endpoint("identity-user-data", "GET", "/api/1/identity/user_data", signed_in=True)  # finding: identity-user-data
PLACES = PendingEndpoint("identity-places-list", "GET", "/api/1/identity/places", signed_in=True)  # finding: identity-places-list
PLACE_CREATE = PendingEndpoint("identity-places-create", "POST", "/api/1/identity/places", signed_in=True)  # finding: identity-places-create
PLACE_UPDATE = PendingEndpoint("identity-places-update", "PUT", "/api/1/identity/places/{place_id}", signed_in=True)  # finding: identity-places-update
PLACE_DELETE = PendingEndpoint("identity-places-delete", "DELETE", "/api/1/identity/places/{place_id}", signed_in=True)  # finding: identity-places-delete
FAVOURITES = PendingEndpoint("identity-favorites-list", "GET", "/api/1/identity/favorites", signed_in=True)  # finding: identity-favorites-list
FAVOURITE_CREATE = PendingEndpoint("identity-favorites-create", "POST", "/api/1/identity/favorites", signed_in=True)  # finding: identity-favorites-create
FAVOURITE_DELETE = PendingEndpoint("identity-favorites-delete", "DELETE", "/api/1/identity/favorites/{favourite_id}", signed_in=True)  # finding: identity-favorites-delete
SAVED_JOURNEY_CREATE = PendingEndpoint("identity-save-journey", "POST", "/api/1/identity/documents/SavedJourney", signed_in=True)  # finding: identity-save-journey
SAVED_JOURNEY_DELETE = PendingEndpoint("identity-delete-journey", "DELETE", "/api/1/identity/documents/SavedJourney/{document_id}", signed_in=True)  # finding: identity-delete-journey
UPDATE_USER = PendingEndpoint("identity-update-user", "POST", "/api/1/identity/update_user", signed_in=True)  # finding: identity-update-user
SIGN_OUT = PendingEndpoint("identity-sessions-delete", "DELETE", "/api/1/identity/sessions", signed_in=True)  # finding: identity-sessions-delete

CREATE_TRIP_URL = PendingEndpoint("createtripurl", "GET", "/api/1/createtripurl", writes=True)  # finding: createtripurl
CREATE_SHORT_URL = PendingEndpoint("createshorturl", "GET", "/api/1/createshorturl", writes=True)  # finding: createshorturl
CITY_VOTE = PendingEndpoint("city-vote", "POST", "/cities/vote_submit/", sends_cookies=True, csrf=True)  # finding: city-vote

TURNSTILE_HOST = "https://turnstile-api.citymapper.com"  # finding: turnstile-userinfo
PASS_USER_INFO = PendingEndpoint("turnstile-userinfo", "POST", "/web/1/userinfo", host=TURNSTILE_HOST, signed_in=True)  # finding: turnstile-userinfo
PASS_SESSION_TTL = PendingEndpoint("turnstile-sessionttl", "GET", "/web/1/sessionttl", host=TURNSTILE_HOST, signed_in=True)  # finding: turnstile-sessionttl
PASS_ADD_METHOD = PendingEndpoint("turnstile-addpaymentmethod", "POST", "/web/1/addpaymentmethod", host=TURNSTILE_HOST, signed_in=True)  # finding: turnstile-addpaymentmethod
PASS_SET_DEFAULT = PendingEndpoint("turnstile-setdefaultpaymentmethod", "POST", "/web/1/setdefaultpaymentmethod", host=TURNSTILE_HOST, signed_in=True)  # finding: turnstile-setdefaultpaymentmethod
PASS_DELETE_METHOD = PendingEndpoint("turnstile-deletepaymentmethod", "POST", "/web/1/deletepaymentmethod", host=TURNSTILE_HOST, signed_in=True)  # finding: turnstile-deletepaymentmethod
PASS_DELETE_ALL = PendingEndpoint("turnstile-deleteallpaymentmethods", "POST", "/web/1/deleteallpaymentmethods", host=TURNSTILE_HOST, signed_in=True)  # finding: turnstile-deleteallpaymentmethods

ALL_ENDPOINTS = [value for value in list(globals().values()) if isinstance(value, Endpoint)]
PENDING_ENDPOINTS = [value for value in ALL_ENDPOINTS if isinstance(value, PendingEndpoint)]
