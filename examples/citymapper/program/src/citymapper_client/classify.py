import json

from .errors import ApiError, ChallengeRequired, ContractBroken, NotFound, RateLimited, SessionExpired

CHALLENGE_MARKERS = ("cf-chl", "challenge-platform", "<title>Just a moment", "cf_chl_opt", "Attention Required! | Cloudflare")
BOT_CHECK_MARKERS = ("_abck", "px-captcha", "datadome", "captcha")


def looks_like_challenge(text):
   head = text[:20000]
   return any(marker in head for marker in CHALLENGE_MARKERS)


def looks_like_bot_check(text):
   head = text[:20000].lower()
   return any(marker in head for marker in BOT_CHECK_MARKERS)


def classify(status, content_type, text, expect, signed_in_endpoint=False):
   """Return the parsed body, or raise the class of failure the response shows.

   expect is "json" or "html". The body is read before the status, because a 200 can carry an
   error envelope and a 403 can carry a challenge page.
   """
   content_type = content_type or ""
   is_json = "json" in content_type

   if status == 429:
      raise RateLimited("Citymapper answered 429 Too Many Requests.", {"status": status})

   if looks_like_challenge(text):
      raise ChallengeRequired("Citymapper served a bot check page. Open citymapper.com in your browser; do not retry.", {"status": status})

   is_signed_out = signed_in_endpoint and status in (401, 403)
   if is_signed_out:
      raise SessionExpired("Not signed in to Citymapper (HTTP {0}). Sign in on citymapper.com in your browser, then run adopt-session.".format(status), {"status": status})

   if status == 404:
      raise NotFound("Citymapper has no such item (HTTP 404).", {"status": status})

   if status >= 400:
      raise ApiError("Citymapper answered HTTP {0}.".format(status), {"status": status, "body_head": text[:200] if is_json else ""})

   if expect == "html":
      return text

   is_html_body = "html" in content_type or text.lstrip().startswith("<")
   got_html_instead_of_json = not is_json and is_html_body

   if got_html_instead_of_json:
      if signed_in_endpoint:
         raise SessionExpired("Citymapper sent a web page instead of data. Sign in on citymapper.com in your browser, then run adopt-session.", {"status": status})

      if looks_like_bot_check(text):
         raise ChallengeRequired("Citymapper served a bot check page. Open citymapper.com in your browser; do not retry.", {"status": status})

   if not is_json:
      raise ContractBroken("Expected JSON from Citymapper, got {0}.".format(content_type or "no content type"), {"status": status})

   try:
      body = json.loads(text)
   except ValueError as error:
      raise ContractBroken("Citymapper sent unparseable JSON.", {"error": str(error)}) from error

   # The site's own client rejects any body whose top-level error is truthy, whatever else it holds.
   is_object = isinstance(body, dict)
   has_error_envelope = is_object and bool(body.get("error"))
   if has_error_envelope:
      raise ApiError("Citymapper returned an error: {0}".format(body.get("error")), {"error": body.get("error")})

   return body
