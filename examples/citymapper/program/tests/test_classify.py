import pytest

from citymapper_client.classify import classify
from citymapper_client.errors import ApiError, ChallengeRequired, ContractBroken, NotFound, RateLimited, SessionExpired

JSON_TYPE = "application/json; charset=utf8"
HTML_TYPE = "text/html; charset=utf-8"
CLOUDFLARE_MARKERS = ["cf-chl", "challenge-platform", "<title>Just a moment...</title>", "cf_chl_opt", "<title>Attention Required! | Cloudflare</title>"]


def test_429_is_rate_limited():
   with pytest.raises(RateLimited):
      classify(429, JSON_TYPE, "{}", "json")


@pytest.mark.parametrize("marker", CLOUDFLARE_MARKERS)
@pytest.mark.parametrize("status", [200, 403, 503])
def test_cloudflare_markers_require_a_challenge(marker, status):
   page = "<html><head></head><body>{0}</body></html>".format(marker)

   with pytest.raises(ChallengeRequired):
      classify(status, HTML_TYPE, page, "json", signed_in_endpoint=True)


@pytest.mark.parametrize("status", [401, 403])
def test_refusal_on_a_signed_in_endpoint_is_session_expired(status):
   with pytest.raises(SessionExpired):
      classify(status, JSON_TYPE, "", "json", signed_in_endpoint=True)


def test_403_on_a_public_endpoint_is_an_api_error():
   with pytest.raises(ApiError) as caught:
      classify(403, JSON_TYPE, "{}", "json", signed_in_endpoint=False)

   assert not isinstance(caught.value, SessionExpired)


def test_404_is_not_found():
   with pytest.raises(NotFound):
      classify(404, HTML_TYPE, "<html><title>Page Not Found</title></html>", "json")


def test_500_is_an_api_error_with_status():
   with pytest.raises(ApiError) as caught:
      classify(500, JSON_TYPE, "{\"error\": \"boom\"}", "json")

   assert caught.value.detail["status"] == 500


def test_html_where_json_was_expected_is_contract_broken():
   with pytest.raises(ContractBroken):
      classify(200, HTML_TYPE, "<html><body>hello</body></html>", "json")


def test_unparseable_json_is_contract_broken():
   with pytest.raises(ContractBroken):
      classify(200, JSON_TYPE, "{not json", "json")


def test_error_envelope_in_a_200_is_an_api_error():
   with pytest.raises(ApiError) as caught:
      classify(200, JSON_TYPE, "{\"error\": \"x\"}", "json")

   assert caught.value.detail["error"] == "x"


@pytest.mark.parametrize("envelope", [
   "{\"error\": \"Invalid region\", \"code\": 400, \"message\": \"x\", \"details\": {}}",
   "{\"error\": true, \"message\": \"bad\"}",
])
def test_wider_error_envelopes_in_a_200_are_api_errors(envelope):
   with pytest.raises(ApiError):
      classify(200, JSON_TYPE, envelope, "json")


def test_falsy_top_level_error_is_still_data():
   body = classify(200, JSON_TYPE, "{\"error\": null, \"results\": []}", "json")

   assert body == {"error": None, "results": []}


def test_valid_json_is_returned_parsed():
   body = classify(200, JSON_TYPE, "{\"travel_time_minutes\": 19}", "json")

   assert body == {"travel_time_minutes": 19}


def test_html_endpoint_returns_the_page_text():
   page = "<html><body>cities</body></html>"

   assert classify(200, HTML_TYPE, page, "html") == page
