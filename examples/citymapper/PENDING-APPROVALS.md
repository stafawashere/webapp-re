# Pending approvals

Generated 2026-10-10 11:35 by tools/engineer/pending_approvals.py. Nothing here was sent. Each entry shows the
dry run the program prints and the exact live call to run after you approve it in chat. Values in
angle brackets are yours to choose.

## First: your Citymapper session

Every account command below needs your own session. The program never signs in for you (it could
create an account). If `help` shows no session cookie: sign in on citymapper.com in your browser,
copy the Cookie request header of any citymapper.com request, then

```bash
pbpaste | uv run --project program citymapper --env-file .env adopt-session --stdin
```

It stores only sessionid, csrftoken, uid, uid_set, cm_region and _locale in `.env` (mode 600) and
prints names and lengths, never values. Then `whoami` should print `"signed_in": true`.

## Approval writes

Public, personal-data, payment or no-inverse actions. Never run without your approval of the exact call.

### share-journey

Why it needs approval: Creates a public citymapper.com/trip link to a journey; anyone with the link can open it and it cannot be deleted.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env share-journey --city nyc --signature '<signature from plan-journey>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "GET",
  "url": "https://citymapper.com/api/1/createtripurl?signature=%3Csignature+from+plan-journey%3E&trip_region_id=us-nyc",
  "body": {},
  "finding": "createtripurl"
 },
 "confirm": "7688f76c8fa5"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env share-journey --city nyc --signature '<signature from plan-journey>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### create-go-link

Why it needs approval: Creates a public Meet Me Somewhere link with your title and message; it cannot be deleted.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env create-go-link --city nyc --place 40.748441,-73.985664 --title 'Meet at the Empire State Building' --message 'See you at 7' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "GET",
  "url": "https://citymapper.com/api/1/createshorturl?endcoord=40.748441%2C-73.985664&endaddress=&endname=40.748441%2C-73.985664&title=Meet+at+the+Empire+State+Building&message=See+you+at+7&place_id=",
  "body": {},
  "finding": "createshorturl"
 },
 "confirm": "97f3504edcdb"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env create-go-link --city nyc --place 40.748441,-73.985664 --title 'Meet at the Empire State Building' --message 'See you at 7' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### vote-for-city

Why it needs approval: Sends your e-mail address to Citymapper with a city vote; no undo.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env vote-for-city --city-slug '<city to vote for>' --email '<your e-mail>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://citymapper.com/cities/vote_submit/",
  "body": {
   "city_slug": "<city to vote for>",
   "email": "<your e-mail>"
  },
  "finding": "city-vote"
 },
 "confirm": "a7948817ea0b"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env vote-for-city --city-slug '<city to vote for>' --email '<your e-mail>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### sign-out

Why it needs approval: Ends the stored Citymapper session; signing back in is yours to do.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env sign-out  --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "DELETE",
  "url": "https://citymapper.com/api/1/identity/sessions",
  "body": {},
  "finding": "identity-sessions-delete"
 },
 "confirm": "433c9c33e411"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env sign-out  --yes --confirm '<confirm value printed by the dry run you approved>'
```

### pass-set-default-payment

Why it needs approval: Changes the default payment method of your paid Citymapper Pass.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env pass-set-default-payment --use-web-session-id --provider '<payment provider id>' --payment-method-id '<payment method id from pass-account>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://turnstile-api.citymapper.com/web/1/setdefaultpaymentmethod",
  "body": {
   "payment_provider_id": "<payment provider id>",
   "payment_method_id": "<payment method id from pass-account>"
  },
  "finding": "turnstile-setdefaultpaymentmethod"
 },
 "confirm": "838cd48bb222"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env pass-set-default-payment --use-web-session-id --provider '<payment provider id>' --payment-method-id '<payment method id from pass-account>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### pass-add-payment-method

Why it needs approval: Attaches a payment method to Citymapper Pass. The token comes from the payment provider; never type a card number.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env pass-add-payment-method --use-web-session-id --provider '<payment provider id>' --payment-method-id '<token from the payment provider>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://turnstile-api.citymapper.com/web/1/addpaymentmethod",
  "body": {
   "payment_provider_id": "<payment provider id>",
   "payment_method_id": "<token from the payment provider>"
  },
  "finding": "turnstile-addpaymentmethod"
 },
 "confirm": "7ce0f319478a"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env pass-add-payment-method --use-web-session-id --provider '<payment provider id>' --payment-method-id '<token from the payment provider>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### pass-remove-payment-method

Why it needs approval: Removes a Pass payment method; no inverse.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env pass-remove-payment-method --use-web-session-id --provider '<payment provider id>' --payment-method-id '<payment method id from pass-account>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://turnstile-api.citymapper.com/web/1/deletepaymentmethod",
  "body": {
   "payment_provider_id": "<payment provider id>",
   "payment_method_id": "<payment method id from pass-account>"
  },
  "finding": "turnstile-deletepaymentmethod"
 },
 "confirm": "bb45bef7ed4f"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env pass-remove-payment-method --use-web-session-id --provider '<payment provider id>' --payment-method-id '<payment method id from pass-account>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### pass-remove-all-payment-methods

Why it needs approval: Removes every Pass payment method for a provider; no inverse.

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env pass-remove-all-payment-methods --use-web-session-id --provider '<payment provider id>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://turnstile-api.citymapper.com/web/1/deleteallpaymentmethods",
  "body": {
   "payment_provider_id": "<payment provider id>"
  },
  "finding": "turnstile-deleteallpaymentmethods"
 },
 "confirm": "9fef9033fc52"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env pass-remove-all-payment-methods --use-web-session-id --provider '<payment provider id>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

## Round-trip writes (need your session)

Each has an exact inverse the program implements. With a session, they can be verified by: read, write,
read back, run the inverse, read back to the starting state. They were not run overnight because there
is no session.

### save-place

Inverse: remove-place --id <place id returned>

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env save-place --city nyc --name 'Test place (citymapper skill)' --near 40.748441,-73.985664 --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://citymapper.com/api/1/identity/places",
  "body": {
   "address": "",
   "coords": [
    40.748441,
    -73.985664
   ],
   "created": 1791646555,
   "deleted": false,
   "editability": 1,
   "last_used": 1791646555,
   "modified": 1791646555,
   "my_places_order": 0,
   "name": "Test place (citymapper skill)",
   "place_type": 2,
   "populated": true,
   "region_code": "us-nyc",
   "role": "",
   "section": "Special",
   "source": 0,
   "template_place_id": ""
  },
  "finding": "identity-places-create"
 },
 "confirm": "b853f2c2e843"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env save-place --city nyc --name 'Test place (citymapper skill)' --near 40.748441,-73.985664 --yes --confirm '<confirm value printed by the dry run you approved>'
```

### update-place

Inverse: update-place --id <same id> --name <name read before>

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env update-place --id '<place id from list-saved-places>' --name 'Renamed place' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "PUT",
  "url": "https://citymapper.com/api/1/identity/places/<place id from list-saved-places>",
  "body": {
   "name": "Renamed place"
  },
  "finding": "identity-places-update"
 },
 "confirm": "6eabb9431121"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env update-place --id '<place id from list-saved-places>' --name 'Renamed place' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### remove-place

Inverse: save-place with the name, address and coords read before (the id changes)

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env remove-place --id '<place id from list-saved-places>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "DELETE",
  "url": "https://citymapper.com/api/1/identity/places/<place id from list-saved-places>",
  "body": {},
  "finding": "identity-places-delete"
 },
 "confirm": "38f9ff29f90c"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env remove-place --id '<place id from list-saved-places>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### add-favourite

Inverse: remove-favourite --id <favourite id returned>

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env add-favourite --city nyc --line subway-6 --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://citymapper.com/api/1/identity/favorites",
  "body": {
   "brand_code": "NewYorkSubway",
   "coords": null,
   "name": "Lexington Avenue Local",
   "region_code": "us-nyc",
   "short_name": "6",
   "target_id": "6",
   "target_type": 3
  },
  "finding": "identity-favorites-create"
 },
 "confirm": "940907e5ddf1"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env add-favourite --city nyc --line subway-6 --yes --confirm '<confirm value printed by the dry run you approved>'
```

### remove-favourite

Inverse: add-favourite with the same stop or line

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env remove-favourite --id '<favourite id from list-favourites>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "DELETE",
  "url": "https://citymapper.com/api/1/identity/favorites/<favourite id from list-favourites>",
  "body": {},
  "finding": "identity-favorites-delete"
 },
 "confirm": "71202bf218c7"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env remove-favourite --id '<favourite id from list-favourites>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### save-journey

Inverse: remove-saved-journey --document-id <document id returned>; may also notify your phone, which cannot be undone

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env save-journey --city nyc --signature '<signature from plan-journey>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://citymapper.com/api/1/identity/documents/SavedJourney",
  "body": {
   "document_data": "{\"region_id\": \"us-nyc\", \"created\": 1791646556, \"signature\": \"<signature from plan-journey>\", \"shared\": false, \"associated_journeys\": []}"
  },
  "finding": "identity-save-journey"
 },
 "confirm": "305dd21cb34c"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env save-journey --city nyc --signature '<signature from plan-journey>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### remove-saved-journey

Inverse: only for a journey this program saved

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env remove-saved-journey --document-id '<document id returned by save-journey>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "DELETE",
  "url": "https://citymapper.com/api/1/identity/documents/SavedJourney/<document id returned by save-journey>",
  "body": {},
  "finding": "identity-delete-journey"
 },
 "confirm": "8bcd0801ca1c"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env remove-saved-journey --document-id '<document id returned by save-journey>' --yes --confirm '<confirm value printed by the dry run you approved>'
```

### update-profile

Inverse: update-profile with the values whoami shows before

Dry run (sends nothing to the write endpoint):

```bash
uv run --project program citymapper --env-file .env update-profile --first-name '<new first name>' --dry-run
```

```json
{
 "dry_run": true,
 "request": {
  "method": "POST",
  "url": "https://citymapper.com/api/1/identity/update_user",
  "body": {
   "first_name": "<new first name>"
  },
  "finding": "identity-update-user"
 },
 "confirm": "a7b2a087839a"
}
```

After you approve, the live call. Rerun the dry run with your real values first; its `confirm` value ties the send to that exact request, and the program refuses to send if the request has changed:

```bash
uv run --project program citymapper --env-file .env update-profile --first-name '<new first name>' --yes --confirm '<confirm value printed by the dry run you approved>'
```
