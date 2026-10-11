"""Approval writes that publish links or send personal data."""
from .. import endpoints
from ..transport import Request
from .account import perform_write

GO_LINK_PAGE = "https://citymapper.com/go/"  # provenance: ignore, public page address shown to you, never requested


def share_journey(context, arguments):
   region = context.region(arguments.get("city"))
   request = Request(endpoints.CREATE_TRIP_URL, query={"signature": arguments.get("signature"), "trip_region_id": region["region_id"]})
   result = perform_write_public(context, arguments, request)
   return result if arguments.get("dry_run") else {"url": (result or {}).get("url", "")}


def dropped_text_warning(sent_fields, reply, slug):
   dropped = []

   for field_name, sent_text in sent_fields.items():
      was_echoed = bool(reply.get(field_name))
      is_dropped = bool(sent_text) and not was_echoed

      if is_dropped:
         dropped.append(field_name)

   if not dropped:
      return None

   return "Citymapper did not echo the {0} back, so the link may not show it. Run open-go-link --slug {1} to check.".format(" and ".join(dropped), slug or "<slug>")


def create_go_link(context, arguments):
   region = context.region(arguments.get("city"))
   place = context.place(region, arguments.get("place"), "place")
   sent_fields = {"title": arguments.get("title") or "", "message": arguments.get("message") or ""}
   query = {"endcoord": "{0},{1}".format(*place.coords), "endaddress": place.address or "", "endname": place.name, **sent_fields, "place_id": ""}
   result = perform_write_public(context, arguments, Request(endpoints.CREATE_SHORT_URL, query=query))

   if arguments.get("dry_run"):
      return result

   reply = result if isinstance(result, dict) else {}
   slug = reply.get("slug", "")
   return {
      "url": reply.get("url") or (GO_LINK_PAGE + slug if slug else ""),
      "slug": slug,
      "title": reply.get("title"),
      "message": reply.get("message"),
      "warning": dropped_text_warning(sent_fields, reply, slug),
   }


def vote_for_city(context, arguments):
   body = {"city_slug": arguments.get("city_slug"), "email": arguments.get("email")}
   result = perform_write(context, arguments, Request(endpoints.CITY_VOTE, json_body=body))
   return result if arguments.get("dry_run") else {"ok": True}


def perform_write_public(context, arguments, request):
   return perform_write(context, arguments, request, needs_session=False)
