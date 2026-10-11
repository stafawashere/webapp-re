# Citymapper scope

Generated 2026-10-10 from a read-only walk of https://citymapper.com in your browser (signed out, since you have no Citymapper session there), CDP captures of the same pages in a separate signed-out browser profile, and the site's public JS bundle.

## Summary

Citymapper's website is a public transit journey planner for 115 regions (252 cities) worldwide. Everything a visitor can do without an account goes through unsigned same-origin JSON calls under https://citymapper.com/api/<version>/: journey planning (transit, walk, cycle, cab and on-demand) between coordinates with depart-at or arrive-by times, live journey times, place search and autocomplete, nearby stops, stations, piers and bike docks per mode, stop details with live departures (bus, metro and rail feeds), line pages with stops, patterns and service status, region-wide line status with disruption texts, and line search. The city is always an explicit region_id parameter; the list of regions and cities, each region's modes, brands, bounding box and timezone are inlined into every server-rendered page as window.citymapper. A web account exists (sign in by e-mail magic link, Google or Facebook) and adds saved places (home, work, others), favourite stops and lines, and 'send to phone' saved journeys, all under /api/1/identity/. You are signed out on citymapper.com, so the account surface was mapped from the bundle and was not exercised; Citymapper Club and Pass payments are app-only. No request signing, nonce, captcha or bot challenge appeared; the site sits behind Cloudflare (__cf_bm) and served 200 to a separate CDP browser and to curl.

Origins: https://citymapper.com, https://global-api.citymapper.com, https://turnstile-api.citymapper.com. Framework: react (react-router SPA bundle /static/components/bundle-<hash>.js inside server-rendered Django pages; landing page is a separate React bundle; some routes are Next.js SSR). Bundler: webpack (module ids, __REACT_HOT_LOADER__ source paths /__w/web/web/src/...). Source maps: False.

## Page map

| Page | URL pattern | Auth | Visited | Purpose | Endpoints |
|---|---|---|---|---|---|
| page-home | / | False | True | Landing page: Get Me Somewhere form, city switcher, news teasers; fetches the current region's info and the brand directory | resource-region-info, resource-brand-directory, identity-user-data, message |
| page-webapp | /webapp, /{region_slug}/webapp | False | True | Journey planner shell: start and end search boxes, Now, Arrive, Leave time selector, map | searchpost, geocode, identity-user-data, message |
| page-directions | /directions?startcoord={lat,lng}&endcoord={lat,lng}&startname=&endname=&startaddress=&endaddress=&departure_time={iso}/arrival_time={iso} | False | True | Journey results: walk, cycle and cab summary row, Suggested and other sections of transit journeys with price, duration and live next departures | journeys, walk7, cycle, taxi, journeytimes, searchpost |
| page-trip-signature | /trip/signature?signature={deflated base64 journey signature} | False | True | Journey detail: legs, stops, exits, live times; share and send-to-phone buttons | trip-meta, journeytimes, refreshjourneys, createtripurl, identity-save-journey |
| page-trip-slug | /trip/{slug} | False | False | Shared trip link: resolves a slug to a journey signature, then shows the journey detail | gettrip, refreshjourneys |
| page-go | /go/{slug}, /widget/{slug} | False | False | Meet Me Somewhere link: destination card that plans a journey to a saved place | getshorturl |
| page-meet | /meet | False | True | Meet Me Somewhere marketing page and place box that creates a go link | createshorturl |
| page-city | /{region_slug} | False | True | City home: journey form, account box, nearby mode tiles, lines card with status, Meet Me Somewhere box, strike map | city-html, routestatus, routeinfo2, findtransport, message, identity-user-data |
| page-status | /{region_slug}/status | False | True | All lines status for the region grouped by mode, with disruption details and partner status | routestatus, routeinfo2 |
| page-nearby | /{region_slug}/{mode_slug}/{stop_type}?name=&coords={lat,lng} | False | True | Nearby list and map for one mode (stations, stops, docks, piers) around a point | nearby3, routeinfo2 |
| page-stop | /{region_slug}/{mode_slug}/{stop_type}/{alias} | False | True | Stop or station: routes, exits, live departures by platform or direction, nearby stops; favourite star | stopinfo, departures-bus, departures-metro, departures-rail, nearby2 |
| page-line | /{region_slug}/{mode_slug}/{line_alias} (also /{region_slug}/l/{line_alias}, which redirects) | False | True | Line: branches (patterns), ordered stops, map path, status; favourite star and share | routeinfo1, vehiclelocations |
| page-planner | /{region_slug}/planner/{brand} | False | False | Brand-only journey planner for a partner network (journeys sent with partner=) | routestatus, routeinfo1, nearby3, journeys |
| page-cities | /cities | False | True | All cities; picking one writes the cm_region cookie and reloads | cities-html |
| page-news | /news, /news/{id}/{slug}, /i/{id}/{slug} | False | True | Company news posts (server rendered) | news-html, blog |
| page-login-dialog | /{region_slug}#login (modal) | False | True | Sign up or log in: e-mail magic link, Facebook, Google | identity-magiclink, identity-sessions-create |
| page-legal | /api/1/resources?id=citymapper-terms-of-service/citymapper-privacy-policy | False | False | Terms of service and privacy policy documents | resources |
| page-server-only | /eta/{slug}, /pass, /pass/{slug}, /ride, /authorise/{reference}, /signup/{token}/confirm, /reset/{token}/continue, /p/reset_password, /account-deletion/{token} | False | False | Server-rendered pages for shared ETAs, Citymapper Pass, payments authorisation and account e-mail flows; no caller in the web bundles | eta, turnstile-userinfo, identity-password-reset |

## Capabilities

| Capability | User action | Mutates | Others see | Exercised | Endpoints | Notes |
|---|---|---|---|---|---|---|
| cap-plan-journey | Type a start and an end (or click the map), pick Now, Arrive or Leave, press GO | False | False | True | journeys, searchpost | Inputs: start and end coordinates (names and addresses optional), region_id, departure_time or arrival_time as ISO UTC, step-free and microtransit flags. Returns sections (Suggested, others) and journeys with legs, live departure hints, price and duration. Exercised in NYC (now and arrive-by) and London (now), Paris (depart-at). |
| cap-plan-walk | Same form; the walk tile in the summary row | False | False | True | walk7, walk1 | limit=2 profiles (fast, and a second). |
| cap-plan-cycle | Same form; the cycle tile | False | False | True | cycle | Profiles quiet, regular, fast; bike share journeys carry price and brand (CitiBike, Santander, Velib); shared.cycle_docks. |
| cap-plan-cab | Same form; the cab tile | False | False | True | taxi | routes[] with duration and length, on_demand_model.categories (Uber, Lyft and local services) where the region has them. |
| cap-plan-vehicle-hire | No web UI caller; bundle method getVehicleHireJourneys | False | False | False | vehiclehire | Defined in the bundle; observed false. |
| cap-journey-times | Automatic every 30 s on results and detail pages | False | False | True | journeytimes | POST body signatures[] (journey signature JSON strings). Up to 10 polls in the UI. |
| cap-journey-detail | Click a journey in the results | False | False | True | refreshjourneys, trip-meta, journeytimes | Navigates to /trip/signature?signature=<deflated base64>; a direct load calls POST /api/1/refreshjourneys (exercised only as an in-app navigation, which reused the stored journey). |
| cap-open-shared-trip | Open /trip/{slug} | False | False | False | gettrip, refreshjourneys |  |
| cap-share-trip | Journey detail, share icon | True | True | False | createtripurl | Creates a public short URL. Not pressed. |
| cap-save-journey | Journey detail, send-to-phone icon (needs sign-in) | True | False | False | identity-save-journey, identity-delete-journey | POST /api/1/identity/documents/SavedJourney {document_data}; delete by document_id. No list endpoint on the web. |
| cap-search-places | Type in the Start or End box | False | False | True | searchpost | POST form body: query, region_id, location (optional bias), is_refinement, refinement_data, powersearch. Results mix Citymapper stations and Google places with coords. |
| cap-resolve-place | Pick a search result whose coords are missing | False | False | False | placeresolve | Google results observed carry coords, so no call was made. |
| cap-reverse-geocode | Click the map to set Start or End | False | False | False | geocode | GET /geocode?lat=&lng= (same origin, outside /api). The map click observed hit a Google POI, which carries its own name. |
| cap-nearby | City page Nearby tile, or /{city}/{mode}/{stop_type}?coords= | False | False | True | nearby3, nearby2 | Per mode: brand_ids or kinds, mode_id, location, limit 50, extended=1. Bike docks carry cycles_available, spaces, electric and manual counts. |
| cap-stop-info | Open a stop page | False | False | True | stopinfo | ids accepts the alias or the id. Returns routes, exits, sharing_urls with the departure API to use. |
| cap-live-departures | Open a stop page; refreshes every 30 s | False | False | True | departures-bus, departures-metro, departures-rail | The brand's departure_apis picks the endpoint: departures (bus, ferry), metrodepartures (subway, metro, tube), raildepartures (commuter rail). Live seconds mixed with scheduled ISO times. |
| cap-stop-schedule | No web UI caller; bundle getSchedules | False | False | False | schedules |  |
| cap-line-info | Open a line page | False | False | True | routeinfo1 | route=<alias>, extended=1 adds patterns with stop_points and paths. |
| cap-lines-info | City page lines card and strike map | False | False | True | routeinfo2 | route_ids=comma list; weekend=1; status_format=rich. |
| cap-line-status | City page lines card, /{city}/status | False | False | True | routestatus | groupings by mode with routes[].status level, summary, description and disruptions; partners (scooters, bikes, cabs). |
| cap-disruptions | Status page, expand a line | False | False | True | routestatus, routeinfo2 | status.disruptions[] with level, summary, description template, replacements and affected stops. |
| cap-find-line | City page Lines card, type in Find a bus or line | False | False | True | findtransport | GET /api/2/findtransport?query=&region_id= as you type. |
| cap-vehicle-locations | Line page with live_line_code; 10 s timer | False | False | False | vehiclelocations | Not fired on the NYC 6, M15 or London Bakerloo pages (live_availability 0). |
| cap-route-paths | No web UI caller; bundle getRoutePaths | False | False | False | routepaths |  |
| cap-everything-map | No web UI caller; bundle getEverything | False | False | False | everythingmap |  |
| cap-list-cities | Open /cities or the Switch City menu | False | False | True | cities-html, city-html | 115 regions and 252 cities inlined in page HTML; 8 regions have api_enabled false. |
| cap-city-info | Open a city page or the home page | False | False | True | city-html, resource-region-info |  |
| cap-switch-city | Switch City, pick a city | False | False | False | cities-html | Client side: sets the cm_region cookie and reloads; the program passes region_id explicitly instead. |
| cap-brand-directory | Home page loads it | False | False | True | resource-brand-directory |  |
| cap-message | Every page load | False | False | True | message | messages[] is usually empty. |
| cap-weather | No web UI caller; bundle getWeather | False | False | False | weather |  |
| cap-transit-score | No web UI caller; bundle getTransitScore | False | False | False | transitscore |  |
| cap-travel-time | No web UI caller; place.js makeTravelTimeRequest | False | False | False | traveltime |  |
| cap-shared-eta | Open /eta/{slug} (server rendered); bundle getETA | False | False | False | eta |  |
| cap-open-go-link | Open /go/{slug} | False | False | False | getshorturl |  |
| cap-create-go-link | City page or /meet: type a place and press the arrow | True | True | False | createshorturl | Creates a public short URL with a title and message. Not pressed. |
| cap-news | Footer News, or /news | False | False | True | news-html, blog |  |
| cap-legal | Footer Terms or Privacy | False | False | False | resources |  |
| cap-sign-in | Account box, Sign up or log in: e-mail, Facebook or Google | True | False | False | identity-magiclink, identity-sessions-create | Dialog opened, nothing submitted. Signing in can create an account, so the program will not automate it; you sign in yourself. |
| cap-sign-out | Account menu, log out | True | False | False | identity-sessions-delete |  |
| cap-user-data | Every page load | False | False | True | identity-user-data | 403 while signed out (observed). |
| cap-update-user | No web UI caller; bundle updateUser | True | False | False | identity-update-user |  |
| cap-saved-places | Search box Saved Places section (signed in) | False | False | False | identity-places-list |  |
| cap-save-place | Star a place (signed in) | True | False | False | identity-places-create |  |
| cap-update-place | No web UI caller; bundle updateUserPlace | True | False | False | identity-places-update |  |
| cap-remove-place | Unstar a saved place (signed in) | True | False | False | identity-places-delete | The web client passes placeId where place_id is required, so the web UI throws before sending (bundle reading). |
| cap-favourites | Lines card and stop pages (signed in) | False | False | False | identity-favorites-list |  |
| cap-favourite-stop | Star on a stop page (signed in) | True | False | False | identity-favorites-create, identity-favorites-delete |  |
| cap-favourite-line | Star on a line page (signed in) | True | False | False | identity-favorites-create, identity-favorites-delete |  |
| cap-password-reset | Server pages /p/reset_password, /signup/{token}/confirm; no web UI caller | True | False | False | identity-password-reset, identity-confirm-signup |  |
| cap-pass-payments | Server pages /pass and /authorise; no web UI caller | True | False | False | turnstile-userinfo, turnstile-addpaymentmethod, turnstile-setdefaultpaymentmethod, turnstile-deletepaymentmethod, turnstile-deleteallpaymentmethods, turnstile-sessionttl | Paid product on turnstile-api.citymapper.com; needs a Session-Id and User-Device. Out of reach without the app and an account. |
| cap-city-vote | No web UI caller; POST /cities/vote_submit/ with X-CSRFToken | True | False | False | city-vote |  |
| cap-telemetry | Every page | True | False | True | logevents | Noise, never called by the program. |

## Endpoints

| Endpoint | Method | URL pattern | Surface | Observed | Query | Body | Pagination | Notes |
|---|---|---|---|---|---|---|---|---|
| journeys | GET | https://citymapper.com/api/7/journeys | rest | True | start, end, saddr, eaddr, sname, ename, region_id, departure_time, arrival_time, include_stepfree, include_networks, include_floating, include_via_microtransit, limit, context, partner, cycle, status_format |  | time-window-journeys | Transit journeys. start and end are 'lat,lng'. Observed keys: start, end, sname, ename, saddr, region_id, include_stepfree=1, include_via_microtransit=1, status_format=html, arrival_time or departure_time ISO UTC. 97 KB for NYC, 166 KB for London. |
| walk7 | GET | https://citymapper.com/api/7/walk | rest | True | start, end, saddr, eaddr, sname, ename, region_id, departure_time, arrival_time, include_stepfree, include_networks, include_floating, include_via_microtransit, limit, context, partner, cycle, status_format |  | time-window-journeys | limit=2 in the UI. |
| walk1 | GET | https://citymapper.com/api/1/walk | rest | False | start, end, saddr, eaddr, sname, ename, region_id, departure_time, arrival_time, include_stepfree, include_networks, include_floating, include_via_microtransit, limit, context, partner, cycle, status_format |  |  | Older walk endpoint; bundle only. |
| cycle | GET | https://citymapper.com/api/6/cycle | rest | True | start, end, saddr, eaddr, sname, ename, region_id, departure_time, arrival_time, include_stepfree, include_networks, include_floating, include_via_microtransit, limit, context, partner, cycle, status_format |  | time-window-journeys |  |
| taxi | GET | https://citymapper.com/api/2/taxi | rest | True | start, end, saddr, eaddr, sname, ename, region_id, departure_time, arrival_time, include_stepfree, include_networks, include_floating, include_via_microtransit, limit, context, partner, cycle, status_format |  |  |  |
| vehiclehire | GET | https://citymapper.com/api/7/vehiclehire | rest | False | start, end, saddr, eaddr, sname, ename, region_id, departure_time, arrival_time, include_stepfree, include_networks, include_floating, include_via_microtransit, limit, context, partner, cycle, status_format |  |  | Bundle only, no caller. |
| journeytimes | POST | https://citymapper.com/api/1/journeytimes?region_id={region_id} | rest | True | region_id | signatures, partner | poll-30s | Body {signatures: [<journey signature JSON string>]}; response order follows the request. |
| refreshjourneys | POST | https://citymapper.com/api/1/refreshjourneys?region_id={region_id} | rest | False | region_id | signatures, time_mode, region_id, partner, use_departures, status_format |  | time_mode SIGNATURE_EXACT or SIGNATURE; bundle and route table, not fired by in-app navigation. |
| trip-meta | GET | https://citymapper.com/trip/signature?signature={deflated base64}&meta_only=true | html | True | signature, meta_only |  |  | Head-tag refresh on client navigation (hackyReplacePageMeta). The signature param is the journey signature, pako-deflated and base64 encoded. |
| gettrip | GET | https://citymapper.com/api/1/gettrip?slug={slug} | rest | False | slug |  |  |  |
| createtripurl | GET | https://citymapper.com/api/1/createtripurl?signature={signature}&trip_region_id={region_id} | rest | False | signature, trip_region_id |  |  | Write despite GET: creates a public short link. |
| createshorturl | GET | https://citymapper.com/api/1/createshorturl?endcoord=&endaddress=&endname=&title=&message=&place_id= | rest | False | endcoord, endaddress, endname, title, message, place_id |  |  | Write despite GET: creates a public Meet Me Somewhere link. |
| getshorturl | GET | https://citymapper.com/api/1/getshorturl?slug={slug} | rest | False | slug |  |  |  |
| eta | POST | https://citymapper.com/api/1/eta?region_id={region_id} | rest | False | region_id | signature |  |  |
| searchpost | POST | https://citymapper.com/api/4/searchpost | rest | True |  | query, region_id, location, is_refinement, refinement_data, search_providers, powersearch, partner |  | Content-Type application/x-www-form-urlencoded with a JSON body; Citymapper-Client: Web Search; Citymapper-Region: <region_id>. |
| placeresolve | GET | https://citymapper.com/api/1/placeresolve?id={id}&region_id={region_id} | rest | False | id, region_id |  |  |  |
| geocode | GET | https://citymapper.com/geocode?lat={lat}&lng={lng} | rest | False | lat, lng |  |  |  |
| nearby3 | GET | https://citymapper.com/api/3/nearby | rest | True | brand_ids, kinds, mode_id, location, viewspan, region_id, limit, extended |  | limit-50 | brand_ids and mode_id come from the region's nearby_modes. |
| nearby2 | GET | https://citymapper.com/api/2/nearby | rest | True | brand_ids, kinds, location, viewspan, limit, region_id | accept, referer, x-requested-with | limit-50 | jQuery call on stop pages. |
| everythingmap | GET | https://citymapper.com/api/1/everythingmap?location={lat,lng}&size={size}&region_id={region_id} | rest | False | location, size, region_id |  |  |  |
| stopinfo | GET | https://citymapper.com/api/3/stopinfo?ids={alias or id}&region_id={region_id} | rest | True | ids, region_id |  |  |  |
| departures-bus | GET | https://citymapper.com/api/1/departures?headways=1&ids={stop_id}&region_id={region_id} | rest | True | headways, ids, region_id |  | poll-30s | Bus and ferry stops. |
| departures-metro | GET | https://citymapper.com/api/2/metrodepartures?headways=1&ids={station_id}&region_id={region_id} | rest | True | headways, ids, region_id |  | poll-30s | Observed in NYC and Paris. |
| departures-rail | GET | https://citymapper.com/api/1/raildepartures?headways=1&ids={station_id}&region_id={region_id} | rest | True | headways, ids, region_id |  | poll-30s |  |
| schedules | GET | https://citymapper.com/api/1/schedules?id={stop_id}&region_id={region_id}&time={time} | rest | False | id, region_id, time |  |  |  |
| routeinfo1 | GET | https://citymapper.com/api/1/routeinfo?route={alias}&region_id={region_id}&weekend=1&status_format=rich&extended=1 | rest | True | route, region_id, weekend, status_format, extended |  |  |  |
| routeinfo2 | GET | https://citymapper.com/api/2/routeinfo?route_ids={id,id}&region_id={region_id}&weekend=1&status_format=rich | rest | True | route_ids, region_id, weekend, status_format, extended |  |  |  |
| routepaths | GET | https://citymapper.com/api/1/routepaths?route_ids={ids}&region_id={region_id} | rest | False | route_ids, region_id |  |  |  |
| routestatus | GET | https://citymapper.com/api/1/routestatus?region_id={region_id}&format=rich | rest | True | region_id, format | accept, citymapper-region, content-type, referer | poll-2min |  |
| findtransport | GET | https://citymapper.com/api/2/findtransport?query={text}&region_id={region_id} | rest | True | query, region_id |  |  | Observed in your browser (URL only, body not captured). |
| vehiclelocations | GET | https://citymapper.com/api/1/vehiclelocations?route={route}&region_id={region_id} | rest | False | route, region_id |  | poll-10s |  |
| message | GET | https://citymapper.com/api/2/message?had_previous_versions=0 | rest | True | had_previous_versions | accept, citymapper-region, content-type, referer |  |  |
| weather | GET | https://citymapper.com/api/1/weather?location={lat,lng}&units={c/f}&term=now | rest | False | location, units, term |  |  |  |
| transitscore | GET | https://citymapper.com/api/1/transitscore?startcoord={lat,lng} | rest | False | startcoord |  |  |  |
| traveltime | GET | https://citymapper.com/api/1/traveltime?startcoord={lat,lng}&endcoord={lat,lng}&region_id={region_id} | rest | False | startcoord, endcoord, region_id |  |  |  |
| blog | GET | https://citymapper.com/api/1/blog[?id={id}] | rest | False | id |  |  |  |
| resources | GET | https://citymapper.com/api/1/resources?id={resource_id} | html | False | id |  |  | Linked from the footer for the terms and privacy policy. |
| city-html | GET | https://citymapper.com/{region_slug} | html | True |  |  |  | 2 MB to 15 MB of HTML; the one source of the region list. |
| cities-html | GET | https://citymapper.com/cities | html | True |  |  |  | Same window.citymapper globals; city tiles link to /{region_slug}. |
| news-html | GET | https://citymapper.com/news | html | True |  |  |  |  |
| resource-region-info | GET | https://citymapper.com/resource/region-info/{region_id} | rest | True |  |  |  | JSON region config; landing.js calls it with the cm_region cookie value. |
| resource-brand-directory | GET | https://citymapper.com/resource/brand-directory | rest | True |  |  |  | 445 KB JSON brand catalogue. |
| identity-user-data | GET | https://citymapper.com/api/1/identity/user_data | rest | True | accept, content-type, referer |  |  | 403 with an empty body while signed out (observed); user object when signed in. |
| identity-sessions-create | POST | https://citymapper.com/api/1/identity/sessions | rest | False |  | auth_provider, email, password, access_token, source_page, has_seen_marketing_opt_out, has_opted_out_of_marketing, is_interested_in_pass |  |  |
| identity-sessions-delete | DELETE | https://citymapper.com/api/1/identity/sessions | rest | False |  |  |  |  |
| identity-magiclink | POST | https://citymapper.com/api/1/identity/magiclink/create | rest | False |  | email, force_prototype, source_page, has_seen_marketing_opt_out, has_opted_out_of_marketing, is_interested_in_pass, redirect_path |  |  |
| identity-update-user | POST | https://citymapper.com/api/1/identity/update_user | rest | False |  | first_name, last_name, mobile, is_interested_in_pass |  |  |
| identity-password-reset | POST | https://citymapper.com/api/1/identity/password_reset[/{token}] | rest | False |  | email, new_password |  |  |
| identity-confirm-signup | POST | https://citymapper.com/api/1/identity/confirm_sign_up/{token} | rest | False |  |  |  |  |
| identity-places-list | GET | https://citymapper.com/api/1/identity/places | rest | False |  |  |  |  |
| identity-places-create | POST | https://citymapper.com/api/1/identity/places | rest | False |  | name, address, coords, role, place_id |  | Body is the place object; role home or work for those slots (bundle). |
| identity-places-update | PUT | https://citymapper.com/api/1/identity/places/{place_id} | rest | False |  | name, address, coords, role |  |  |
| identity-places-delete | DELETE | https://citymapper.com/api/1/identity/places/{place_id} | rest | False |  |  |  |  |
| identity-favorites-list | GET | https://citymapper.com/api/1/identity/favorites | rest | False |  |  |  |  |
| identity-favorites-create | POST | https://citymapper.com/api/1/identity/favorites | rest | False |  | target_type, target_id, region_id |  | target_type 1 bus stop, 2 station, 3 transit line (bundle). |
| identity-favorites-delete | DELETE | https://citymapper.com/api/1/identity/favorites/{favourite_id} | rest | False |  |  |  |  |
| identity-save-journey | POST | https://citymapper.com/api/1/identity/documents/SavedJourney | rest | False |  | document_data |  |  |
| identity-delete-journey | DELETE | https://citymapper.com/api/1/identity/documents/SavedJourney/{document_id} | rest | False |  |  |  |  |
| turnstile-userinfo | POST | https://turnstile-api.citymapper.com/web/1/userinfo | rest | False |  | payment_provider_id |  |  |
| turnstile-addpaymentmethod | POST | https://turnstile-api.citymapper.com/web/1/addpaymentmethod | rest | False |  | payment_method_id, payment_provider_id |  |  |
| turnstile-setdefaultpaymentmethod | POST | https://turnstile-api.citymapper.com/web/1/setdefaultpaymentmethod | rest | False |  | payment_method_id, payment_provider_id |  |  |
| turnstile-deletepaymentmethod | POST | https://turnstile-api.citymapper.com/web/1/deletepaymentmethod | rest | False |  | payment_method_id, payment_provider_id |  |  |
| turnstile-deleteallpaymentmethods | POST | https://turnstile-api.citymapper.com/web/1/deleteallpaymentmethods | rest | False |  | payment_provider_id |  |  |
| turnstile-sessionttl | GET | https://turnstile-api.citymapper.com/web/1/sessionttl | rest | False |  |  |  |  |
| city-vote | POST | https://citymapper.com/cities/vote_submit/ | rest | False |  | city_slug, email |  |  |
| logevents | POST | https://citymapper.com/api/2/logevents | rest | True |  | text/plain event lines |  | noise. Analytics. |
| resourceproxy-images | GET | https://global-api.citymapper.com/resourceproxy/{name}.png | rest | True |  |  |  | noise. City illustrations on /cities. |
| static-img | GET | https://citymapper.com/static-img?src={icon names} | rest | True |  |  |  | noise. Route icons. |

## Entities

| Entity | Description | Fields | Ids | Sources |
|---|---|---|---|---|
| region | A supported metro area; the unit every API call is scoped by | region_id, region_name, region_slug, region_name_aliases, bounding_box, default_place, timezone, web_enabled, api_enabled, nearby_modes, core_brand_ids, distance_units | region_id, region_slug | city-html, resource-region-info |
| city | A city inside a region (252) | city_id, city_name, city_slug, region_id, default_place, show_in_city_switcher | city_id, city_slug | city-html |
| nearby-mode | A mode tile for nearby searches in a region | mode_id, mode_slug, short_title, kind_ids, request_brand_ids, priority_brand_ids, mode_type | mode_id | city-html, resource-region-info |
| brand | A transport operator or network | brand_id, name, departure_apis, affinities | brand_id | city-html, resource-brand-directory |
| place | A search result: station, stop, address or Google place | id, name, address, coords, type, result_type, source, brands, lines | id | searchpost, placeresolve, geocode |
| journey | One planned option | duration_seconds, walk_seconds, distance_meters, calories, legs, signature, formatted_price, price_amount, currency_code, journey_equivalence_hash, profile_id, journey_kind | signature, journey_equivalence_hash | journeys, walk7, cycle, taxi, refreshjourneys |
| leg | A part of a journey | mode, routes, stops, shape, frequency, departure_time, arrival_time, pattern_ids, distance, duration |  | journeys |
| journey-time | Live timing for a journey signature | time, time_mode, leg_times, formatted_price, traffic_level, request_signature | request_signature | journeytimes |
| nearby-element | A stop, station, pier or dock near a point | id, name, coords, kind, alias, brand_ids, route_ids, route_names, bearing, walk_time_seconds, cycles_available, cycles_spaces, cycles_electric_available | id, alias | nearby3, nearby2 |
| stop | A stop or station with routes and exits | id, alias, name, coords, route_ids, brand_ids, exits, sharing_urls | id, alias | stopinfo |
| departure | A live or scheduled departure | route_id, destination_name, headsign, time_seconds, scheduled_time, expected_departure_time, live_departures_seconds, is_live, platform_number, pattern_id, direction_id |  | departures-bus, departures-metro, departures-rail |
| route | A line | id, name, long_name, brand, mode, color, aliases, live_line_code, status, patterns, url | id, aliases | routeinfo1, routeinfo2, routestatus, findtransport |
| pattern | A branch or direction of a line | id, name, pattern_type, path, stop_points | id | routeinfo1 |
| route-status | A line's current service level | level, summary, description, replacements, disruptions |  | routestatus, routeinfo1, routeinfo2 |
| disruption | One disruption on a line | level, summary, description, replacements, stops |  | routestatus |
| vehicle | A live vehicle position on a line (bundle) | inferred |  | vehiclelocations |
| message | Site-wide notice | messages |  | message |
| go-link | A Meet Me Somewhere short link | url, endcoord, endname, endaddress, title, message | slug | createshorturl, getshorturl |
| news-post | A news article | id, slug, title | id | news-html, blog |
| user | The signed-in user (bundle) | id, email, first_name, last_name, mobile, is_interested_in_pass, has_seen_marketing_opt_out, has_opted_out_of_marketing | id | identity-user-data |
| saved-place | A saved place (bundle) | place_id, name, address, coords, role | place_id | identity-places-list |
| favourite | A favourite stop, station or line (bundle) | id, target_type, target_id, region_id | id | identity-favorites-list |
| saved-journey | A journey sent to the phone (bundle) | document_id, document_data | document_id | identity-save-journey |
| payment-method | A Citymapper Pass payment method (bundle) | payment_method_id, payment_provider_id | payment_method_id | turnstile-userinfo |

## Auth and session

- **mechanism**: cookie-session (Django sessionid), optional; every public read works signed out
- **cookie_names**: sessionid, csrftoken, uid, uid_set, cm_region, _locale, __cf_bm
- **header_names**: Citymapper-Region, Citymapper-Client, User-Device, Session-Id (turnstile only), X-CSRFToken (city vote only)
- **csrf**: A csrftoken cookie is set on first visit, but the bundle sends X-CSRFToken only on the uncalled city vote; identity writes send none (unknown whether the server enforces it)
- **login_flow**: E-mail magic link (POST identity/magiclink/create), Google Identity Services access token or Facebook SDK token posted to identity/sessions; no password form in the UI; no Apple sign-in
- **session_lifetime**: unknown; you are signed out
- **refresh**: none observed; a signed-out session answers 403 on identity/user_data

## Pagination and time windows

| Scheme | Kind | Request keys | Response keys | Terminator | Page size |
|---|---|---|---|---|---|
| time-window-journeys | none | departure_time, arrival_time, limit | sections, journeys | one response per query; a later window is a new query with a later departure_time | None |
| poll-30s | none | ids, headways | time_seconds, scheduled_time, live_departures_seconds, last_updated_time | the response is the next departures window (about 30 to 60 minutes); the UI re-polls every 30 s | None |
| poll-2min | none | region_id | last_updated_time | single snapshot; the UI refetches every 2 minutes | None |
| poll-10s | none | route |  | single snapshot; the UI refetches every 10 s (bundle) | None |
| limit-50 | offset-limit | limit, location, viewspan | elements, bounding_box | fewer than limit elements, or move the location; no offset or cursor exists | 50 |

## Caveats

| Kind | Severity | Detail | Evidence |
|---|---|---|---|
| anti-bot | medium | Cloudflare fronts the site and sets __cf_bm. No challenge appeared for your browser, a separate CDP Brave profile or plain curl; behaviour at higher rates is untested. | response headers server: cloudflare, cf-ray, set-cookie __cf_bm (curl and CDP captures 2026-10-10) |
| rate-limit | medium | No rate-limit headers (x-ratelimit-*, retry-after) on any API response; thresholds unknown. Pace at 3 s or more per request. | response headers in var/captures/run-2026-10-10-082844-*.jsonl list only cf-cache-status and x-version |
| signing | low | No request signing or nonce. The journey 'signature' is a JSON journey descriptor returned by the planner; /trip/signature?signature= carries it pako-deflated and base64 encoded. | journeys[].signature is a 900-character JSON string; bundle route table (research/bundle/api-inventory.md) |
| csrf | medium | Identity writes (places, favourites, saved journeys) send no CSRF header from the web client; whether the server enforces csrftoken is unknown until a signed-in write is tried. | api-inventory.md section (b) Auth |
| other | high | Web account exists but you are signed out on citymapper.com, and signing in may create an account (magic link, Google or Facebook). Account reads and writes cannot be verified until you sign in yourself. | GET /api/1/identity/user_data 403 in your browser; login dialog shows e-mail, Facebook, Google |
| other | high | Citymapper Club and Pass are paid features; Pass payment methods live on turnstile-api.citymapper.com and need a Session-Id the web pages never expose. App-only on the web. | bundle turnstile methods with no caller; news posts on Club features |
| other | medium | Share and Meet Me Somewhere links (createtripurl, createshorturl) are GET requests that create public URLs; they are writes visible to others. | bundle create-links.js; trip-share.js calls it on mount of the share block |
| feature-flag | medium | 8 regions have api_enabled false (fr-nantes, fr-bordeaux, fr-toulouse, fr-strasbourg, fr-marseille, ch-ch, mc-monaco, at-vienna); routing there may be absent or partial. Coordinates outside a region's bounding box are rejected client side as out of bounds. | window.citymapper.regions in the /nyc HTML; journey-results toggleOutOfBounds |
| realtime | low | No websockets or SSE. Live data is polled: departures and journey times every 30 s, line status every 2 minutes, vehicles every 10 s. | CDP captures report 0 websocket frames; bundle timers |
| other | medium | Region config and the city list exist only inside 2 to 15 MB server-rendered HTML pages (or /resource/region-info per region); reading the city list costs one large page load, so it should be cached. | city-paris 4.8 MB, nearby-paris-metro 15 MB, city-london 8 MB in capture logs |
| other | low | Embedded Google Maps browser key (39 characters) and Google and Facebook client ids in the bundle; only used for map tiles and social sign-in, never needed by the program. | bundle constants GOOGLE_MAPS_API_KEY, GOOGLE_KEY, FACEBOOK_APP_ID (names and lengths only) |
| terms | medium | This is the website's private API, not the official developer API; the terms of service link is /api/1/resources?id=citymapper-terms-of-service. | footer link |
| other | low | Bike docks have no detail page (404); dock availability comes from nearby results only. | GET /nyc/bike/docks/CitiBike_904930bd-... 404 (capture stop-nyc-bike) |
| other | low | The web client's delete-place call passes placeId where place_id is required, so the web UI cannot remove a saved place; the program must send place_id itself. | bundle user-actions.js removePlace (api-inventory.md) |

## Open questions

- Account surface (user_data, places, favourites, saved journeys, update_user) is mapped from the bundle only: response shapes and CSRF enforcement need one signed-in session, which only you can create.
- vehiclelocations was not fired on any line page walked (live_availability 0 on NYC 6, M15, London Bakerloo); which regions have live vehicles is unknown.
- refreshjourneys, gettrip, getshorturl, eta, placeresolve, geocode, schedules, routepaths, everythingmap, weather, transitscore, traveltime, vehiclehire, walk v1 and blog are defined in the bundle but were not observed live; the engineer stage replays them once each.
- Response bodies of findtransport were not captured (seen by URL in your browser only).
- How far ahead departure_time may be set, and whether past times are accepted, is untested.
- Brand planner pages (/{region}/planner/{brand}) were not visited; valid brand slugs are unknown.
