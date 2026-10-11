"""Provenance gate: every endpoint literal in src/ is backed by a knowledge base finding.

Endpoint(...) literals need a finding with status verified and verify_count >= 2 whose method, host
and path match. PendingEndpoint(...) literals need a finding that exists and is not dead; they are
reported separately and their commands are never labelled verified. Any http(s) URL or API path
literal outside endpoints.py is a violation unless its line carries "# provenance: ignore, <reason>"
with a reason of ten characters or more. An ignore marker never covers endpoints.py or a line that
builds an Endpoint, and an Endpoint built outside endpoints.py is a violation.

A second pass imports endpoints.py and checks every object in ALL_ENDPOINTS against the findings,
and the number of declarations the text pass recognised must equal len(ALL_ENDPOINTS).

Positive controls run first: eight planted source defects must produce exactly eight violations and
three planted endpoint objects exactly three, or the gate exits 2 as unrunnable.

   uv run --offline python scripts/check_provenance.py
"""
import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace

PROGRAM_DIR = Path(__file__).resolve().parents[1]
SITE_ROOT = PROGRAM_DIR.parent
SOURCE_DIR = PROGRAM_DIR / "src" / "citymapper_client"
ENDPOINTS_FILE = "endpoints.py"
DEFAULT_HOST = "https://citymapper.com"
ENDPOINT_CALL = re.compile(r'^\s*[A-Z0-9_]+ = (Endpoint|PendingEndpoint)\("([^"]+)", "([A-Z]+)", "([^"]+)"(.*)\)\s*#\s*finding:\s*(\S+)\s*$')
ENDPOINT_MENTION = re.compile(r"\b(?:Pending)?Endpoint\(")
CLASS_LINE = re.compile(r"^\s*class\s")
HOST_ARGUMENT = re.compile(r"\bhost\s*=\s*([^,)\s]+)")
HOST_CONSTANT = re.compile(r'^\s*([A-Z0-9_]+) = "(https://[^"]+)"\s*#\s*finding:\s*(\S+)\s*$')
PATH_LITERAL = re.compile(r'["\'](https?://[^"\'\s]+|/(?:api|resource|geocode|trip|web/1|cities/vote)[^"\']*)["\']')
IGNORE_MARKER = re.compile(r"#\s*provenance:\s*ignore,\s*(.+)$")
MINIMUM_REASON_LENGTH = 10
EXPECTED_SOURCE_CONTROLS = 8
EXPECTED_OBJECT_CONTROLS = 3


def read_findings(knowledge_dir):
   findings = {}

   for path in sorted((knowledge_dir / "endpoints").glob("*.md")):
      text = path.read_text()
      front = text.split("---", 2)[1] if text.startswith("---") else ""
      meta = {}

      for line in front.splitlines():
         key, separator, value = line.partition(":")
         if separator:
            meta[key.strip()] = value.strip().strip('"')

      findings[meta.get("id", path.stem)] = {
         "status": meta.get("status", ""),
         "verify_count": int(meta.get("verify_count", "0") or 0),
         "method": meta.get("method", "").upper(),
         "url": meta.get("url", ""),
      }

   return findings


def shape_of(url_or_path):
   without_optional = re.sub(r"\[[^\]]*\]", "", url_or_path)
   without_query = without_optional.split("?", 1)[0]
   host_match = re.match(r"(https?://[^/]+)(/.*)?$", without_query)
   host = host_match.group(1) if host_match else DEFAULT_HOST
   path = (host_match.group(2) or "/") if host_match else without_query
   return host, re.sub(r"\{[^}]*\}", "{}", path).rstrip("/") or "/"


def contract_problem(finding_id, is_pending, method, host, literal_path, findings):
   kind = "PendingEndpoint" if is_pending else "Endpoint"
   finding = findings.get(finding_id)

   if finding is None:
      return "{0} {1} {2} has no finding {3}".format(kind, method, literal_path, finding_id)

   finding_host, finding_path = shape_of(finding["url"])
   same_method = finding["method"] == method
   same_path = finding_path == shape_of(literal_path)[1]
   same_host = finding_host == host
   matches_contract = same_method and same_path and same_host

   if not matches_contract:
      return "{0} {1}{2} differs from finding {3} ({4} {5}{6})".format(method, host, literal_path, finding_id, finding["method"], finding_host, finding_path)

   is_dead = finding["status"] == "dead"
   is_backed = finding["status"] == "verified" and finding["verify_count"] >= 2

   if is_dead:
      return "uses dead finding {0}".format(finding_id)

   if not is_pending and not is_backed:
      return "Endpoint {0} is {1} with {2} passes; it needs verified x2 or PendingEndpoint".format(finding_id, finding["status"], finding["verify_count"])

   return None


def check_source(files, findings):
   violations = []
   counts = {"Endpoint": 0, "PendingEndpoint": 0}
   hosts = {"ORIGIN": DEFAULT_HOST}

   for path, text in files:
      is_endpoints_file = path.name == ENDPOINTS_FILE

      for number, line in enumerate(text.splitlines(), start=1):
         location = "{0}:{1}".format(path.name, number)
         is_class_line = CLASS_LINE.match(line) is not None
         builds_endpoint = ENDPOINT_MENTION.search(line) is not None and not is_class_line
         ignore = IGNORE_MARKER.search(line)

         if ignore:
            ignore_is_refused = is_endpoints_file or builds_endpoint
            reason_too_short = len(ignore.group(1).strip()) < MINIMUM_REASON_LENGTH

            if ignore_is_refused:
               violations.append("{0} provenance ignore is not allowed on an endpoint line".format(location))
            elif reason_too_short:
               violations.append("{0} provenance ignore without a reason".format(location))

            continue

         host_constant = HOST_CONSTANT.match(line) if is_endpoints_file else None
         if host_constant:
            hosts[host_constant.group(1)] = host_constant.group(2)
            finding = findings.get(host_constant.group(3))
            host_backed = finding is not None and shape_of(finding["url"])[0] == host_constant.group(2)
            if not host_backed:
               violations.append("{0} host {1} has no finding on that host".format(location, host_constant.group(2)))
            continue

         call = ENDPOINT_CALL.match(line) if is_endpoints_file else None
         if call:
            kind, finding_id, method, literal_path, rest, cited = call.groups()
            counts[kind] += 1
            host_argument = HOST_ARGUMENT.search(rest)
            host_name = host_argument.group(1) if host_argument else "ORIGIN"

            if host_name not in hosts:
               violations.append("{0} host={1} is not a host constant backed by a finding".format(location, host_name))
               continue

            if cited != finding_id:
               violations.append("{0} cites {1} but declares {2}".format(location, cited, finding_id))
               continue

            problem = contract_problem(finding_id, kind == "PendingEndpoint", method, hosts[host_name], literal_path, findings)
            if problem:
               violations.append("{0} {1}".format(location, problem))

            continue

         if builds_endpoint and not is_endpoints_file:
            violations.append("{0} builds an endpoint outside {1}".format(location, ENDPOINTS_FILE))
            continue

         if builds_endpoint:
            violations.append("{0} endpoint declaration is not one line of NAME = Endpoint(finding, METHOD, path)  # finding: id".format(location))
            continue

         for literal in PATH_LITERAL.findall(line):
            violations.append("{0} unbacked literal {1}".format(location, literal))

   return violations, counts


def check_objects(endpoint_objects, findings):
   violations = []

   for endpoint in endpoint_objects:
      is_pending = bool(getattr(endpoint, "pending", False))
      problem = contract_problem(endpoint.finding, is_pending, endpoint.method, endpoint.host, endpoint.path, findings)

      if problem:
         violations.append("ALL_ENDPOINTS {0}".format(problem))

   return violations


def load_endpoint_objects():
   module_name = "citymapper_endpoints_under_provenance_check"
   spec = importlib.util.spec_from_file_location(module_name, SOURCE_DIR / ENDPOINTS_FILE)
   module = importlib.util.module_from_spec(spec)
   sys.modules[module_name] = module
   spec.loader.exec_module(module)
   return list(module.ALL_ENDPOINTS)


def positive_controls(findings):
   planted_source = [
      (Path("endpoints.py"), 'GHOST = Endpoint("no-such-finding", "GET", "/api/9/ghost")  # finding: no-such-finding\n'),
      (Path("capability.py"), 'url = "/api/1/hidden"\n'),
      (Path("endpoints.py"), 'SNEAKY = Endpoint("gettrip", "GET", "/api/1/gettrip")  # finding: gettrip\n'),
      (Path("endpoints.py"), 'UNCITED = Endpoint("no-such-finding", "GET", "/meet/ghost")\n'),
      (Path("capability.py"), 'ghost = Endpoint("journeys", "GET", "/news/ghost")\n'),
      (Path("endpoints.py"), 'LEAK = PendingEndpoint("gettrip", "GET", "/api/1/gettrip", host="https://collector.example.net")  # finding: gettrip\n'),
      (Path("capability.py"), 'url = "https://collector.example.net/api/1/journeys"\n'),
      (Path("endpoints.py"), 'HIDDEN = Endpoint("journeys", "GET", "/api/1/hidden")  # provenance: ignore, reviewed by hand already\n'),
   ]
   planted_objects = [
      SimpleNamespace(finding="no-such-finding", method="GET", host=DEFAULT_HOST, path="/meet/ghost", pending=False),
      SimpleNamespace(finding="journeys", method="GET", host="https://collector.example.net", path="/api/7/journeys", pending=False),
      SimpleNamespace(finding="gettrip", method="GET", host=DEFAULT_HOST, path="/api/1/gettrip", pending=False),
   ]
   source_violations, _ = check_source(planted_source, findings)
   object_violations = check_objects(planted_objects, findings)
   return source_violations, object_violations


def main():
   findings = read_findings(SITE_ROOT / "knowledge")
   source_controls, object_controls = positive_controls(findings)
   source_controls_hold = len(source_controls) == EXPECTED_SOURCE_CONTROLS
   object_controls_hold = len(object_controls) == EXPECTED_OBJECT_CONTROLS

   if not (source_controls_hold and object_controls_hold):
      print("positive control: {0} of {1} planted source defects and {2} of {3} planted objects caught; gate unrunnable".format(len(source_controls), EXPECTED_SOURCE_CONTROLS, len(object_controls), EXPECTED_OBJECT_CONTROLS))
      for violation in source_controls + object_controls:
         print("   " + violation)
      sys.exit(2)

   print("positive control: {0} of {1} planted source defects and {2} of {3} planted objects caught".format(len(source_controls), EXPECTED_SOURCE_CONTROLS, len(object_controls), EXPECTED_OBJECT_CONTROLS))
   files = [(path, path.read_text()) for path in sorted(SOURCE_DIR.rglob("*.py"))]
   violations, counts = check_source(files, findings)
   endpoint_objects = load_endpoint_objects()
   violations += check_objects(endpoint_objects, findings)
   declared_count = counts["Endpoint"] + counts["PendingEndpoint"]

   if declared_count != len(endpoint_objects):
      violations.append("text pass recognised {0} endpoint declarations but ALL_ENDPOINTS holds {1}".format(declared_count, len(endpoint_objects)))

   for violation in violations:
      print(violation)

   print("Endpoint {0}, PendingEndpoint {1}, ALL_ENDPOINTS {2}".format(counts["Endpoint"], counts["PendingEndpoint"], len(endpoint_objects)))
   print("provenance violations: {0}".format(len(violations)))
   sys.exit(1 if violations else 0)


if __name__ == "__main__":
   main()
