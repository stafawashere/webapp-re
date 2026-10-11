# Citymapper web API inventory

Source: `bundle.js` (/webapp React app, release v749.0.0) and `landing.js`, read offline. Every claim below is backed by an `evidence` snippet in `api-inventory.json`, checked verbatim against the bundle by the generator script. Anything marked "inferred" is not proven by code.

68 entries: 61 methods registered on `CitymapperAPI`, of which 33 have a caller in either bundle, plus 7 direct calls or URL contracts that bypass the class.

## How requests are built

`src/api/api.js` creates the only instance as `new CitymapperAPI({errorHandler, hostname: ""})`. The class defaults are hostname `https://citymapper.com`, prefix `/api`, turnstileHostname `https://turnstile-api.citymapper.com`, stagingTurnstileHostname `https://turnstile-staging-api.citymapper.com`, turnstilePrefix `/web`. With hostname `""` every resource is a same-origin relative path, `/api/<version>/<name>`. The one exception is `cityvote`, built on `prefix("")`, so it is `/cities/vote_submit/`. Templates come from url-assembler (`template`, `query`, `param`, `segment`); undefined query values are left out (inferred from the library, and `toString` is patched to drop a bare `?`).

Every call goes through `http.proxy`: `fetch(url, {method, credentials: "include", headers: {...headers, "Content-Type": contentType}, body})`. Content-Type defaults to `application/json; charset=utf-8` and is set even on GET. The body is `JSON.stringify(body)` unless the content type is `text/plain`, so `searchpost` sends JSON text under a form-urlencoded content type. A status of 400 or more rejects with `{url, status, statusText, body}`.

`_request` merges `this._staticHeaders` over the per-call headers. In the browser `_staticHeaders` is `{}`. During Next.js SSR, `with-initial-props.js` re-initialises the instance with hostname `SSR_API_HOST` or `https://<request host>` and static headers `Cookie: sessionid=<request cookie>`, `User-Agent` and `X-Forwarded-For` copied from the incoming request.

`http.get(url, params, options)` drops `options` whenever `params` is truthy. Methods that pass `null` keep their headers (routestatus, message, blog). `getTransport` passes a params object, and `turnstileGetSessionTimeRemaining` passes `{}`, which loses its `User-Device` and `Session-Id` headers.

The error handler ignores 403 from `/api/1/identity/*` (signed out) and 503, or 404 with body.error `NO_CYCLE_ROUTES_AVAILABLE`, from `/api/6/cycle`. Everything else goes to Sentry.

## Inventory

| Name | Method | URL | Required params | Auth | Mutates | Called by |
|---|---|---|---|---|---|---|
| getAllJourneys | GET | `/api/7/journeys` | start, end, status_format | none | no | containers/journey-results/results-page.js fetch() on mount and when start/end/time change on /directions, /:r (+1 more) |
| getWalkJourneys | GET | `/api/1/walk` | start, end, status_format | none | no | no caller found |
| getWalk7Journeys | GET | `/api/7/walk` | start, end, status_format | none | no | results-page fetch() with limit 2; journey-page componentDidUpdate when highlighted journey is walkable |
| getCycleJourneys | GET | `/api/6/cycle` | start, end, status_format | none | no | results-page fetch(); journey-page when highlighted journey_kind matches /cycle/ |
| getTaxiJourneys | GET | `/api/2/taxi` | start, end, status_format | none | no | results-page fetch() unless planner.skipTaxi |
| getVehicleHireJourneys | GET | `/api/7/vehiclehire` | start, end, status_format | none | no | no caller found |
| refreshJourney | POST | `/api/1/refreshjourneys?region_id={regionId}` | region_id, signatures, time_mode, region_id, status_format | none | no | containers/journey-detail/journey-page.js refreshJourney(): on mount for /trip/signature?signature=<hashified> (+1 more) |
| getTrip | GET | `/api/1/gettrip?slug={slug}` | slug | none | no | journey-page componentDidMount when route is /trip/:slug |
| getJourneyTimes | POST | `/api/1/journeytimes?region_id={region_id}` | signatures | none | no | results-page fetchAccurate(): all result signatures, every 30s, retry every 1s while no results, max 10 rounds (+2 more) |
| getStopInfo | GET | `/api/3/stopinfo?ids={stopId}&region_id={regionId}` | ids, region_id | none | no | containers/stop-station-page.js refresh() on mount and when :alias changes (route /:region_slug/:mode/:stopTyp |
| getDepartures | GET | `/api/1/departures  or  /api/2/metrodepartures  or  /api/1/raildepartures  ?headways=1&ids={stopId}&region_id={regionId}` | headways, ids, region_id | none | no | containers/stop-station-page.js fetchLiveTimes() after getStopInfo, brand taken from window.citymapper.brands[ |
| getSchedules | GET | `/api/1/schedules?id={stopId}&region_id={regionId}&time={time}` | id, region_id | none | no | no caller found |
| getNearby | GET | `/api/3/nearby` | location | none | no | containers/nearby-page/index.js fetch() on mount and on map pan (route /:region_slug/:mode/:stopType with stop (+1 more) |
| getEverything | GET | `/api/1/everythingmap?location={lat,lng}&size={size}&region_id={regionId}` | location, size | none | no | no caller found |
| getSearchResults | POST | `/api/4/searchpost` | query, region_id | none | no | components/search/search.js fetchResults (debounced 300ms) on typing in the start/end/place search box, when t |
| getTransport | GET | `/api/2/findtransport?query={query}&region_id={regionId}` | query, region_id | none | no | components/search/search.js fetchResults when the search box has transportSearch (line/stop search) |
| resolvePlace | GET | `/api/1/placeresolve?id={id}&region_id={region_id}` | id, region_id | none | no | components/search/search.js handleResultSelected when a picked result has an id but no coords |
| getRouteInfo | GET | `/api/1/routeinfo?route={route}&region_id=&weekend=&status_format=&extended=  or  /api/2/routeinfo?route_ids={id,id}&region_id=&weekend=&status_format=&extended=` | region_id | none | no | components/lines-card/fetch-status-enhancer.js for saved lines missing from region status (+5 more) |
| getRoutePaths | GET | `/api/1/routepaths?route_ids={ids}&region_id={regionId}` | route_ids, region_id | none | no | no caller found |
| getRouteStatus | GET | `/api/1/routestatus?region_id={region_id}&format={format}` | region_id | none | no | containers/status-page/index.js (/:region_slug/status) and lines-card fetch-status-enhancer (+2 more) |
| getVehicleLocations | GET | `/api/1/vehiclelocations?route={route}&region_id={region_id}` | route, region_id | none | no | containers/line-page/line-page.js fetchVehicles() after route info loads |
| getMessage | GET | `/api/2/message?had_previous_versions=0` | had_previous_versions | none | no | components/god-message/god-message.js componentDidMount once per session (godMessages.fetched) |
| getBlogPosts | GET | `/api/1/blog[?id={id}]` | none | none | no | no caller found |
| getWeather | GET | `/api/1/weather?location={lat,lng}&units={c or f}&term={now}` | location | none | no | no caller found |
| getTransitScore | GET | `/api/1/transitscore?startcoord={lat,lng}` | startcoord | none | no | no caller found |
| getETA | POST | `/api/1/eta?region_id={region_id}` | region_id, signature | none | no | no caller found |
| createGoLink | GET | `/api/1/createshorturl?endcoord=&endaddress=&endname=&title=&message=&place_id=` | endcoord, endname, title, message, place_id | none | yes | components/golink-card/golink-card.js handleClick ('Meet me somewhere' card on the city home page), then navig |
| createTripLink | GET | `/api/1/createtripurl?signature={signature}&trip_region_id={region_id}` | signature, trip_region_id | none | yes | containers/journey-detail/trip-share.js componentDidMount (share block on the journey detail page) |
| getShortURL | GET | `/api/1/getshorturl?slug={slug}` | slug | none | no | containers/go-page/go-page.js fetchData() on mount |
| logEvents | POST | `/api/2/logevents` | (text/plain body) | none (uid in User-Device) | yes | analytics/providers/redshift.js flush(): batched with a 2s debounce, also on window.onbeforeunload; events fro |
| cityVote | POST | `/cities/vote_submit/` | city_slug, email | X-CSRFToken + cookie | yes | no caller found |
| getUserData | GET | `/api/1/identity/user_data` | none | sessionid cookie | no | index.js on every /webapp boot; enhancers/with-initial-props.js on the client after SSR hydration; landing-pag (+1 more) |
| logUserIn | POST | `/api/1/identity/sessions` | auth_provider | none | yes | components/login/login.js loginWithGoogleCallback (Google Identity Services token client) and loginWithFaceboo |
| logUserOut | DELETE | `/api/1/identity/sessions` | none | sessionid cookie | yes | components/login/login-logout-button.js logout (header button) via user-actions logUserOut |
| signUserUp | POST | `/api/1/identity/signup` | auth_provider | none | yes | no caller found |
| sendMagicLink | POST | `/api/1/identity/magiclink/create` | email | none | yes | components/login/login.js signupOrLogin (email form submit, 'Sign up or log in') |
| confirmEmailAddress | POST | `/api/1/identity/confirm_sign_up/{token}` | none | none | yes | no caller found |
| resetPasswordForEmail | POST | `/api/1/identity/password_reset` | none | none | yes | no caller found |
| setNewPasswordForEmail | POST | `/api/1/identity/password_reset/{token}` | none | none | yes | no caller found |
| updateUser | POST | `/api/1/identity/update_user` | none | sessionid cookie | yes | no caller found |
| getUserPlaces | GET | `/api/1/identity/places` | none | sessionid cookie | no | user-actions syncUserData after login and after every place save/remove |
| saveUserPlace | POST | `/api/1/identity/places` | (place object) | sessionid cookie | yes | components/save/save-button.js toggleSave (star on a place) via user-actions savePlace |
| updateUserPlace | PUT | `/api/1/identity/places/{place_id}` | (place minus place_id) | sessionid cookie | yes | no caller found |
| delUserPlace | DELETE | `/api/1/identity/places/{place_id}` | none | sessionid cookie | yes | components/save/save-button.js toggleSave via user-actions removePlace |
| getUserFavourites | GET | `/api/1/identity/favorites` | none | sessionid cookie | no | user-actions syncUserData |
| saveUserFavourite | POST | `/api/1/identity/favorites` | (favourite object) | sessionid cookie | yes | components/save/save-button.js on stop, station and line pages, via user-actions saveFavorite |
| delUserFavourite | DELETE | `/api/1/identity/favorites/{favouriteId}` | none | sessionid cookie | yes | components/save/save-button.js via user-actions removeFavorite (favorite_id) |
| saveUserJourney | POST | `/api/1/identity/documents/SavedJourney` | document_data | sessionid cookie | yes | components/save/send-to-phone-button.js ('Send to phone' on journey detail) via user-actions saveJourney |
| delUserJourney | DELETE | `/api/1/identity/documents/SavedJourney/{document_id}` | none | sessionid cookie | yes | send-to-phone-button unsave via user-actions unsaveJourney |
| turnstileGetUserInfo | POST | `https://turnstile-api.citymapper.com/web/1/userinfo` | payment_provider_id | User-Device + Session-Id headers | no | no caller found |
| stagingTurnstileGetUserInfo | POST | `https://turnstile-staging-api.citymapper.com/web/1/userinfo` | payment_provider_id | User-Device + Session-Id headers | no | no caller found |
| turnstileAddPaymentMethod | POST | `https://turnstile-api.citymapper.com/web/1/addpaymentmethod` | payment_method_id, payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| stagingTurnstileAddPaymentMethod | POST | `https://turnstile-staging-api.citymapper.com/web/1/addpaymentmethod` | payment_method_id, payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| turnstileSetDefaultPaymentMethod | POST | `https://turnstile-api.citymapper.com/web/1/setdefaultpaymentmethod` | payment_method_id, payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| stagingTurnstileSetDefaultPaymentMethod | POST | `https://turnstile-staging-api.citymapper.com/web/1/setdefaultpaymentmethod` | payment_method_id, payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| turnstileDeletePaymentMethod | POST | `https://turnstile-api.citymapper.com/web/1/deletepaymentmethod` | payment_method_id, payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| stagingTurnstileDeletePaymentMethod | POST | `https://turnstile-staging-api.citymapper.com/web/1/deletepaymentmethod` | payment_method_id, payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| turnstileDeleteAllPaymentMethods | POST | `https://turnstile-api.citymapper.com/web/1/deleteallpaymentmethods` | payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| stagingTurnstileDeleteAllPaymentMethods | POST | `https://turnstile-staging-api.citymapper.com/web/1/deleteallpaymentmethods` | payment_provider_id | User-Device + Session-Id headers | yes | no caller found |
| turnstileGetSessionTimeRemaining | GET | `https://turnstile-api.citymapper.com/web/1/sessionttl` | none | User-Device + Session-Id headers | no | no caller found |
| stagingTurnstileGetSessionTimeRemaining | GET | `https://turnstile-staging-api.citymapper.com/web/1/sessionttl` | none | User-Device + Session-Id headers | no | no caller found |
| nearby-util.makeApiCall (direct jQuery) | GET | `/api/2/nearby?brand_ids= or kinds=&location=lat,lng[&viewspan=]&limit=&region_id=` | location, limit, region_id | none | no | containers/stop-station-page.js: nearby stops list after getStopInfo (brandIds, limit 50) (+1 more) |
| place.makeTravelTimeRequest (direct jQuery) | GET | `/api/1/traveltime?startcoord=lat,lng&endcoord=lat,lng&region_id=` | startcoord, endcoord, region_id | none | no | no caller found |
| geocode (direct fetch) | GET | `/geocode?lat={lat}&lng={lng}` | lat, lng | none | no | setUserLocationFromBrowser ('current location' in GMS form, go page, golink card) (+1 more) |
| hackyReplacePageMeta (direct fetch) | GET | `{current pathname}?{current query}&meta_only=true` | meta_only | none | no | index.js history.listen: every client-side route change |
| directions link (navigation, not XHR) | GET (page navigation) | `/directions?startcoord=&endcoord=&startname=&endname=&startaddress=&endaddress=&departure_time= or arrival_time=` | none | none | no | no caller found |
| landing region-info (direct fetch, landing.js only) | GET | `/resource/region-info/{cm_region cookie or uk-london}` | none | none | no | landing.js boot; on failure retries with uk-london, then falls back to {} |
| landing brand-directory (direct fetch, landing.js only) | GET | `/resource/brand-directory` | none | none | no | landing.js boot, in parallel with region-info |

Full per-entry detail (optional params, shapes, headers, response fields, refresh timing, evidence) is in `api-inventory.json`.

## (a) Router and page routes

The /webapp client is a react-router tree in `src/app.js`, mounted by `src/index.js` into `#content`. The same code also runs inside a Next.js shell (`__NEXT_DATA__`, `x-nextjs-data`), where `with-initial-props.js` builds the store server side. `src/uri-config.js` holds the URL list in two groups: `django` templates (server pages) and `ssr` templates (Next pages listed in `SSR_PAGES`). `NON_BUNDLE_PAGE` marks routes that this bundle does not render.

| Route (uri-config name) | Component | What it fetches |
|---|---|---|
| `/directions`, `/:region_slug/directions` (directions, cityInRegionDirections) | JRContainer, results-page.js | On mount and on query change: `/api/7/journeys`, `/api/7/walk` (limit 2), `/api/6/cycle`, `/api/2/taxi` in parallel, then `/api/1/journeytimes` every 30s up to 10 times. `/geocode` for unnamed endpoints. Query contract: see the "directions link" entry. |
| `/webapp`, `/:region_slug/webapp` (webapp, cityInRegionWebapp) | JRContainer | Same as directions. |
| `/webapp/new` (webappNew) | not in the react-router tree | `ssr` template only; rendered by the Next app, not by this bundle (inferred). |
| `/:region_slug/planner/:brand` (brandPlanner) | JRContainer with planner options | `loadBrandNetwork`: `/api/1/routestatus`, `/api/1/routeinfo?extended=1` per brand line, `/api/3/nearby` (limit 500, viewspan from region bounding box). Journeys sent with `partner=<brand with - replaced by _>`, taxi skipped. |
| `/trip/signature`, `/:region_slug/trip/signature`, `/:region_slug/planner/:brand/trip/signature` (tripSig, cityInRegionTripSig, brandPlannerTripSig) | JDContainer, journey-page.js | `?signature=` is pako-deflated, base64 signature; decoded then `POST /api/1/refreshjourneys` (exact false), then `/api/1/journeytimes` every 30s, max 10. Lazy `/api/7/walk` and `/api/6/cycle`. Share block calls `/api/1/createtripurl`. |
| `/trip/:slug` (tripSlug) | journey-page.js | `/api/1/gettrip?slug=` then the same refresh flow. |
| `/go/:slug`, `/widget/:slug` (go, widget) | go-page.js | `/api/1/getshorturl?slug=`. |
| `/:region_slug/status` (status) | containers/status-page | `/api/1/routestatus` (header Citymapper-Region), refetched every 2 minutes; strike map then calls `/api/2/routeinfo?route_ids=`. |
| `/:region_slug/:mode/:id` (line) | NearbyOrLine: line-page.js when `:id` is not a nearby stop-type slug | `/api/1/routeinfo?route=&extended=1`, then `/api/1/vehiclelocations` with a 10s timer. |
| `/:region_slug/:mode/:stopType` (nearby; stopType is a plural like stops, stations, docks, piers, plus the region's `mode_web_slug_extra` values) | nearby-page/index.js | `/api/3/nearby` (limit 50, brand_ids or kinds, mode_id), refetched on map pan; `/api/2/routeinfo` for featured routes. |
| `/:region_slug/:mode/:stopType/:alias` (stopStation) | stop-station-page.js | `/api/3/stopinfo?ids=<alias>`, then departures via the brand's `departure_apis` (`/api/1/departures`, `/api/2/metrodepartures` or `/api/1/raildepartures`) every 30s, and `/api/2/nearby` (jQuery, limit 50). |
| `/:region_slug` (home) | home-page.js | God message `/api/2/message`, lines card (`/api/1/routestatus` plus `/api/1/routeinfo` for saved lines not in status), strike map (`/api/2/routeinfo?route_ids=`), golink card (`/api/1/createshorturl` on click). Component-to-card mapping partly inferred from minified names. |
| `/cities` | CitiesPageWithHeaderAndFooter | Static list plus `window.citymapper.regions`; clicking a city writes the `cm_region` cookie and reloads. |
| `/router`, `/superrouter`, `/:region_slug/router`, `/:region_slug/superrouter` | redirect | Redirect to `/directions`. |

Every page boot: `GET /api/1/identity/user_data`; on success `syncUserData` fetches `/api/1/identity/places`, `/api/1/identity/favorites`, `/api/1/identity/user_data` again and `/api/1/routestatus`. Every client-side navigation: `GET <path>?<query>&meta_only=true` for head tags, and a `pageView` analytics event batched to `POST /api/2/logevents`.

Server-only routes named in uri-config but not rendered here: `/news`, `/news/:id[/:slug]`, `/:region_slug/news`, `/eta/:slug`, `/pass`, `/pass/:slug`, `/account-deletion/:token`, `/authorise/:reference`, `/p/reset_password`, `/signup/:token/confirm`, `/reset/:token/continue`, `/ride`, `/ride/:slug`, `/contact[/:slug]`, `/tools/:id/:slug`, `/company`, `/jobs`, `/api`, `/powers`, `/enterprise`, `/love`, `/meet`, `/simple`, `/tinyhome`. Their API use (blog, eta, confirm_sign_up, password_reset, update_user, turnstile) is defined in the client but has no caller in these two bundles, so those pages most likely call it server side (inferred).

## (b) Auth

Session: Django-style cookie `sessionid` (`SESSION_COOKIE` in `constants/storage-keys.js`). The browser sends it because every fetch uses `credentials: "include"`. The SSR path forwards it as an explicit `Cookie` header. Signed-in state is detected only by `GET /api/1/identity/user_data` succeeding; 403 means signed out.

Login options in `components/login/login.js`:

1. Email magic link: `POST /api/1/identity/magiclink/create` with email, source_page, is_interested_in_pass, redirect_path. The email link returns with `?ls=<base64 email>`, which `login-logout-button.js` decodes with `atob` to show "Logged in as". Hash `#login` opens the login modal.
2. Google: Google Identity Services `initTokenClient` with scope `userinfo.email`; the returned access_token goes to `POST /api/1/identity/sessions` with `auth_provider: "google"`. Client id constant `GOOGLE_KEY` (72 chars, value not copied).
3. Facebook: FB JS SDK v2.5 `FB.login`, then the access token to `POST /api/1/identity/sessions` with `auth_provider: "facebook"`. App id constant `FACEBOOK_APP_ID` (15 chars, value not copied).
4. Email + password (`auth_provider: "emailpassword"`) and `signup` exist in the API layer but the web UI never calls them.

There is no Apple sign-in anywhere in either bundle. `login-providers.js` only contains `facebookLogin`.

Logout: `DELETE /api/1/identity/sessions`.

CSRF: the only CSRF handling is `cityVote`, which sends `X-CSRFToken` from a `csrfToken` argument. Nothing in either bundle reads a `csrftoken` cookie or a `csrfmiddlewaretoken` field, and the identity POST, PUT and DELETE calls send no CSRF header. Either the API views are CSRF-exempt or CSRF is enforced by Content-Type/origin; unknown.

Other identifiers: cookie `uid` (device id) is read for analytics and sent as `User-Device` on `/api/2/logevents`; `NO_UID` when absent. Turnstile calls take `uid` and `sessionid` as explicit arguments and send them as `User-Device` and `Session-Id`.

Signed-in features in the web client:

- Saved places (`/api/1/identity/places`): list, save (star button), update (PUT, unused), delete. Home and work come from `role`. Delete from the web is broken: `removePlace` passes `placeId` but the method requires `place_id`, so the invariant throws before any request (inferred from code).
- Favourites (`/api/1/identity/favorites`): stops, stations and lines (target_type 1 bus stop, 2 station, 3 transit line). Saved lines feed the lines card status.
- Saved journeys ("Send to phone"): `POST /api/1/identity/documents/SavedJourney` with `document_data` JSON, delete by document_id. No list call exists, so saved journeys are only known within the session.
- `update_user` accepts first_name, last_name, mobile, is_interested_in_pass; email cannot be changed. No caller in the web bundles.
- User object fields used: id, email, first_name, is_interested_in_pass, has_seen_marketing_opt_out, has_opted_out_of_marketing (from the reducer's initial state; server fields beyond these unknown).

## (c) Region and city handling

The /webapp bundle never fetches region config over XHR. The server inlines it as `window.citymapper` (`region`, `regionId`, `brands`, `cityMeta`, `regions`, `next_cities`, `landingpage`, `static_config_localization`, `STACK`, `isStaging`, `httpReferer`), or, under Next SSR, as `__NEXT_DATA__.props.pageProps.initStoreState` built from `req._staticConfig` (region, landingPage, brands, cityMeta, hackneyCoverage, partner_apps, next_cities, staticConfigLocalization).

`region_id` for API calls is always `store.region.region_id`. Region fields the client reads: region_id, region_slug, region_name, region_name_localization_key, nearby_modes (mode_slug, mode_id, request_brand_ids, priority_brand_ids, kind_ids), bounding_box and core_bounding_box (southwest_corner_coords, northeast_corner_coords), default_place.coords, region_default_languages. Brands are keyed by brand id and carry `departure_apis`, which picks the departures endpoint.

The server picks the region from the URL `:region_slug` or the `cm_region` cookie (inferred for the server side). The city switcher writes `cm_region=<region id>` with js-cookie and reloads; `REGION_QUERY` `set_region` and `LANG_QUERY` `lang` exist as constants, and only `lang` is used client side. Locale is stored in cookie `_locale` (Path=/, SameSite=None; Secure; Partitioned on https).

Brand network: `actions/brand-network-actions.js` `loadBrandNetwork` (planner pages) caches per brand in the store and builds the network from routestatus, routeinfo (extended) and nearby (limit 500). There is no dedicated "regions" endpoint in the client.

Supported cities, static fallback list in `components/city-switcher/Cities.js` (109 entries, 105 distinct region ids; several cities share a region id), merged at runtime with `window.citymapper.regions`:

**Europe (71):** uk-london /london (London), uk-manchester /manchester (Manchester), uk-manchester /manchester (Liverpool), uk-birmingham /birmingham (Birmingham), uk-edinburgh /edinburgh (Edinburgh), uk-edinburgh /edinburgh (Glasgow), uk-birmingham /birmingham (Nottingham), uk-bristol /bristol (Cardiff), uk-bristol /bristol (Bristol), uk-newcastle /newcastle (Newcastle), ie-dublin /dublin (Dublin), fr-paris /paris (Paris), fr-lyon /lyon (Lyon), fr-marseille /marseille (Marseille), fr-toulouse /toulouse (Toulouse), fr-lille /lille (Lille), fr-bordeaux /bordeaux (Bordeaux), fr-strasbourg /strasbourg (Strasbourg), fr-nantes /nantes (Nantes), be-brussels /brussels (Belgium), nl-randstad /randstad (The Netherlands), lu-luxembourg /luxembourg (Luxembourg), de-berlin /berlin (Berlin), de-hamburg /hamburg (Hamburg), de-munich /munich (Munich), de-frankfurt /frankfurt (Frankfurt), de-rhineruhr /rhineruhr (Cologne & Dortmund), de-lowersaxony /lowersaxony (Bremen & Hanover), de-nuremberg /nuremberg (Nuremberg), de-stuttgart /stuttgart (Stuttgart), it-rome /roma (Rome), it-milan /milano (Milan), it-naples /naples (Naples), it-turin /turin (Turin), it-genova /genoa (Genoa), it-florence /florence (Florence), it-bologna /bologna (Bologna), it-venice /venezia (Venice), es-madrid /madrid (Madrid), es-barcelona /barcelona (Barcelona), es-basquecountry /basquecountry (Basque Country), es-valencia /valencia (Valencia), es-seville /seville (Seville), es-zaragoza /zaragoza (Zaragoza), es-malaga /malaga (Malaga), es-granada /granada (Granada), es-balearics /balearics (Balearic Islands), pt-lisbon /lisboa (Lisbon), gr-athens /athens (Athens), se-stockholm /stockholm (Stockholm), dk-copenhagen /copenhagen (Copenhagen), no-oslo /oslo (Oslo), fi-helsinki /helsinki (Helsinki), is-iceland /reykjavik (Reykjavik), lv-latvia /riga (Riga), lt-lithuania /lithuania (Vilnius), ee-estonia /tallinn (Tallinn), cz-prague /prague (Prague), hu-budapest /budapest (Budapest), at-vienna /vienna (Vienna), ch-ch /switzerland (Switzerland), pl-warsaw /warsaw (Warsaw), pl-krakow /krakow (Krakow), sk-bratislava /bratislava (Bratislava), hr-zagreb /zagreb (Zagreb), ro-bucharest /bucharest (Bucharest), rs-belgrade /belgrade (Belgrade), mc-monaco /monaco (Monaco), ru-moscow /moscow (Moscow), ru-stpetersburg /sanktpeterburg (St. Petersburg), tr-istanbul /istanbul (Istanbul).

**US & Canada (28):** us-nyc /nyc (New York), us-dc /dc (DC & Baltimore), us-detroit /detroit (Detroit), us-la /la (Los Angeles & San Diego), us-sf /sfbayarea (SF Bay Area), us-chicago /chicago (Chicago), us-philadelphia /philadelphia (Philadelphia), us-boston /boston (Boston), us-miami /miami (Miami), us-stlouis /stlouis (St. Louis), us-atlanta /atlanta (Atlanta), us-dallas /dallas (Dallas), us-houston /houston (Houston), us-austin /austin (Austin), us-pittsburgh /pittsburgh (Pittsburgh), us-cleveland /cleveland (Cleveland), us-minneapolis /twincities (Minneapolis), us-seattle /seattle (Seattle), us-denver /denver (Denver), us-saltlakecity /saltlakecity (Salt Lake City), us-portland /portland (Portland), us-sanantonio /sanantonio (San Antonio), us-lasvegas /lasvegas (Las Vegas), us-phoenix /phoenix (Phoenix), us-honolulu /honolulu (Honolulu), ca-toronto /toronto (Toronto), ca-montreal /montreal (Montreal), ca-vancouver /vancouver (Vancouver).

**Asia and ROW (10):** hk-hongkong /hong-kong (Hong Kong), sg-singapore /singapore (Singapore), kr-seoul /seoul (Seoul), jp-tokyo /tokyo (Tokyo), tw-taiwan /taiwan (Taiwan\n              ), au-sydney /sydney (Sydney), au-melbourne /melbourne (Melbourne), br-saopaulo /sao-paulo (Sao Paulo), mx-df /df (Mexico City), ae-ae /united-arab-emirates (United Arab Emirates).

## (d) Signing, nonces, rate limits, bot checks, app-only features

- No request signing, HMAC, nonce or computed header exists in either bundle. The only `nonce` hits are Next.js script tags. The journey `signature` is an opaque server-issued token, not a client-computed signature.
- No retry, backoff or 429 / Retry-After handling. Rate control is client pacing only: search debounce 300ms, departures 30s, journeytimes 30s (1s while empty) capped at 10, vehicle locations 10s, status 2 minutes, analytics batched every 2s.
- No captcha or bot check: no Cloudflare Turnstile (`challenges.cloudflare.com`, `cf-turnstile`), reCAPTCHA or hCaptcha strings. "Turnstile" in this code is Citymapper's own payment service at `turnstile-api.citymapper.com/web/1/*` (and a staging host), used for Citymapper Pass payment methods (userinfo, add, set default, delete, delete all, session TTL), authenticated by `User-Device` and `Session-Id` headers. None of these methods has a caller in either bundle.
- Embedded keys, names and lengths only: `GOOGLE_MAPS_API_KEY` (39 chars, inlined `process.env`), `GOOGLE_KEY` OAuth client id (72 chars), `FACEBOOK_APP_ID` (15 chars).
- App-only features: the server flags the native app web view by a `CM;` marker in the User-Agent (`isCMClient`, client version is the third `;` field); supported app versions constant iOS 7.8 and Android 7.8; "Send to phone" stores a SavedJourney document that the app is expected to pick up (inferred); god messages with `citymapper://` URLs are filtered out on the web.
- Server helper endpoints outside `/api`: `/geocode`, `/static-img?src=` (map marker images), `/api/resourceproxy/tos.html` and `privacy-policy.html`, `/api/1/resources?id=citymapper-terms-of-service` and `citymapper-privacy-policy`, `https://global-api.citymapper.com/resourceproxy/greenie-*-web.png` city images.

## (e) landing.js

landing.js bundles the same `CitymapperAPI` class with the same instance (`new Zt({errorHandler, hostname: ""})`), the same user, journey, message and search actions, and the same login component. Differences:

- It fetches its own config: `GET /resource/region-info/<cm_region cookie or uk-london>` (falls back to uk-london, then `{}`) and `GET /resource/brand-directory` (brands keyed by brand_id). The /webapp bundle gets both inlined instead.
- It boots `GET /api/1/identity/user_data` and `syncUserData` like /webapp, and calls `/geocode`, search, message and journey endpoints through the shared components (GMS card and search box).
- No extra API methods and no calls to the methods that are unused in /webapp.

## Open questions

1. How the server picks the region when the URL has no `:region_slug`: `cm_region` cookie, IP geolocation, or Accept-Language. Needs a live request without the cookie.
2. CSRF on identity writes: the client sends no token on `POST /api/1/identity/places`, `favorites`, `sessions`, so check live whether a missing `X-CSRFToken` is rejected.
3. Where `uid` comes from (server Set-Cookie on first page?) and whether `/api/1/identity/*` also needs it or only `sessionid`.
4. Response schemas for the endpoints with no caller (everythingmap, schedules, weather, transitscore, routepaths, eta, blog) and for the Turnstile service; only request shapes are known.
5. What the server-rendered pages (`/eta/:slug`, `/pass`, `/signup/:token/confirm`, `/reset/:token/continue`, `/news`) call, since these bundles define the methods but never call them.
