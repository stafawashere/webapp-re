"""Build scope/scope.json and scope/scope.md for citymapper from the walk data in scope_data.py."""
import json
from pathlib import Path

from scope_data import AUTH, CAPABILITIES, CAVEATS, ENDPOINTS, ENTITIES, OPEN_QUESTIONS, PAGES, PAGINATION, SITE, SUMMARY

ROOT = Path(__file__).resolve().parents[2]
GENERATED = "2026-10-10"


def build():
   scope = {
      "site": SITE,
      "generated": GENERATED,
      "summary": SUMMARY,
      "pages": PAGES,
      "capabilities": CAPABILITIES,
      "endpoints": ENDPOINTS,
      "entities": ENTITIES,
      "auth": AUTH,
      "pagination": PAGINATION,
      "caveats": CAVEATS,
      "open_questions": OPEN_QUESTIONS,
   }

   (ROOT / "scope").mkdir(exist_ok=True)
   (ROOT / "scope/scope.json").write_text(json.dumps(scope, indent=3, ensure_ascii=False) + "\n")
   (ROOT / "scope/scope.md").write_text(render_markdown(scope))
   print("wrote scope.json and scope.md: {0} pages, {1} capabilities, {2} endpoints".format(len(PAGES), len(CAPABILITIES), len(ENDPOINTS)))


def table(headers, rows):
   lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]

   for row in rows:
      cells = [str(cell).replace("|", "/").replace("\n", " ") for cell in row]
      lines.append("| " + " | ".join(cells) + " |")

   return "\n".join(lines)


def render_markdown(scope):
   site = scope["site"]
   parts = [
      "# Citymapper scope",
      "",
      "Generated {0} from a read-only walk of https://citymapper.com in your browser (signed out, since you have no Citymapper session there), CDP captures of the same pages in a separate signed-out browser profile, and the site's public JS bundle.".format(scope["generated"]),
      "",
      "## Summary",
      "",
      scope["summary"],
      "",
      "Origins: {0}. Framework: {1}. Bundler: {2}. Source maps: {3}.".format(", ".join(site["origins"]), site["framework"], site["bundler"], site["source_maps"]),
      "",
      "## Page map",
      "",
      table(["Page", "URL pattern", "Auth", "Visited", "Purpose", "Endpoints"], [(item["id"], item["url_pattern"], item.get("requires_auth"), item.get("visited"), item["purpose"], ", ".join(item.get("endpoints", []))) for item in scope["pages"]]),
      "",
      "## Capabilities",
      "",
      table(["Capability", "User action", "Mutates", "Others see", "Exercised", "Endpoints", "Notes"], [(item["id"], item["user_action"], item["mutates"], item.get("visible_to_others"), item["exercised"], ", ".join(item["endpoints"]), item.get("notes", "")) for item in scope["capabilities"]]),
      "",
      "## Endpoints",
      "",
      table(["Endpoint", "Method", "URL pattern", "Surface", "Observed", "Query", "Body", "Pagination", "Notes"], [(item["id"], item["method"], item["url_pattern"], item["surface"], item["observed"], ", ".join(item.get("query_keys", [])), ", ".join(item.get("body_fields", [])), item.get("pagination", ""), ("noise. " if item.get("noise") else "") + item.get("notes", "")) for item in scope["endpoints"]]),
      "",
      "## Entities",
      "",
      table(["Entity", "Description", "Fields", "Ids", "Sources"], [(item["id"], item.get("description", ""), ", ".join(item["fields"]), ", ".join(item.get("id_fields", [])), ", ".join(item.get("source_endpoints", []))) for item in scope["entities"]]),
      "",
      "## Auth and session",
      "",
   ]

   for key, value in scope["auth"].items():
      shown = ", ".join(value) if isinstance(value, list) else value
      parts.append("- **{0}**: {1}".format(key, shown))

   parts += [
      "",
      "## Pagination and time windows",
      "",
      table(["Scheme", "Kind", "Request keys", "Response keys", "Terminator", "Page size"], [(item["id"], item["kind"], ", ".join(item.get("request_keys", [])), ", ".join(item.get("response_keys", [])), item.get("terminator", ""), item.get("page_size")) for item in scope["pagination"]]),
      "",
      "## Caveats",
      "",
      table(["Kind", "Severity", "Detail", "Evidence"], [(item["kind"], item["severity"], item["detail"], item.get("evidence", "")) for item in scope["caveats"]]),
      "",
      "## Open questions",
      "",
   ]
   parts += ["- " + question for question in scope["open_questions"]]
   parts.append("")
   return "\n".join(parts)


if __name__ == "__main__":
   build()
