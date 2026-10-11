"""Render openapi/citymapper.openapi.yaml from the knowledge base and the scope.

Only findings with status verified go into paths. Hypotheses go to x-hypotheses and dead findings to
x-retired, so the spec never claims an unreplayed contract works. The file is parsed back to prove
it loads.

   uv run --with pyyaml python tools/engineer/render_openapi.py
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCOPE = json.loads((ROOT / "scope/scope.json").read_text())
OUTPUT = ROOT / "openapi/citymapper.openapi.yaml"
JSON_BODY_ENDPOINTS = {"journeytimes", "refreshjourneys", "searchpost"}


def read_findings():
   findings = {}

   for path in sorted((ROOT / "knowledge/endpoints").glob("*.md")):
      text = path.read_text()
      front = text.split("---", 2)[1] if text.startswith("---") else ""
      meta = {}

      for line in front.splitlines():
         key, separator, value = line.partition(":")
         if separator:
            meta[key.strip()] = value.strip().strip('"')

      findings[meta.get("id", path.stem)] = meta

   return findings


def camel(identifier):
   parts = re.split(r"[^a-zA-Z0-9]+", identifier)
   return parts[0].lower() + "".join(part.capitalize() for part in parts[1:])


def split_url(url):
   without_optional = re.sub(r"\[[^\]]*\]", "", url)
   base = without_optional.split("?", 1)[0]
   match = re.match(r"(https?://[^/]+)(/.*)?$", base)
   server = match.group(1)
   path = match.group(2) or "/"
   path = re.sub(r"\{([^}]*)\}", lambda found: "{" + re.sub(r"[^a-z0-9_]+", "_", found.group(1).lower()).strip("_") + "}", path)
   return server, path


def response_schema(shape):
   if not shape:
      return {"type": "object"}

   properties = {}
   for key, description in shape.items():
      top = key.split(".")[0].split("[")[0]

      if top in ("$", ""):
         continue

      is_list = key.split(".")[0].endswith("[]")
      entry = properties.setdefault(top, {"type": "array" if is_list else "object", "description": ""})
      entry["description"] = (entry["description"] + " " + "{0}: {1}".format(key, description)).strip()

   return {"type": "object", "properties": properties}


def operation(finding_id, meta, endpoint):
   path_parameters = re.findall(r"\{([^}]*)\}", split_url(meta["url"])[1])
   parameters = [{"name": name, "in": "path", "required": True, "schema": {"type": "string"}} for name in path_parameters]

   for key in endpoint.get("query_keys", []):
      parameters.append({"name": key, "in": "query", "required": False, "schema": {"type": "string"}})

   for header in endpoint.get("request_header_names", []):
      if header.lower() in ("citymapper-region", "citymapper-client", "x-csrftoken", "user-device", "session-id"):
         source = {"citymapper-region": "the region_id of the request", "citymapper-client": "constant 'Web Search' on searchpost", "x-csrftoken": "csrftoken cookie", "user-device": "uid cookie", "session-id": "sessionid cookie"}[header.lower()]
         parameters.append({"name": header, "in": "header", "required": False, "schema": {"type": "string"}, "x-value-source": source})

   content_type = "text/html" if endpoint.get("surface") == "html" else "application/json"
   record = {
      "operationId": camel(finding_id),
      "summary": meta.get("goal", finding_id),
      "description": endpoint.get("notes", ""),
      "parameters": parameters,
      "responses": {"200": {"description": "Success", "content": {content_type: {"schema": response_schema(endpoint.get("response_shape"))}}}},
      "x-provenance": {"finding": finding_id, "status": meta.get("status"), "verify_count": int(meta.get("verify_count", 0) or 0), "last_verified": meta.get("last_verified", "")},
   }

   if endpoint.get("body_fields"):
      body_type = "application/x-www-form-urlencoded (JSON text body)" if finding_id == "searchpost" else "application/json"
      record["requestBody"] = {"content": {"application/json": {"schema": {"type": "object", "properties": {field: {} for field in endpoint["body_fields"]}}}}, "x-content-type-sent": body_type}

   return record


def main():
   findings = read_findings()
   endpoints = {endpoint["id"]: endpoint for endpoint in SCOPE["endpoints"]}
   servers = set()
   paths = {}
   hypotheses = []
   retired = []

   for finding_id, meta in findings.items():
      endpoint = endpoints.get(finding_id, {})
      status = meta.get("status")

      if status == "dead":
         retired.append({"finding": finding_id, "method": meta.get("method"), "url": meta.get("url")})
         continue

      if status != "verified":
         hypotheses.append({"finding": finding_id, "method": meta.get("method"), "url": meta.get("url"), "status": status})
         continue

      server, path = split_url(meta["url"])
      servers.add(server)
      method = meta.get("method", "GET").lower()
      key = path if path not in paths or method not in paths[path] else path + "#" + finding_id
      paths.setdefault(key, {})[method] = operation(finding_id, meta, endpoint)

   spec = {
      "openapi": "3.1.0",
      "info": {
         "title": "Citymapper web API (private, observed)",
         "version": "2026-10-10",
         "description": "Rendered from the citymapper knowledge base (knowledge/endpoints). Only replayed, verified contracts are in paths; bundle-only contracts are in x-hypotheses and retired ones in x-retired. These are the website's own requests, not Citymapper's official developer API.",
      },
      "servers": [{"url": server} for server in sorted(servers)],
      "paths": dict(sorted(paths.items())),
      "components": {"securitySchemes": {"sessionCookie": {"type": "apiKey", "in": "cookie", "name": "sessionid"}}},
      "x-hypotheses": hypotheses,
      "x-retired": retired,
      "x-discovery-notes": {
         "authentication": {"type": "cookie-session (optional)", "session_cookie": "sessionid", "login": "e-mail magic link, Google or Facebook token to /api/1/identity/sessions (not automated)"},
         "required_headers": {"Citymapper-Region": "region id, on searchpost, routestatus and message", "Citymapper-Client": "'Web Search' on searchpost", "Content-Type": "application/json; charset=utf-8 on every call, form type with a JSON body on searchpost"},
         "anti_bot": {"cdn": "cloudflare", "cookie": "__cf_bm", "challenges": "none observed", "rate_limit": "no headers; client paces at 3 s or more"},
         "session": {"initialization": "none needed for public reads", "region": "explicit region_id on every call"},
         "quirks": [
            {"name": "google-results-without-coords", "description": "searchpost Google autocomplete items carry no coords; resolve with placeresolve?id=google:<id>"},
            {"name": "departures-per-brand", "description": "stopinfo sharing_urls[].departure_api picks departures, metrodepartures or raildepartures"},
            {"name": "named-tile-size", "description": "everythingmap size must be small or large"},
            {"name": "signature-is-a-journey", "description": "journey signature is a JSON journey descriptor, deflated and base64 encoded in /trip/signature URLs"},
         ],
      },
   }

   OUTPUT.parent.mkdir(exist_ok=True)
   OUTPUT.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=120))
   loaded = yaml.safe_load(OUTPUT.read_text())
   operations = sum(len(item) for item in loaded["paths"].values())
   print("openapi: parsed {0}; {1}; {2} paths, {3} operations, {4} hypotheses, {5} retired".format(OUTPUT.relative_to(ROOT), loaded["openapi"], len(loaded["paths"]), operations, len(loaded["x-hypotheses"]), len(loaded["x-retired"])))


if __name__ == "__main__":
   main()
