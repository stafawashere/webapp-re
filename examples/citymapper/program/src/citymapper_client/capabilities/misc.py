import html
import re

from .. import endpoints
from ..errors import NotFound, UsageError
from ..models import coords_of, require_list

RETIRED_WEATHER = "Citymapper's /api/1/weather answers 404 with its 'Page Not Found' HTML in New York and London (replay 2026-10-10)."
RETIRED_TRANSIT_SCORE = "Citymapper's /api/1/transitscore answers 404 with its 'Page Not Found' HTML in New York and London (replay 2026-10-10)."
LEGAL_DOCUMENTS = {"terms": "citymapper-terms-of-service", "privacy": "citymapper-privacy-policy"}
TAG = re.compile(r"<[^>]+>")
SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)


def get_map_around(context, arguments):
   region = context.region(arguments.get("city"))
   near = context.place(region, arguments.get("near"), "near")
   size = arguments.get("size")

   if not size:
      raise UsageError("Pass --size (the tile size name the API accepts).")

   response = context.send(endpoints.EVERYTHING_MAP, query={"location": "{0},{1}".format(*near.coords), "size": size, "region_id": region["region_id"]})
   elements = response.get("elements") if isinstance(response, dict) and isinstance(response.get("elements"), list) else [response]
   return {"elements": elements}


def get_weather(context, arguments):
   raise NotFound(RETIRED_WEATHER, {"blocked": "retired upstream"})


def get_transit_score(context, arguments):
   raise NotFound(RETIRED_TRANSIT_SCORE, {"blocked": "retired upstream"})


def open_go_link(context, arguments):
   slug = arguments.get("slug")

   if not slug:
      raise UsageError("Pass --slug (the part after citymapper.com/go/).")

   response = context.send(endpoints.GET_SHORT_URL, query={"slug": slug})
   destination = response if isinstance(response, dict) else {}
   return {"name": destination.get("endname") or destination.get("name"), "coords": coords_of(destination.get("endcoord") or destination.get("coords")), "address": destination.get("endaddress") or destination.get("address"), "raw": destination}


def list_news(context, arguments):
   query = {"id": arguments["id"]} if arguments.get("id") else None
   response = context.send(endpoints.BLOG, query=query)
   posts = []

   for post in require_list(response, "posts", "news posts"):
      url = post.get("url") or ""
      identifier = re.search(r"/i/(\d+)", url)
      posts.append({"id": identifier.group(1) if identifier else "", "title": post.get("title", ""), "url": url, "summary": post.get("summary"), "date": post.get("post_date")})

   limit = arguments.get("limit")
   return {"posts": posts[:limit] if limit else posts}


def page_text(page):
   without_code = SCRIPT_OR_STYLE.sub(" ", page)
   text = html.unescape(TAG.sub(" ", without_code))
   return re.sub(r"\s+", " ", text).strip()


def get_legal(context, arguments):
   document = arguments.get("document")

   if document not in LEGAL_DOCUMENTS:
      raise UsageError("Pass --document terms or --document privacy.")

   page = context.send(endpoints.RESOURCES, query={"id": LEGAL_DOCUMENTS[document]})
   title = TITLE.search(page)
   return {"title": html.unescape(title.group(1)).strip() if title else document, "text": page_text(page), "url": endpoints.RESOURCES.url() + "?id=" + LEGAL_DOCUMENTS[document]}
