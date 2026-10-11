"""Scope facts for citymapper, from the 2026-10-10 walk (run-2026-10-10-082844).

Sources: CDP captures in var/captures/run-2026-10-10-082844-*.jsonl, the Claude in Chrome walk
(request URLs and DOM), and research/bundle/api-inventory.json (bundle reading, no requests).
"""

SITE = {
   "slug": "citymapper",
   "name": "Citymapper",
   "origins": ["https://citymapper.com", "https://global-api.citymapper.com", "https://turnstile-api.citymapper.com"],
   "framework": "react (react-router SPA bundle /static/components/bundle-<hash>.js inside server-rendered Django pages; landing page is a separate React bundle; some routes are Next.js SSR)",
   "bundler": "webpack (module ids, __REACT_HOT_LOADER__ source paths /__w/web/web/src/...)",
   "source_maps": False,
}

SUMMARY = (
   "Citymapper's website is a public transit journey planner for 115 regions (252 cities) worldwide. "
   "Everything a visitor can do without an account goes through unsigned same-origin JSON calls under https://citymapper.com/api/<version>/: "
   "journey planning (transit, walk, cycle, cab and on-demand) between coordinates with depart-at or arrive-by times, live journey times, "
   "place search and autocomplete, nearby stops, stations, piers and bike docks per mode, stop details with live departures (bus, metro and rail feeds), "
   "line pages with stops, patterns and service status, region-wide line status with disruption texts, and line search. "
   "The city is always an explicit region_id parameter; the list of regions and cities, each region's modes, brands, bounding box and timezone are inlined into every server-rendered page as window.citymapper. "
   "A web account exists (sign in by e-mail magic link, Google or Facebook) and adds saved places (home, work, others), favourite stops and lines, and 'send to phone' saved journeys, all under /api/1/identity/. "
   "You are signed out on citymapper.com, so the account surface was mapped from the bundle and was not exercised; Citymapper Club and Pass payments are app-only. "
   "No request signing, nonce, captcha or bot challenge appeared; the site sits behind Cloudflare (__cf_bm) and served 200 to a separate CDP browser and to curl."
)

PAGES = [
   {"id": "page-home", "url_pattern": "/", "purpose": "Landing page: Get Me Somewhere form, city switcher, news teasers; fetches the current region's info and the brand directory", "requires_auth": False, "visited": True, "capabilities": ["cap-city-info", "cap-brand-directory", "cap-plan-journey"], "endpoints": ["resource-region-info", "resource-brand-directory", "identity-user-data", "message"]},
   {"id": "page-webapp", "url_pattern": "/webapp, /{region_slug}/webapp", "purpose": "Journey planner shell: start and end search boxes, Now, Arrive, Leave time selector, map", "requires_auth": False, "visited": True, "capabilities": ["cap-search-places", "cap-plan-journey", "cap-reverse-geocode"], "endpoints": ["searchpost", "geocode", "identity-user-data", "message"]},
   {"id": "page-directions", "url_pattern": "/directions?startcoord={lat,lng}&endcoord={lat,lng}&startname=&endname=&startaddress=&endaddress=&departure_time={iso}|arrival_time={iso}", "purpose": "Journey results: walk, cycle and cab summary row, Suggested and other sections of transit journeys with price, duration and live next departures", "requires_auth": False, "visited": True, "capabilities": ["cap-plan-journey", "cap-plan-walk", "cap-plan-cycle", "cap-plan-cab", "cap-journey-times"], "endpoints": ["journeys", "walk7", "cycle", "taxi", "journeytimes", "searchpost"]},
   {"id": "page-trip-signature", "url_pattern": "/trip/signature?signature={deflated base64 journey signature}", "purpose": "Journey detail: legs, stops, exits, live times; share and send-to-phone buttons", "requires_auth": False, "visited": True, "capabilities": ["cap-journey-detail", "cap-journey-times", "cap-share-trip", "cap-save-journey"], "endpoints": ["trip-meta", "journeytimes", "refreshjourneys", "createtripurl", "identity-save-journey"]},
   {"id": "page-trip-slug", "url_pattern": "/trip/{slug}", "purpose": "Shared trip link: resolves a slug to a journey signature, then shows the journey detail", "requires_auth": False, "visited": False, "capabilities": ["cap-open-shared-trip"], "endpoints": ["gettrip", "refreshjourneys"]},
   {"id": "page-go", "url_pattern": "/go/{slug}, /widget/{slug}", "purpose": "Meet Me Somewhere link: destination card that plans a journey to a saved place", "requires_auth": False, "visited": False, "capabilities": ["cap-open-go-link"], "endpoints": ["getshorturl"]},
   {"id": "page-meet", "url_pattern": "/meet", "purpose": "Meet Me Somewhere marketing page and place box that creates a go link", "requires_auth": False, "visited": True, "capabilities": ["cap-create-go-link"], "endpoints": ["createshorturl"]},
   {"id": "page-city", "url_pattern": "/{region_slug}", "purpose": "City home: journey form, account box, nearby mode tiles, lines card with status, Meet Me Somewhere box, strike map", "requires_auth": False, "visited": True, "capabilities": ["cap-city-info", "cap-line-status", "cap-lines-info", "cap-find-line", "cap-message"], "endpoints": ["city-html", "routestatus", "routeinfo2", "findtransport", "message", "identity-user-data"]},
   {"id": "page-status", "url_pattern": "/{region_slug}/status", "purpose": "All lines status for the region grouped by mode, with disruption details and partner status", "requires_auth": False, "visited": True, "capabilities": ["cap-line-status", "cap-disruptions"], "endpoints": ["routestatus", "routeinfo2"]},
   {"id": "page-nearby", "url_pattern": "/{region_slug}/{mode_slug}/{stop_type}?name=&coords={lat,lng}", "purpose": "Nearby list and map for one mode (stations, stops, docks, piers) around a point", "requires_auth": False, "visited": True, "capabilities": ["cap-nearby"], "endpoints": ["nearby3", "routeinfo2"]},
   {"id": "page-stop", "url_pattern": "/{region_slug}/{mode_slug}/{stop_type}/{alias}", "purpose": "Stop or station: routes, exits, live departures by platform or direction, nearby stops; favourite star", "requires_auth": False, "visited": True, "capabilities": ["cap-stop-info", "cap-live-departures", "cap-favourite-stop"], "endpoints": ["stopinfo", "departures-bus", "departures-metro", "departures-rail", "nearby2"]},
   {"id": "page-line", "url_pattern": "/{region_slug}/{mode_slug}/{line_alias} (also /{region_slug}/l/{line_alias}, which redirects)", "purpose": "Line: branches (patterns), ordered stops, map path, status; favourite star and share", "requires_auth": False, "visited": True, "capabilities": ["cap-line-info", "cap-vehicle-locations", "cap-favourite-line"], "endpoints": ["routeinfo1", "vehiclelocations"]},
   {"id": "page-planner", "url_pattern": "/{region_slug}/planner/{brand}", "purpose": "Brand-only journey planner for a partner network (journeys sent with partner=)", "requires_auth": False, "visited": False, "capabilities": ["cap-plan-journey"], "endpoints": ["routestatus", "routeinfo1", "nearby3", "journeys"]},
   {"id": "page-cities", "url_pattern": "/cities", "purpose": "All cities; picking one writes the cm_region cookie and reloads", "requires_auth": False, "visited": True, "capabilities": ["cap-list-cities", "cap-switch-city"], "endpoints": ["cities-html"]},
   {"id": "page-news", "url_pattern": "/news, /news/{id}/{slug}, /i/{id}/{slug}", "purpose": "Company news posts (server rendered)", "requires_auth": False, "visited": True, "capabilities": ["cap-news"], "endpoints": ["news-html", "blog"]},
   {"id": "page-login-dialog", "url_pattern": "/{region_slug}#login (modal)", "purpose": "Sign up or log in: e-mail magic link, Facebook, Google", "requires_auth": False, "visited": True, "capabilities": ["cap-sign-in"], "endpoints": ["identity-magiclink", "identity-sessions-create"]},
   {"id": "page-legal", "url_pattern": "/api/1/resources?id=citymapper-terms-of-service|citymapper-privacy-policy", "purpose": "Terms of service and privacy policy documents", "requires_auth": False, "visited": False, "capabilities": ["cap-legal"], "endpoints": ["resources"]},
   {"id": "page-server-only", "url_pattern": "/eta/{slug}, /pass, /pass/{slug}, /ride, /authorise/{reference}, /signup/{token}/confirm, /reset/{token}/continue, /p/reset_password, /account-deletion/{token}", "purpose": "Server-rendered pages for shared ETAs, Citymapper Pass, payments authorisation and account e-mail flows; no caller in the web bundles", "requires_auth": False, "visited": False, "capabilities": ["cap-shared-eta", "cap-pass-payments", "cap-password-reset"], "endpoints": ["eta", "turnstile-userinfo", "identity-password-reset"]},
]


def capability(identifier, name, action, endpoints, mutates=False, exercised=True, others=False, entities=None, notes=""):
   return {
      "id": identifier,
      "name": name,
      "user_action": action,
      "mutates": mutates,
      "visible_to_others": others,
      "exercised": exercised,
      "endpoints": endpoints,
      "entities": entities or [],
      "notes": notes,
   }


CAPABILITIES = [
   capability("cap-plan-journey", "Plan a transit journey", "Type a start and an end (or click the map), pick Now, Arrive or Leave, press GO", ["journeys", "searchpost"], entities=["journey", "leg", "place"], notes="Inputs: start and end coordinates (names and addresses optional), region_id, departure_time or arrival_time as ISO UTC, step-free and microtransit flags. Returns sections (Suggested, others) and journeys with legs, live departure hints, price and duration. Exercised in NYC (now and arrive-by) and London (now), Paris (depart-at)."),
   capability("cap-plan-walk", "Plan a walking route", "Same form; the walk tile in the summary row", ["walk7", "walk1"], entities=["journey"], notes="limit=2 profiles (fast, and a second)."),
   capability("cap-plan-cycle", "Plan a cycling route (own bike or bike share)", "Same form; the cycle tile", ["cycle"], entities=["journey"], notes="Profiles quiet, regular, fast; bike share journeys carry price and brand (CitiBike, Santander, Velib); shared.cycle_docks."),
   capability("cap-plan-cab", "Estimate a cab or on-demand ride", "Same form; the cab tile", ["taxi"], entities=["journey"], notes="routes[] with duration and length, on_demand_model.categories (Uber, Lyft and local services) where the region has them."),
   capability("cap-plan-vehicle-hire", "Plan with scooters or hire vehicles", "No web UI caller; bundle method getVehicleHireJourneys", ["vehiclehire"], exercised=False, entities=["journey"], notes="Defined in the bundle; observed false."),
   capability("cap-journey-times", "Refresh live times of planned journeys", "Automatic every 30 s on results and detail pages", ["journeytimes"], entities=["journey-time"], notes="POST body signatures[] (journey signature JSON strings). Up to 10 polls in the UI."),
   capability("cap-journey-detail", "Open a journey's detail", "Click a journey in the results", ["refreshjourneys", "trip-meta", "journeytimes"], entities=["journey", "leg"], notes="Navigates to /trip/signature?signature=<deflated base64>; a direct load calls POST /api/1/refreshjourneys (exercised only as an in-app navigation, which reused the stored journey)."),
   capability("cap-open-shared-trip", "Open a shared trip link", "Open /trip/{slug}", ["gettrip", "refreshjourneys"], exercised=False, entities=["journey"]),
   capability("cap-share-trip", "Create a share link for a journey", "Journey detail, share icon", ["createtripurl"], mutates=True, exercised=False, others=True, entities=["journey"], notes="Creates a public short URL. Not pressed."),
   capability("cap-save-journey", "Send a journey to your phone (save it to the account)", "Journey detail, send-to-phone icon (needs sign-in)", ["identity-save-journey", "identity-delete-journey"], mutates=True, exercised=False, entities=["saved-journey"], notes="POST /api/1/identity/documents/SavedJourney {document_data}; delete by document_id. No list endpoint on the web."),
   capability("cap-search-places", "Search places, addresses, stations and stops", "Type in the Start or End box", ["searchpost"], entities=["place"], notes="POST form body: query, region_id, location (optional bias), is_refinement, refinement_data, powersearch. Results mix Citymapper stations and Google places with coords."),
   capability("cap-resolve-place", "Resolve a place result without coordinates", "Pick a search result whose coords are missing", ["placeresolve"], exercised=False, entities=["place"], notes="Google results observed carry coords, so no call was made."),
   capability("cap-reverse-geocode", "Name a point clicked on the map", "Click the map to set Start or End", ["geocode"], exercised=False, entities=["place"], notes="GET /geocode?lat=&lng= (same origin, outside /api). The map click observed hit a Google POI, which carries its own name."),
   capability("cap-nearby", "List nearby stops, stations, piers or bike docks for one mode", "City page Nearby tile, or /{city}/{mode}/{stop_type}?coords=", ["nearby3", "nearby2"], entities=["nearby-element"], notes="Per mode: brand_ids or kinds, mode_id, location, limit 50, extended=1. Bike docks carry cycles_available, spaces, electric and manual counts."),
   capability("cap-stop-info", "Get a stop or station's details", "Open a stop page", ["stopinfo"], entities=["stop", "route"], notes="ids accepts the alias or the id. Returns routes, exits, sharing_urls with the departure API to use."),
   capability("cap-live-departures", "Get live departures at a stop or station", "Open a stop page; refreshes every 30 s", ["departures-bus", "departures-metro", "departures-rail"], entities=["departure"], notes="The brand's departure_apis picks the endpoint: departures (bus, ferry), metrodepartures (subway, metro, tube), raildepartures (commuter rail). Live seconds mixed with scheduled ISO times."),
   capability("cap-stop-schedule", "Get a stop's timetable", "No web UI caller; bundle getSchedules", ["schedules"], exercised=False, entities=["departure"]),
   capability("cap-line-info", "Get a line's branches, stops, path and status", "Open a line page", ["routeinfo1"], entities=["route", "pattern", "stop"], notes="route=<alias>, extended=1 adds patterns with stop_points and paths."),
   capability("cap-lines-info", "Get several lines at once", "City page lines card and strike map", ["routeinfo2"], entities=["route"], notes="route_ids=comma list; weekend=1; status_format=rich."),
   capability("cap-line-status", "Get the status of every line in a city", "City page lines card, /{city}/status", ["routestatus"], entities=["route-status"], notes="groupings by mode with routes[].status level, summary, description and disruptions; partners (scooters, bikes, cabs)."),
   capability("cap-disruptions", "Read disruption details for a line or region", "Status page, expand a line", ["routestatus", "routeinfo2"], entities=["disruption"], notes="status.disruptions[] with level, summary, description template, replacements and affected stops."),
   capability("cap-find-line", "Find a bus or line by name or number", "City page Lines card, type in Find a bus or line", ["findtransport"], entities=["route"], notes="GET /api/2/findtransport?query=&region_id= as you type."),
   capability("cap-vehicle-locations", "Get live vehicle positions on a line", "Line page with live_line_code; 10 s timer", ["vehiclelocations"], exercised=False, entities=["vehicle"], notes="Not fired on the NYC 6, M15 or London Bakerloo pages (live_availability 0)."),
   capability("cap-route-paths", "Get line paths for a map", "No web UI caller; bundle getRoutePaths", ["routepaths"], exercised=False, entities=["route"]),
   capability("cap-everything-map", "Get everything on the map around a point", "No web UI caller; bundle getEverything", ["everythingmap"], exercised=False, entities=["nearby-element"]),
   capability("cap-list-cities", "List every supported city and region", "Open /cities or the Switch City menu", ["cities-html", "city-html"], entities=["region", "city"], notes="115 regions and 252 cities inlined in page HTML; 8 regions have api_enabled false."),
   capability("cap-city-info", "Get one city's configuration (modes, brands, bounding box, timezone)", "Open a city page or the home page", ["city-html", "resource-region-info"], entities=["region", "brand"]),
   capability("cap-switch-city", "Switch the current city", "Switch City, pick a city", ["cities-html"], exercised=False, entities=["region"], notes="Client side: sets the cm_region cookie and reloads; the program passes region_id explicitly instead."),
   capability("cap-brand-directory", "List transport brands (operators) worldwide", "Home page loads it", ["resource-brand-directory"], entities=["brand"]),
   capability("cap-message", "Read the site-wide service message", "Every page load", ["message"], entities=["message"], notes="messages[] is usually empty."),
   capability("cap-weather", "Get the weather at a point", "No web UI caller; bundle getWeather", ["weather"], exercised=False),
   capability("cap-transit-score", "Get a transit score for a point", "No web UI caller; bundle getTransitScore", ["transitscore"], exercised=False),
   capability("cap-travel-time", "Get the travel time between two points", "No web UI caller; place.js makeTravelTimeRequest", ["traveltime"], exercised=False),
   capability("cap-shared-eta", "Read a shared ETA", "Open /eta/{slug} (server rendered); bundle getETA", ["eta"], exercised=False),
   capability("cap-open-go-link", "Open a Meet Me Somewhere link", "Open /go/{slug}", ["getshorturl"], exercised=False, entities=["go-link"]),
   capability("cap-create-go-link", "Create a Meet Me Somewhere link", "City page or /meet: type a place and press the arrow", ["createshorturl"], mutates=True, exercised=False, others=True, entities=["go-link"], notes="Creates a public short URL with a title and message. Not pressed."),
   capability("cap-news", "Read Citymapper news posts", "Footer News, or /news", ["news-html", "blog"], entities=["news-post"]),
   capability("cap-legal", "Read the terms of service or privacy policy", "Footer Terms or Privacy", ["resources"], exercised=False),
   capability("cap-sign-in", "Sign up or log in", "Account box, Sign up or log in: e-mail, Facebook or Google", ["identity-magiclink", "identity-sessions-create"], mutates=True, exercised=False, entities=["user"], notes="Dialog opened, nothing submitted. Signing in can create an account, so the program will not automate it; you sign in yourself."),
   capability("cap-sign-out", "Log out", "Account menu, log out", ["identity-sessions-delete"], mutates=True, exercised=False, entities=["user"]),
   capability("cap-user-data", "Read the signed-in user", "Every page load", ["identity-user-data"], entities=["user"], notes="403 while signed out (observed)."),
   capability("cap-update-user", "Update your name, mobile or Pass interest", "No web UI caller; bundle updateUser", ["identity-update-user"], mutates=True, exercised=False, entities=["user"]),
   capability("cap-saved-places", "List your saved places (home, work, others)", "Search box Saved Places section (signed in)", ["identity-places-list"], exercised=False, entities=["saved-place"]),
   capability("cap-save-place", "Save a place", "Star a place (signed in)", ["identity-places-create"], mutates=True, exercised=False, entities=["saved-place"]),
   capability("cap-update-place", "Edit a saved place", "No web UI caller; bundle updateUserPlace", ["identity-places-update"], mutates=True, exercised=False, entities=["saved-place"]),
   capability("cap-remove-place", "Remove a saved place", "Unstar a saved place (signed in)", ["identity-places-delete"], mutates=True, exercised=False, entities=["saved-place"], notes="The web client passes placeId where place_id is required, so the web UI throws before sending (bundle reading)."),
   capability("cap-favourites", "List your favourite stops, stations and lines", "Lines card and stop pages (signed in)", ["identity-favorites-list"], exercised=False, entities=["favourite"]),
   capability("cap-favourite-stop", "Favourite or unfavourite a stop or station", "Star on a stop page (signed in)", ["identity-favorites-create", "identity-favorites-delete"], mutates=True, exercised=False, entities=["favourite"]),
   capability("cap-favourite-line", "Favourite or unfavourite a line", "Star on a line page (signed in)", ["identity-favorites-create", "identity-favorites-delete"], mutates=True, exercised=False, entities=["favourite"]),
   capability("cap-password-reset", "Reset a password or confirm an e-mail", "Server pages /p/reset_password, /signup/{token}/confirm; no web UI caller", ["identity-password-reset", "identity-confirm-signup"], mutates=True, exercised=False, entities=["user"]),
   capability("cap-pass-payments", "Manage Citymapper Pass payment methods", "Server pages /pass and /authorise; no web UI caller", ["turnstile-userinfo", "turnstile-addpaymentmethod", "turnstile-setdefaultpaymentmethod", "turnstile-deletepaymentmethod", "turnstile-deleteallpaymentmethods", "turnstile-sessionttl"], mutates=True, exercised=False, entities=["payment-method"], notes="Paid product on turnstile-api.citymapper.com; needs a Session-Id and User-Device. Out of reach without the app and an account."),
   capability("cap-city-vote", "Vote for a new city", "No web UI caller; POST /cities/vote_submit/ with X-CSRFToken", ["city-vote"], mutates=True, exercised=False, others=False),
   capability("cap-telemetry", "Analytics events", "Every page", ["logevents"], mutates=True, notes="Noise, never called by the program."),
]


def endpoint(identifier, method, url, observed, query=None, body=None, headers=None, surface="rest", shape=None, pagination="", notes="", noise=False, operation=""):
   item = {
      "id": identifier,
      "method": method,
      "url_pattern": url,
      "surface": surface,
      "observed": observed,
      "query_keys": query or [],
      "request_header_names": headers or ["accept", "content-type", "referer"],
      "body_fields": body or [],
      "response_shape": shape or {},
      "pagination": pagination,
      "notes": notes,
   }

   if operation:
      item["operation"] = operation

   if noise:
      item["noise"] = True

   return item


JOURNEY_QUERY = ["start", "end", "saddr", "eaddr", "sname", "ename", "region_id", "departure_time", "arrival_time", "include_stepfree", "include_networks", "include_floating", "include_via_microtransit", "limit", "context", "partner", "cycle", "status_format"]
JOURNEY_SHAPE = {"sections[]": "id, name, journeys[] (indexes), ad_may_follow", "journeys[]": "start, end, legs[], duration_seconds, walk_seconds, distance_meters, calories, signature, journey_equivalence_hash, formatted_price, price_amount, currency_code, step_free, trip_curation_url_ids, log", "journeys[].legs[]": "mode (walk, transit, cycle, ...), routes[], stops[] (id, name, coords, duration_seconds_to_here), shape[[lat,lng]], frequency, departure_time, arrival_time, pattern_ids, boarding_info", "shared": "station_exits[], trip_curation_urls[]", "routing_request_id": "str"}

ENDPOINTS = [
   endpoint("journeys", "GET", "https://citymapper.com/api/7/journeys", True, JOURNEY_QUERY, shape=JOURNEY_SHAPE, pagination="time-window-journeys", notes="Transit journeys. start and end are 'lat,lng'. Observed keys: start, end, sname, ename, saddr, region_id, include_stepfree=1, include_via_microtransit=1, status_format=html, arrival_time or departure_time ISO UTC. 97 KB for NYC, 166 KB for London."),
   endpoint("walk7", "GET", "https://citymapper.com/api/7/walk", True, JOURNEY_QUERY, shape={"journeys[]": "duration_seconds, distance_meters, calories, legs[], signature, profile_id, profile_localized_name", "shared.station_exits[]": "..."}, pagination="time-window-journeys", notes="limit=2 in the UI."),
   endpoint("walk1", "GET", "https://citymapper.com/api/1/walk", False, JOURNEY_QUERY, notes="Older walk endpoint; bundle only."),
   endpoint("cycle", "GET", "https://citymapper.com/api/6/cycle", True, JOURNEY_QUERY, shape={"journeys[]": "journey_kind (cycle_personal, cycle_hire), profile_id, journey_profile, duration_seconds, distance_meters, legs[], signature, formatted_price, representative_brand_id", "shared.cycle_docks[]": "dock ids and availability"}, pagination="time-window-journeys"),
   endpoint("taxi", "GET", "https://citymapper.com/api/2/taxi", True, JOURNEY_QUERY, shape={"routes[]": "mode taxi, length_meters, duration_seconds, legs[]", "on_demand_model": "title, categories[]", "status": "int"}),
   endpoint("vehiclehire", "GET", "https://citymapper.com/api/7/vehiclehire", False, JOURNEY_QUERY, notes="Bundle only, no caller."),
   endpoint("journeytimes", "POST", "https://citymapper.com/api/1/journeytimes?region_id={region_id}", True, ["region_id"], ["signatures", "partner"], ["accept", "content-type", "origin", "referer"], shape={"journey_times[]": "time (ISO with offset), time_mode (NOWISH, ...), formatted_price, leg_times[], request_signature, traffic_level"}, pagination="poll-30s", notes="Body {signatures: [<journey signature JSON string>]}; response order follows the request."),
   endpoint("refreshjourneys", "POST", "https://citymapper.com/api/1/refreshjourneys?region_id={region_id}", False, ["region_id"], ["signatures", "time_mode", "region_id", "partner", "use_departures", "status_format"], shape={"refreshed_journeys[]": "journey, error", "shared": "..."}, notes="time_mode SIGNATURE_EXACT or SIGNATURE; bundle and route table, not fired by in-app navigation."),
   endpoint("trip-meta", "GET", "https://citymapper.com/trip/signature?signature={deflated base64}&meta_only=true", True, ["signature", "meta_only"], surface="html", notes="Head-tag refresh on client navigation (hackyReplacePageMeta). The signature param is the journey signature, pako-deflated and base64 encoded."),
   endpoint("gettrip", "GET", "https://citymapper.com/api/1/gettrip?slug={slug}", False, ["slug"], shape={"signature": "str"}),
   endpoint("createtripurl", "GET", "https://citymapper.com/api/1/createtripurl?signature={signature}&trip_region_id={region_id}", False, ["signature", "trip_region_id"], shape={"url": "str"}, notes="Write despite GET: creates a public short link."),
   endpoint("createshorturl", "GET", "https://citymapper.com/api/1/createshorturl?endcoord=&endaddress=&endname=&title=&message=&place_id=", False, ["endcoord", "endaddress", "endname", "title", "message", "place_id"], shape={"url": "str"}, notes="Write despite GET: creates a public Meet Me Somewhere link."),
   endpoint("getshorturl", "GET", "https://citymapper.com/api/1/getshorturl?slug={slug}", False, ["slug"]),
   endpoint("eta", "POST", "https://citymapper.com/api/1/eta?region_id={region_id}", False, ["region_id"], ["signature"]),
   endpoint("searchpost", "POST", "https://citymapper.com/api/4/searchpost", True, [], ["query", "region_id", "location", "is_refinement", "refinement_data", "search_providers", "powersearch", "partner"], ["accept", "citymapper-client", "citymapper-region", "content-type", "origin", "referer"], shape={"results[]": "id, name, result_type (heading or item), type (station, place, ...), coords, address, brands, lines, route_icon_names, source, place_details_available, search_providers", "included_search_providers[]": "id, name", "query": "str"}, notes="Content-Type application/x-www-form-urlencoded with a JSON body; Citymapper-Client: Web Search; Citymapper-Region: <region_id>."),
   endpoint("placeresolve", "GET", "https://citymapper.com/api/1/placeresolve?id={id}&region_id={region_id}", False, ["id", "region_id"]),
   endpoint("geocode", "GET", "https://citymapper.com/geocode?lat={lat}&lng={lng}", False, ["lat", "lng"], shape={"results[]": "address_components[], formatted_address (Google geocoder shape)"}),
   endpoint("nearby3", "GET", "https://citymapper.com/api/3/nearby", True, ["brand_ids", "kinds", "mode_id", "location", "viewspan", "region_id", "limit", "extended"], shape={"elements[]": "id, name, coords, kind (transitstop, cycledock, ...), brand_ids, route_ids, route_names, route_icon_names, alias, bearing, walk_time_seconds; docks add cycles_available, cycles_spaces, cycles_total, cycles_electric_available, cycles_manual_available", "bounding_box": "southwest_corner_coords, northeast_corner_coords", "last_updated_time": "str"}, pagination="limit-50", notes="brand_ids and mode_id come from the region's nearby_modes."),
   endpoint("nearby2", "GET", "https://citymapper.com/api/2/nearby", True, ["brand_ids", "kinds", "location", "viewspan", "limit", "region_id"], ["accept", "referer", "x-requested-with"], shape={"elements[]": "same element shape as nearby3", "bounding_box": "..."}, pagination="limit-50", notes="jQuery call on stop pages."),
   endpoint("everythingmap", "GET", "https://citymapper.com/api/1/everythingmap?location={lat,lng}&size={size}&region_id={region_id}", False, ["location", "size", "region_id"]),
   endpoint("stopinfo", "GET", "https://citymapper.com/api/3/stopinfo?ids={alias or id}&region_id={region_id}", True, ["ids", "region_id"], shape={"stops[]": "id, requested_id, alias, name, coords, route_ids, brand_ids, url, sharing_urls[{departure_api, url}], exits[], stop_curation_url_ids", "routes[]": "id, name, brand_id, icon_name, color"}),
   endpoint("departures-bus", "GET", "https://citymapper.com/api/1/departures?headways=1&ids={stop_id}&region_id={region_id}", True, ["headways", "ids", "region_id"], shape={"stops[]": "id, name, coords, bearing, region_id, routes[], services[{route_id, headsign, live_departures_seconds[], representative_pattern_id}]"}, pagination="poll-30s", notes="Bus and ferry stops."),
   endpoint("departures-metro", "GET", "https://citymapper.com/api/2/metrodepartures?headways=1&ids={station_id}&region_id={region_id}", True, ["headways", "ids", "region_id"], shape={"stations[]": "station{name, coords, live_code, status}, sections[{id, name, departure_types, departure_groupings[{grouping_id, departures[{route_id, destination_name, time_seconds | scheduled_time, pattern_id, direction_id, is_advisory_message}]}]}], routes[], messages[]", "last_updated_time": "str"}, pagination="poll-30s", notes="Observed in NYC and Paris."),
   endpoint("departures-rail", "GET", "https://citymapper.com/api/1/raildepartures?headways=1&ids={station_id}&region_id={region_id}", True, ["headways", "ids", "region_id"], shape={"stations[]": "station{...}, can_have_departures, departures[{destination, route_id, brand_id, pattern_id, scheduled_time, expected_departure_time, time_seconds, is_live, status, platform_number, trip_short_name, stops[]}]"}, pagination="poll-30s"),
   endpoint("schedules", "GET", "https://citymapper.com/api/1/schedules?id={stop_id}&region_id={region_id}&time={time}", False, ["id", "region_id", "time"]),
   endpoint("routeinfo1", "GET", "https://citymapper.com/api/1/routeinfo?route={alias}&region_id={region_id}&weekend=1&status_format=rich&extended=1", True, ["route", "region_id", "weekend", "status_format", "extended"], shape={"routes[]": "id, name, long_name, brand, mode, color, live_line_code, live_availability, url, aliases, status{level, summary, description, replacements}, patterns[{id, name, pattern_type, path, stop_points}]", "stops": "{stop_id: {name, coords, routes, brands, live_code, status}}", "feeds[]": "...", "status": "int"}),
   endpoint("routeinfo2", "GET", "https://citymapper.com/api/2/routeinfo?route_ids={id,id}&region_id={region_id}&weekend=1&status_format=rich", True, ["route_ids", "region_id", "weekend", "status_format", "extended"], shape={"routes[]": "same route shape as routeinfo1", "stops": "{stop_id: {...}}"}),
   endpoint("routepaths", "GET", "https://citymapper.com/api/1/routepaths?route_ids={ids}&region_id={region_id}", False, ["route_ids", "region_id"]),
   endpoint("routestatus", "GET", "https://citymapper.com/api/1/routestatus?region_id={region_id}&format=rich", True, ["region_id", "format"], ["accept", "citymapper-region", "content-type", "referer"], shape={"groupings[]": "id, name, include_in_disruption_count, routes[{name, long_name, brand, aliases, status{level, summary, description, replacements, disruptions[{level, summary, description, replacements, stops}]}}], partners[]", "last_updated_time": "str", "referenced_routes[]": "..."}, pagination="poll-2min"),
   endpoint("findtransport", "GET", "https://citymapper.com/api/2/findtransport?query={text}&region_id={region_id}", True, ["query", "region_id"], notes="Observed in your browser (URL only, body not captured)."),
   endpoint("vehiclelocations", "GET", "https://citymapper.com/api/1/vehiclelocations?route={route}&region_id={region_id}", False, ["route", "region_id"], pagination="poll-10s"),
   endpoint("message", "GET", "https://citymapper.com/api/2/message?had_previous_versions=0", True, ["had_previous_versions"], ["accept", "citymapper-region", "content-type", "referer"], shape={"messages[]": "..."}),
   endpoint("weather", "GET", "https://citymapper.com/api/1/weather?location={lat,lng}&units={c|f}&term=now", False, ["location", "units", "term"]),
   endpoint("transitscore", "GET", "https://citymapper.com/api/1/transitscore?startcoord={lat,lng}", False, ["startcoord"]),
   endpoint("traveltime", "GET", "https://citymapper.com/api/1/traveltime?startcoord={lat,lng}&endcoord={lat,lng}&region_id={region_id}", False, ["startcoord", "endcoord", "region_id"]),
   endpoint("blog", "GET", "https://citymapper.com/api/1/blog[?id={id}]", False, ["id"]),
   endpoint("resources", "GET", "https://citymapper.com/api/1/resources?id={resource_id}", False, ["id"], surface="html", notes="Linked from the footer for the terms and privacy policy."),
   endpoint("city-html", "GET", "https://citymapper.com/{region_slug}", True, surface="html", shape={"window.citymapper.region": "region_id, region_name, region_slug, bounding_box, default_place, nearby_modes[], timezone, core_brand_ids, distance_units, feature flags", "window.citymapper.regions": "[[region, distance_km]] x115", "window.citymapper.citiesInRegions": "{city_slug: {city_name, city_id, region_id, default_place, show_in_city_switcher}} x252", "window.citymapper.brands": "{brand_id: {..., departure_apis}}", "window.citymapper.apiUrl": "/api/"}, notes="2 MB to 15 MB of HTML; the one source of the region list."),
   endpoint("cities-html", "GET", "https://citymapper.com/cities", True, surface="html", notes="Same window.citymapper globals; city tiles link to /{region_slug}."),
   endpoint("news-html", "GET", "https://citymapper.com/news", True, surface="html"),
   endpoint("resource-region-info", "GET", "https://citymapper.com/resource/region-info/{region_id}", True, shape={"$": "region_id, region_name, region_slug, bounding_box, default_place, nearby_modes[], offline_maps[], timezone, region_is_launched, web_enabled, api_enabled, core_brand_ids, default_cycle_brand_id, distance_units, clock, ondemand"}, notes="JSON region config; landing.js calls it with the cm_region cookie value."),
   endpoint("resource-brand-directory", "GET", "https://citymapper.com/resource/brand-directory", True, notes="445 KB JSON brand catalogue."),
   endpoint("identity-user-data", "GET", "https://citymapper.com/api/1/identity/user_data", True, ["accept", "content-type", "referer"], notes="403 with an empty body while signed out (observed); user object when signed in."),
   endpoint("identity-sessions-create", "POST", "https://citymapper.com/api/1/identity/sessions", False, [], ["auth_provider", "email", "password", "access_token", "source_page", "has_seen_marketing_opt_out", "has_opted_out_of_marketing", "is_interested_in_pass"]),
   endpoint("identity-sessions-delete", "DELETE", "https://citymapper.com/api/1/identity/sessions", False),
   endpoint("identity-magiclink", "POST", "https://citymapper.com/api/1/identity/magiclink/create", False, [], ["email", "force_prototype", "source_page", "has_seen_marketing_opt_out", "has_opted_out_of_marketing", "is_interested_in_pass", "redirect_path"]),
   endpoint("identity-update-user", "POST", "https://citymapper.com/api/1/identity/update_user", False, [], ["first_name", "last_name", "mobile", "is_interested_in_pass"]),
   endpoint("identity-password-reset", "POST", "https://citymapper.com/api/1/identity/password_reset[/{token}]", False, [], ["email", "new_password"]),
   endpoint("identity-confirm-signup", "POST", "https://citymapper.com/api/1/identity/confirm_sign_up/{token}", False),
   endpoint("identity-places-list", "GET", "https://citymapper.com/api/1/identity/places", False),
   endpoint("identity-places-create", "POST", "https://citymapper.com/api/1/identity/places", False, [], ["name", "address", "coords", "role", "place_id"], notes="Body is the place object; role home or work for those slots (bundle)."),
   endpoint("identity-places-update", "PUT", "https://citymapper.com/api/1/identity/places/{place_id}", False, [], ["name", "address", "coords", "role"]),
   endpoint("identity-places-delete", "DELETE", "https://citymapper.com/api/1/identity/places/{place_id}", False),
   endpoint("identity-favorites-list", "GET", "https://citymapper.com/api/1/identity/favorites", False),
   endpoint("identity-favorites-create", "POST", "https://citymapper.com/api/1/identity/favorites", False, [], ["target_type", "target_id", "region_id"], notes="target_type 1 bus stop, 2 station, 3 transit line (bundle)."),
   endpoint("identity-favorites-delete", "DELETE", "https://citymapper.com/api/1/identity/favorites/{favourite_id}", False),
   endpoint("identity-save-journey", "POST", "https://citymapper.com/api/1/identity/documents/SavedJourney", False, [], ["document_data"]),
   endpoint("identity-delete-journey", "DELETE", "https://citymapper.com/api/1/identity/documents/SavedJourney/{document_id}", False),
   endpoint("turnstile-userinfo", "POST", "https://turnstile-api.citymapper.com/web/1/userinfo", False, [], ["payment_provider_id"], ["user-device", "session-id", "content-type"]),
   endpoint("turnstile-addpaymentmethod", "POST", "https://turnstile-api.citymapper.com/web/1/addpaymentmethod", False, [], ["payment_method_id", "payment_provider_id"], ["user-device", "session-id", "content-type"]),
   endpoint("turnstile-setdefaultpaymentmethod", "POST", "https://turnstile-api.citymapper.com/web/1/setdefaultpaymentmethod", False, [], ["payment_method_id", "payment_provider_id"], ["user-device", "session-id", "content-type"]),
   endpoint("turnstile-deletepaymentmethod", "POST", "https://turnstile-api.citymapper.com/web/1/deletepaymentmethod", False, [], ["payment_method_id", "payment_provider_id"], ["user-device", "session-id", "content-type"]),
   endpoint("turnstile-deleteallpaymentmethods", "POST", "https://turnstile-api.citymapper.com/web/1/deleteallpaymentmethods", False, [], ["payment_provider_id"], ["user-device", "session-id", "content-type"]),
   endpoint("turnstile-sessionttl", "GET", "https://turnstile-api.citymapper.com/web/1/sessionttl", False, [], [], ["user-device", "session-id"]),
   endpoint("city-vote", "POST", "https://citymapper.com/cities/vote_submit/", False, [], ["city_slug", "email"], ["x-csrftoken", "content-type"]),
   endpoint("logevents", "POST", "https://citymapper.com/api/2/logevents", True, [], ["text/plain event lines"], ["citymapper-client", "citymapper-region", "user-device", "content-type"], noise=True, notes="Analytics."),
   endpoint("resourceproxy-images", "GET", "https://global-api.citymapper.com/resourceproxy/{name}.png", True, noise=True, notes="City illustrations on /cities."),
   endpoint("static-img", "GET", "https://citymapper.com/static-img?src={icon names}", True, noise=True, notes="Route icons."),
]

ENTITIES = [
   {"id": "region", "description": "A supported metro area; the unit every API call is scoped by", "fields": ["region_id", "region_name", "region_slug", "region_name_aliases", "bounding_box", "default_place", "timezone", "web_enabled", "api_enabled", "nearby_modes", "core_brand_ids", "distance_units"], "id_fields": ["region_id", "region_slug"], "source_endpoints": ["city-html", "resource-region-info"]},
   {"id": "city", "description": "A city inside a region (252)", "fields": ["city_id", "city_name", "city_slug", "region_id", "default_place", "show_in_city_switcher"], "id_fields": ["city_id", "city_slug"], "source_endpoints": ["city-html"]},
   {"id": "nearby-mode", "description": "A mode tile for nearby searches in a region", "fields": ["mode_id", "mode_slug", "short_title", "kind_ids", "request_brand_ids", "priority_brand_ids", "mode_type"], "id_fields": ["mode_id"], "source_endpoints": ["city-html", "resource-region-info"]},
   {"id": "brand", "description": "A transport operator or network", "fields": ["brand_id", "name", "departure_apis", "affinities"], "id_fields": ["brand_id"], "source_endpoints": ["city-html", "resource-brand-directory"]},
   {"id": "place", "description": "A search result: station, stop, address or Google place", "fields": ["id", "name", "address", "coords", "type", "result_type", "source", "brands", "lines"], "id_fields": ["id"], "source_endpoints": ["searchpost", "placeresolve", "geocode"]},
   {"id": "journey", "description": "One planned option", "fields": ["duration_seconds", "walk_seconds", "distance_meters", "calories", "legs", "signature", "formatted_price", "price_amount", "currency_code", "journey_equivalence_hash", "profile_id", "journey_kind"], "id_fields": ["signature", "journey_equivalence_hash"], "source_endpoints": ["journeys", "walk7", "cycle", "taxi", "refreshjourneys"]},
   {"id": "leg", "description": "A part of a journey", "fields": ["mode", "routes", "stops", "shape", "frequency", "departure_time", "arrival_time", "pattern_ids", "distance", "duration"], "id_fields": [], "source_endpoints": ["journeys"]},
   {"id": "journey-time", "description": "Live timing for a journey signature", "fields": ["time", "time_mode", "leg_times", "formatted_price", "traffic_level", "request_signature"], "id_fields": ["request_signature"], "source_endpoints": ["journeytimes"]},
   {"id": "nearby-element", "description": "A stop, station, pier or dock near a point", "fields": ["id", "name", "coords", "kind", "alias", "brand_ids", "route_ids", "route_names", "bearing", "walk_time_seconds", "cycles_available", "cycles_spaces", "cycles_electric_available"], "id_fields": ["id", "alias"], "source_endpoints": ["nearby3", "nearby2"]},
   {"id": "stop", "description": "A stop or station with routes and exits", "fields": ["id", "alias", "name", "coords", "route_ids", "brand_ids", "exits", "sharing_urls"], "id_fields": ["id", "alias"], "source_endpoints": ["stopinfo"]},
   {"id": "departure", "description": "A live or scheduled departure", "fields": ["route_id", "destination_name", "headsign", "time_seconds", "scheduled_time", "expected_departure_time", "live_departures_seconds", "is_live", "platform_number", "pattern_id", "direction_id"], "id_fields": [], "source_endpoints": ["departures-bus", "departures-metro", "departures-rail"]},
   {"id": "route", "description": "A line", "fields": ["id", "name", "long_name", "brand", "mode", "color", "aliases", "live_line_code", "status", "patterns", "url"], "id_fields": ["id", "aliases"], "source_endpoints": ["routeinfo1", "routeinfo2", "routestatus", "findtransport"]},
   {"id": "pattern", "description": "A branch or direction of a line", "fields": ["id", "name", "pattern_type", "path", "stop_points"], "id_fields": ["id"], "source_endpoints": ["routeinfo1"]},
   {"id": "route-status", "description": "A line's current service level", "fields": ["level", "summary", "description", "replacements", "disruptions"], "id_fields": [], "source_endpoints": ["routestatus", "routeinfo1", "routeinfo2"]},
   {"id": "disruption", "description": "One disruption on a line", "fields": ["level", "summary", "description", "replacements", "stops"], "id_fields": [], "source_endpoints": ["routestatus"]},
   {"id": "vehicle", "description": "A live vehicle position on a line (bundle)", "fields": ["inferred"], "id_fields": [], "source_endpoints": ["vehiclelocations"]},
   {"id": "message", "description": "Site-wide notice", "fields": ["messages"], "id_fields": [], "source_endpoints": ["message"]},
   {"id": "go-link", "description": "A Meet Me Somewhere short link", "fields": ["url", "endcoord", "endname", "endaddress", "title", "message"], "id_fields": ["slug"], "source_endpoints": ["createshorturl", "getshorturl"]},
   {"id": "news-post", "description": "A news article", "fields": ["id", "slug", "title"], "id_fields": ["id"], "source_endpoints": ["news-html", "blog"]},
   {"id": "user", "description": "The signed-in user (bundle)", "fields": ["id", "email", "first_name", "last_name", "mobile", "is_interested_in_pass", "has_seen_marketing_opt_out", "has_opted_out_of_marketing"], "id_fields": ["id"], "source_endpoints": ["identity-user-data"]},
   {"id": "saved-place", "description": "A saved place (bundle)", "fields": ["place_id", "name", "address", "coords", "role"], "id_fields": ["place_id"], "source_endpoints": ["identity-places-list"]},
   {"id": "favourite", "description": "A favourite stop, station or line (bundle)", "fields": ["id", "target_type", "target_id", "region_id"], "id_fields": ["id"], "source_endpoints": ["identity-favorites-list"]},
   {"id": "saved-journey", "description": "A journey sent to the phone (bundle)", "fields": ["document_id", "document_data"], "id_fields": ["document_id"], "source_endpoints": ["identity-save-journey"]},
   {"id": "payment-method", "description": "A Citymapper Pass payment method (bundle)", "fields": ["payment_method_id", "payment_provider_id"], "id_fields": ["payment_method_id"], "source_endpoints": ["turnstile-userinfo"]},
]

AUTH = {
   "mechanism": "cookie-session (Django sessionid), optional; every public read works signed out",
   "cookie_names": ["sessionid", "csrftoken", "uid", "uid_set", "cm_region", "_locale", "__cf_bm"],
   "header_names": ["Citymapper-Region", "Citymapper-Client", "User-Device", "Session-Id (turnstile only)", "X-CSRFToken (city vote only)"],
   "csrf": "A csrftoken cookie is set on first visit, but the bundle sends X-CSRFToken only on the uncalled city vote; identity writes send none (unknown whether the server enforces it)",
   "login_flow": "E-mail magic link (POST identity/magiclink/create), Google Identity Services access token or Facebook SDK token posted to identity/sessions; no password form in the UI; no Apple sign-in",
   "session_lifetime": "unknown; you are signed out",
   "refresh": "none observed; a signed-out session answers 403 on identity/user_data",
}

PAGINATION = [
   {"id": "time-window-journeys", "kind": "none", "request_keys": ["departure_time", "arrival_time", "limit"], "response_keys": ["sections", "journeys"], "terminator": "one response per query; a later window is a new query with a later departure_time", "page_size": None},
   {"id": "poll-30s", "kind": "none", "request_keys": ["ids", "headways"], "response_keys": ["time_seconds", "scheduled_time", "live_departures_seconds", "last_updated_time"], "terminator": "the response is the next departures window (about 30 to 60 minutes); the UI re-polls every 30 s", "page_size": None},
   {"id": "poll-2min", "kind": "none", "request_keys": ["region_id"], "response_keys": ["last_updated_time"], "terminator": "single snapshot; the UI refetches every 2 minutes", "page_size": None},
   {"id": "poll-10s", "kind": "none", "request_keys": ["route"], "response_keys": [], "terminator": "single snapshot; the UI refetches every 10 s (bundle)", "page_size": None},
   {"id": "limit-50", "kind": "offset-limit", "request_keys": ["limit", "location", "viewspan"], "response_keys": ["elements", "bounding_box"], "terminator": "fewer than limit elements, or move the location; no offset or cursor exists", "page_size": 50},
]

CAVEATS = [
   {"kind": "anti-bot", "detail": "Cloudflare fronts the site and sets __cf_bm. No challenge appeared for your browser, a separate CDP Brave profile or plain curl; behaviour at higher rates is untested.", "severity": "medium", "evidence": "response headers server: cloudflare, cf-ray, set-cookie __cf_bm (curl and CDP captures 2026-10-10)"},
   {"kind": "rate-limit", "detail": "No rate-limit headers (x-ratelimit-*, retry-after) on any API response; thresholds unknown. Pace at 3 s or more per request.", "severity": "medium", "evidence": "response headers in var/captures/run-2026-10-10-082844-*.jsonl list only cf-cache-status and x-version"},
   {"kind": "signing", "detail": "No request signing or nonce. The journey 'signature' is a JSON journey descriptor returned by the planner; /trip/signature?signature= carries it pako-deflated and base64 encoded.", "severity": "low", "evidence": "journeys[].signature is a 900-character JSON string; bundle route table (research/bundle/api-inventory.md)"},
   {"kind": "csrf", "detail": "Identity writes (places, favourites, saved journeys) send no CSRF header from the web client; whether the server enforces csrftoken is unknown until a signed-in write is tried.", "severity": "medium", "evidence": "api-inventory.md section (b) Auth"},
   {"kind": "other", "detail": "Web account exists but you are signed out on citymapper.com, and signing in may create an account (magic link, Google or Facebook). Account reads and writes cannot be verified until you sign in yourself.", "severity": "high", "evidence": "GET /api/1/identity/user_data 403 in your browser; login dialog shows e-mail, Facebook, Google"},
   {"kind": "other", "detail": "Citymapper Club and Pass are paid features; Pass payment methods live on turnstile-api.citymapper.com and need a Session-Id the web pages never expose. App-only on the web.", "severity": "high", "evidence": "bundle turnstile methods with no caller; news posts on Club features"},
   {"kind": "other", "detail": "Share and Meet Me Somewhere links (createtripurl, createshorturl) are GET requests that create public URLs; they are writes visible to others.", "severity": "medium", "evidence": "bundle create-links.js; trip-share.js calls it on mount of the share block"},
   {"kind": "feature-flag", "detail": "8 regions have api_enabled false (fr-nantes, fr-bordeaux, fr-toulouse, fr-strasbourg, fr-marseille, ch-ch, mc-monaco, at-vienna); routing there may be absent or partial. Coordinates outside a region's bounding box are rejected client side as out of bounds.", "severity": "medium", "evidence": "window.citymapper.regions in the /nyc HTML; journey-results toggleOutOfBounds"},
   {"kind": "realtime", "detail": "No websockets or SSE. Live data is polled: departures and journey times every 30 s, line status every 2 minutes, vehicles every 10 s.", "severity": "low", "evidence": "CDP captures report 0 websocket frames; bundle timers"},
   {"kind": "other", "detail": "Region config and the city list exist only inside 2 to 15 MB server-rendered HTML pages (or /resource/region-info per region); reading the city list costs one large page load, so it should be cached.", "severity": "medium", "evidence": "city-paris 4.8 MB, nearby-paris-metro 15 MB, city-london 8 MB in capture logs"},
   {"kind": "other", "detail": "Embedded Google Maps browser key (39 characters) and Google and Facebook client ids in the bundle; only used for map tiles and social sign-in, never needed by the program.", "severity": "low", "evidence": "bundle constants GOOGLE_MAPS_API_KEY, GOOGLE_KEY, FACEBOOK_APP_ID (names and lengths only)"},
   {"kind": "terms", "detail": "This is the website's private API, not the official developer API; the terms of service link is /api/1/resources?id=citymapper-terms-of-service.", "severity": "medium", "evidence": "footer link"},
   {"kind": "other", "detail": "Bike docks have no detail page (404); dock availability comes from nearby results only.", "severity": "low", "evidence": "GET /nyc/bike/docks/CitiBike_904930bd-... 404 (capture stop-nyc-bike)"},
   {"kind": "other", "detail": "The web client's delete-place call passes placeId where place_id is required, so the web UI cannot remove a saved place; the program must send place_id itself.", "severity": "low", "evidence": "bundle user-actions.js removePlace (api-inventory.md)"},
]

OPEN_QUESTIONS = [
   "Account surface (user_data, places, favourites, saved journeys, update_user) is mapped from the bundle only: response shapes and CSRF enforcement need one signed-in session, which only you can create.",
   "vehiclelocations was not fired on any line page walked (live_availability 0 on NYC 6, M15, London Bakerloo); which regions have live vehicles is unknown.",
   "refreshjourneys, gettrip, getshorturl, eta, placeresolve, geocode, schedules, routepaths, everythingmap, weather, transitscore, traveltime, vehiclehire, walk v1 and blog are defined in the bundle but were not observed live; the engineer stage replays them once each.",
   "Response bodies of findtransport were not captured (seen by URL in your browser only).",
   "How far ahead departure_time may be set, and whether past times are accepted, is untested.",
   "Brand planner pages (/{region}/planner/{brand}) were not visited; valid brand slugs are unknown.",
]
