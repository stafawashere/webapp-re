"""Signed-in reads and writes. Shapes come from the web bundle; none was observed live (you are signed out)."""
import json
import time
from datetime import datetime, timezone

from .. import endpoints
from ..errors import SessionExpired, UsageError
from ..models import coords_of
from ..transport import Request
from .departures import stop_details
from .lines import route_info

FAVOURITE_TARGET_TYPES = {"stop": 1, "busstop": 1, "station": 2, "line": 3, "route": 3}


def require_session(context):
   if not context.session.signed_in:
      raise SessionExpired("No Citymapper session stored. Sign in on citymapper.com in your browser yourself, then run adopt-session.", {"env_file": str(context.env_file)})


def require_csrf_token(context, request):
   has_csrf_token = bool(context.session.cookies.get("csrftoken"))
   is_missing_token = request.endpoint.csrf and not has_csrf_token

   if is_missing_token:
      raise SessionExpired("This call needs the csrftoken cookie and none is stored. Copy the Cookie header of a citymapper.com request again (it must include csrftoken), then run adopt-session.", {"env_file": str(context.env_file)})


def require_approved_request(arguments, request):
   approved_digest = arguments.get("confirm")

   if not approved_digest:
      raise UsageError("--yes also needs --confirm with the confirm value from the dry run you approved. Nothing was sent.", {"request": request.describe()})

   if approved_digest != request.confirm_digest():
      raise UsageError("This request differs from the dry run you approved, so nothing was sent. Run --dry-run again, show the new request and ask for approval.", {"request": request.describe(), "approved_confirm": approved_digest})


def perform_write(context, arguments, request, needs_session=True):
   if arguments.get("dry_run"):
      return {"dry_run": True, "request": request.describe(), "confirm": request.confirm_digest()}

   if not arguments.get("yes"):
      raise UsageError("This changes your account. Run with --dry-run, approve the exact call in chat, then rerun with --yes --confirm <confirm from the dry run>.", {"request": request.describe()})

   if needs_session:
      require_session(context)

   require_csrf_token(context, request)
   require_approved_request(arguments, request)
   return context.transport.send(request)


def whoami(context, arguments):
   try:
      user = context.send(endpoints.USER_DATA)
   except SessionExpired:
      return {"signed_in": False, "user": {}}

   return {"signed_in": True, "user": user if isinstance(user, dict) else {}}


def list_saved_places(context, arguments):
   require_session(context)
   response = context.send(endpoints.PLACES)
   places = []

   for item in (response or {}).get("items") or []:
      places.append({"id": str(item.get("place_id", "")), "name": item.get("name", ""), "role": item.get("role") or None, "address": item.get("address"), "coords": coords_of(item.get("coords")), "region": item.get("region_code")})

   return {"places": places}


def list_favourites(context, arguments):
   require_session(context)
   response = context.send(endpoints.FAVOURITES)
   region_id = context.region(arguments["city"])["region_id"] if arguments.get("city") else None
   favourites = []

   for item in (response or {}).get("items") or []:
      in_city = region_id is None or item.get("region_code") == region_id

      if in_city:
         favourites.append({"id": str(item.get("favorite_id", "")), "type": str(item.get("target_type_code", "")), "target_id": str(item.get("target_id", "")), "name": item.get("name"), "region_id": item.get("region_code")})

   return {"favourites": favourites}


def pass_headers(context, arguments):
   if not arguments.get("use_web_session_id"):
      raise UsageError("Citymapper Pass needs a Session-Id from the Citymapper app, and the web shows no source for it. --use-web-session-id sends your web sessionid cookie as Session-Id instead; that is an unproven guess.")

   return {"User-Device": context.session.cookies.get("uid", ""), "Session-Id": context.session.cookies.get("sessionid", "")}


def pass_account(context, arguments):
   require_session(context)
   body = {"payment_provider_id": arguments.get("provider") or "stripe"}
   return {"raw": context.transport.send(Request(endpoints.PASS_USER_INFO, json_body=body, headers=pass_headers(context, arguments)))}


def pass_session_time(context, arguments):
   require_session(context)
   response = context.transport.send(Request(endpoints.PASS_SESSION_TTL, headers=pass_headers(context, arguments)))
   seconds = response.get("seconds_remaining") or response.get("ttl") if isinstance(response, dict) else None
   return {"seconds": seconds, "raw": response}


def pass_write(context, arguments, endpoint, needs_method):
   provider = arguments.get("provider")
   method_id = arguments.get("payment_method_id")

   if not provider:
      raise UsageError("Pass --provider (the payment provider id).")

   if needs_method and not method_id:
      raise UsageError("Pass --payment-method-id (a token from the payment provider; never a card number).")

   body = {"payment_provider_id": provider}
   if needs_method:
      body["payment_method_id"] = method_id

   result = perform_write(context, arguments, Request(endpoint, json_body=body, headers=pass_headers(context, arguments)))
   return result if arguments.get("dry_run") else {"raw": result}


def pass_set_default_payment(context, arguments):
   return pass_write(context, arguments, endpoints.PASS_SET_DEFAULT, True)


def pass_add_payment_method(context, arguments):
   return pass_write(context, arguments, endpoints.PASS_ADD_METHOD, True)


def pass_remove_payment_method(context, arguments):
   return pass_write(context, arguments, endpoints.PASS_DELETE_METHOD, True)


def pass_remove_all_payment_methods(context, arguments):
   return pass_write(context, arguments, endpoints.PASS_DELETE_ALL, False)


def iso_now():
   return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + "{0:03d}Z".format(datetime.now(timezone.utc).microsecond // 1000)


def save_place(context, arguments):
   region = context.region(arguments.get("city"))
   place = context.place(region, arguments.get("near"), "near")
   now = iso_now()
   role = arguments.get("role") or ""
   address = place.address or ""
   body = {
      "address": address,
      "coords": place.coords,
      "created": now,
      "editability": 1,
      "modified": now,
      "my_places_order": 0,
      "name": arguments.get("name") or place.name,
      "place_type": 2,
      "populated": True,
      "region_code": region["region_id"],
      "role": role,
      "section": "Special",
      "source": 0,
      "template_place_id": "",
   }
   result = perform_write(context, arguments, Request(endpoints.PLACE_CREATE, json_body=body))
   return result if arguments.get("dry_run") else {"place": result}


def update_place(context, arguments):
   identifier = arguments.get("id")

   if not identifier:
      raise UsageError("Pass --id of the saved place (from list-saved-places).")

   body = {}
   if arguments.get("name"):
      body["name"] = arguments["name"]

   if arguments.get("near"):
      region = context.region(arguments.get("city"))
      place = context.place(region, arguments["near"], "near")
      body.update({"coords": place.coords, "address": place.address or ""})

   if not body:
      raise UsageError("Pass --name or --near to change.")

   result = perform_write(context, arguments, Request(endpoints.PLACE_UPDATE, json_body=body, path_values={"place_id": identifier}))
   return result if arguments.get("dry_run") else {"place": result}


def remove_place(context, arguments):
   identifier = arguments.get("id")

   if not identifier:
      raise UsageError("Pass --id of the saved place (from list-saved-places).")

   result = perform_write(context, arguments, Request(endpoints.PLACE_DELETE, path_values={"place_id": identifier}))
   return result if arguments.get("dry_run") else {"removed": True}


def add_favourite(context, arguments):
   region = context.region(arguments.get("city"))
   has_stop = bool(arguments.get("stop"))
   has_line = bool(arguments.get("line"))

   if has_stop == has_line:
      raise UsageError("Pass exactly one of --stop or --line.")

   if has_stop:
      stop, _ = stop_details(context, region, arguments["stop"])
      sharing = stop.get("sharing_urls") or []
      departure_api = sharing[0].get("departure_api") if sharing else None
      kind = "busstop" if departure_api == "departures" else "station"
      target_type = FAVOURITE_TARGET_TYPES[kind]
      body = {"brand_code": (stop.get("brand_ids") or [""])[0], "coords": coords_of(stop.get("coords")), "name": stop.get("name", ""), "region_code": region["region_id"], "short_name": stop.get("name", ""), "target_id": str(stop["id"]), "target_type": target_type}
   else:
      route, _ = route_info(context, region, arguments["line"])
      route_id = route.get("live_line_code") or (route.get("aliases") or [arguments["line"]])[0]
      body = {"brand_code": route.get("brand", ""), "coords": None, "name": route.get("long_name") or route.get("name", ""), "region_code": region["region_id"], "short_name": route.get("name", ""), "target_id": str(route_id), "target_type": FAVOURITE_TARGET_TYPES["line"]}

   result = perform_write(context, arguments, Request(endpoints.FAVOURITE_CREATE, json_body=body))
   return result if arguments.get("dry_run") else {"favourite": result}


def remove_favourite(context, arguments):
   identifier = arguments.get("id")

   if not identifier:
      raise UsageError("Pass --id of the favourite (from list-favourites).")

   result = perform_write(context, arguments, Request(endpoints.FAVOURITE_DELETE, path_values={"favourite_id": identifier}))
   return result if arguments.get("dry_run") else {"removed": True}


def save_journey(context, arguments):
   region = context.region(arguments.get("city"))
   signature = arguments.get("signature")

   if not signature:
      raise UsageError("Pass --signature from a plan-journey result.")

   document = {"region_id": region["region_id"], "created": int(time.time()), "signature": signature, "shared": False, "associated_journeys": []}
   result = perform_write(context, arguments, Request(endpoints.SAVED_JOURNEY_CREATE, json_body={"document_data": json.dumps(document)}))

   if arguments.get("dry_run"):
      return result

   document_id = (result or {}).get("document_id") or ((result or {}).get("document") or {}).get("document_id")
   return {"document_id": str(document_id or ""), "raw": result}


def remove_saved_journey(context, arguments):
   identifier = arguments.get("document_id")

   if not identifier:
      raise UsageError("Pass --document-id (returned by save-journey).")

   result = perform_write(context, arguments, Request(endpoints.SAVED_JOURNEY_DELETE, path_values={"document_id": identifier}))
   return result if arguments.get("dry_run") else {"removed": True}


def update_profile(context, arguments):
   fields = {"first_name": arguments.get("first_name"), "last_name": arguments.get("last_name"), "mobile": arguments.get("mobile"), "is_interested_in_pass": arguments.get("interested_in_pass")}
   body = {key: value for key, value in fields.items() if value is not None}

   if not body:
      raise UsageError("Pass at least one of --first-name, --last-name, --mobile, --interested-in-pass.")

   result = perform_write(context, arguments, Request(endpoints.UPDATE_USER, json_body=body))
   return result if arguments.get("dry_run") else {"user": result if isinstance(result, dict) else {}}


def sign_out(context, arguments):
   result = perform_write(context, arguments, Request(endpoints.SIGN_OUT))
   return result if arguments.get("dry_run") else {"signed_out": True}
