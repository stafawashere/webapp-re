import dataclasses
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from citymapper_client import cli
from citymapper_client.context import Context
from citymapper_client.errors import ContractBroken
from citymapper_client.models import Status
from citymapper_client.registry import build_registry
from citymapper_client.session import Session

from support import load_fixture, signed_in_session
from test_commands import JOURNEY_SIGNATURE, READ_CASES, run_command

STORED_SESSION_STATUSES = {
   "list-saved-places": "blocked: needs your Citymapper session (you are signed out; sign in yourself, then adopt-session)",
   "save-place": "blocked: needs your Citymapper session (you are signed out); round trip with inverse ready, dry run checked",
   "list-favourites": "needs session: not yet verified live",
   "sign-out": "needs session: then your approval (dry run checked; PENDING-APPROVALS.md)",
}
PRIMARY_TABLE_LIST = {
   "plan-journey": "journeys",
   "plan-walk": "journeys",
   "plan-cycle": "journeys",
   "plan-vehicle-hire": "journeys",
   "plan-cab": "routes",
   "get-line": "stops",
   "get-stop": "routes",
}


def test_help_lists_57_commands_and_exits_0(capsys, tmp_path, monkeypatch):
   site_root = tmp_path / "cli-root"
   monkeypatch.setenv("CITYMAPPER_ROOT", str(site_root))

   exit_code = cli.main(["help"])

   printed = json.loads(capsys.readouterr().out)
   names = [command["name"] for command in printed["commands"]]
   assert exit_code == 0
   assert len(names) == 57
   assert "plan-journey" in names
   assert printed["session"]["has_session_cookie"] is False
   assert printed["session"]["env_file"] == str(site_root / ".env")
   assert printed["pacer"]["halted"] is False


def test_unknown_city_exits_17_with_a_json_error(capsys, make_context, monkeypatch):
   context, fake = make_context()
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   exit_code = cli.main(["get-city", "--city", "atlantis"])

   captured = capsys.readouterr()
   error = json.loads(captured.err)
   assert exit_code == 17
   assert error["class"] == "NotFound"
   assert "atlantis" in error["message"]
   assert captured.out == ""
   assert fake.requests == []


def test_known_city_prints_json_and_exits_0(capsys, make_context, monkeypatch):
   context, _ = make_context()
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   exit_code = cli.main(["get-city", "--city", "portvale"])

   assert exit_code == 0
   assert json.loads(capsys.readouterr().out)["region_id"] == "zz-portvale"


def routestatus_with_a_null_level():
   body = load_fixture("routestatus.json")
   body["groupings"][0]["routes"][0]["status"]["level"] = None
   return body


def routestatus_with_a_null_disruption_level():
   body = load_fixture("routestatus.json")
   body["groupings"][0]["routes"][0]["status"]["disruptions"][0]["level"] = None
   return body


@pytest.mark.parametrize("argv, responses, expected_detail", [
   (["search-places", "--city", "portvale", "--query", "Harbour"], {"searchpost": []}, {"field": "results"}),
   (["search-places", "--city", "portvale", "--query", "Harbour"], {"searchpost": {"elapsed": 12}}, {"field": "results"}),
   (["plan-journey", "--city", "portvale", "--from", "Harbour", "--to", "10.5,20.5"], {"searchpost": {"elapsed": 12}}, {"field": "results"}),
   (["get-disruptions", "--city", "portvale"], {"routestatus": routestatus_with_a_null_level()}, {"field": "level"}),
   (["get-disruptions", "--city", "portvale"], {"routestatus": routestatus_with_a_null_disruption_level()}, {"field": "level"}),
])
def test_a_response_that_changed_shape_exits_14_with_a_json_error(capsys, make_context, monkeypatch, argv, responses, expected_detail):
   context, _ = make_context(responses)
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   exit_code = cli.main(argv)

   captured = capsys.readouterr()
   error = json.loads(captured.err)
   assert exit_code == 14
   assert error["class"] == "ContractBroken"
   for key, expected in expected_detail.items():
      allowed = expected if isinstance(expected, tuple) else (expected,)
      assert error["detail"][key] in allowed
   assert captured.out == ""


def test_usage_error_exits_2(capsys, make_context, monkeypatch):
   context, _ = make_context()
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   exit_code = cli.main(["plan-journey", "--city", "portvale", "--from", "10.5,20.5", "--to", "10.6,20.7", "--depart-at", "08:30", "--arrive-by", "09:30"])

   assert exit_code == 2
   assert json.loads(capsys.readouterr().err)["class"] == "UsageError"


def update_profile_dry_run_body(capsys, make_context, monkeypatch, extra_argv):
   context, fake = make_context()
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   exit_code = cli.main(["update-profile", "--first-name", "Ada", *extra_argv, "--dry-run"])

   assert exit_code == 0
   assert fake.requests == []
   return json.loads(capsys.readouterr().out)["request"]["body"]


def test_update_profile_sends_only_the_fields_passed(capsys, make_context, monkeypatch):
   body = update_profile_dry_run_body(capsys, make_context, monkeypatch, [])

   assert body == {"first_name": "Ada"}


def test_update_profile_can_turn_pass_interest_off_on_purpose(capsys, make_context, monkeypatch):
   body = update_profile_dry_run_body(capsys, make_context, monkeypatch, ["--no-interested-in-pass"])

   assert body == {"first_name": "Ada", "is_interested_in_pass": False}


@pytest.mark.parametrize("ignored_option", ["--step-free", "--with-paths"])
def test_plan_cab_rejects_options_it_cannot_honour(capsys, ignored_option):
   with pytest.raises(SystemExit) as caught:
      cli.main(["plan-cab", "--city", "portvale", "--from", "10.5,20.5", "--to", "10.6,20.7", ignored_option])

   assert caught.value.code == 2
   assert "unrecognized arguments: " + ignored_option in capsys.readouterr().err


def test_update_place_can_move_a_place_with_city_and_near(capsys, make_context, monkeypatch):
   context, fake = make_context()
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   exit_code = cli.main(["update-place", "--id", "77", "--city", "portvale", "--near", "10.5,20.5", "--dry-run"])

   assert exit_code == 0
   assert fake.requests == []
   assert json.loads(capsys.readouterr().out)["request"]["body"]["coords"] == [10.5, 20.5]


@pytest.mark.parametrize("argv", [
   ["save-place", "--name", "Studio", "--near", "10.5,20.5", "--dry-run"],
   ["create-go-link", "--place", "10.5,20.5", "--title", "Meet here", "--dry-run"],
])
def test_writes_that_resolve_a_place_need_city_at_parse_time(capsys, argv):
   with pytest.raises(SystemExit) as caught:
      cli.main(argv)

   assert caught.value.code == 2
   assert "the following arguments are required: --city" in capsys.readouterr().err


def is_record_list(value):
   is_non_empty_list = isinstance(value, list) and bool(value)
   return is_non_empty_list and isinstance(value[0], dict)


def primary_rows(name, output):
   if name in PRIMARY_TABLE_LIST:
      return output[PRIMARY_TABLE_LIST[name]]

   record_lists = [key for key, value in output.items() if is_record_list(value)]
   assert len(record_lists) <= 1, "{0} has several record lists {1}; name its primary one in PRIMARY_TABLE_LIST".format(name, record_lists)
   return output[record_lists[0]] if record_lists else []


@pytest.mark.parametrize("name", sorted(READ_CASES))
def test_table_shows_the_primary_list_of_each_read_command(make_context, name):
   arguments, responses = READ_CASES[name]
   context, _ = make_context(responses, session=signed_in_session())
   output = run_command(context, name, arguments)
   rows = primary_rows(name, output)

   table = cli.as_table(output, name)

   if not rows:
      assert json.loads(table) == output
      return

   lines = table.splitlines()
   header = lines[0].split(" | ")
   assert len(lines) == len(rows) + 2

   for row, line in zip(rows, lines[2:]):
      cells = dict(zip(header, line.split(" | ")))
      shared_scalars = {column: value for column, value in row.items() if column in cells and not isinstance(value, (dict, list))}
      assert shared_scalars, "{0} row shares no column with the table".format(name)
      assert {column: cells[column] for column in shared_scalars} == {column: str(value) for column, value in shared_scalars.items()}


def help_statuses_with_stored_session_statuses(capsys, tmp_path, monkeypatch, has_session):
   site_root = tmp_path / "session-root"
   monkeypatch.setenv("CITYMAPPER_ROOT", str(site_root))
   readiness_file = site_root / "var/state/readiness.json"
   readiness_file.parent.mkdir(parents=True)
   readiness_file.write_text(json.dumps({name: {"status": status} for name, status in STORED_SESSION_STATUSES.items()}))

   if has_session:
      Session(cookies={"sessionid": "fake-session-for-test"}).save(site_root / ".env")

   assert cli.main(["help"]) == 0
   printed = json.loads(capsys.readouterr().out)
   assert printed["session"]["has_session_cookie"] is has_session
   return {command["name"]: command["readiness"] for command in printed["commands"] if command["name"] in STORED_SESSION_STATUSES}


def test_help_stops_calling_session_commands_blocked_after_adopt_session(capsys, tmp_path, monkeypatch):
   statuses = help_statuses_with_stored_session_statuses(capsys, tmp_path, monkeypatch, has_session=True)

   assert statuses == {
      "list-saved-places": "session present, not verified live yet (run scripts/live_check.py --only list-saved-places)",
      "save-place": "session present, not verified live yet; round trip with inverse ready, dry run checked",
      "list-favourites": "session present, not verified live yet (run scripts/live_check.py --only list-favourites)",
      "sign-out": "session present, not verified live yet, then your approval (dry run checked; PENDING-APPROVALS.md)",
   }


def test_help_says_how_to_unblock_session_commands_without_a_session(capsys, tmp_path, monkeypatch):
   statuses = help_statuses_with_stored_session_statuses(capsys, tmp_path, monkeypatch, has_session=False)

   assert statuses == {
      "list-saved-places": "blocked: needs your Citymapper session (sign in, then adopt-session)",
      "save-place": "blocked: needs your Citymapper session (sign in, then adopt-session); round trip with inverse ready, dry run checked",
      "list-favourites": "blocked: needs your Citymapper session (sign in, then adopt-session)",
      "sign-out": "blocked: needs your Citymapper session (sign in, then adopt-session), then your approval (dry run checked; PENDING-APPROVALS.md)",
   }


def parse_signatures(*extra_argv):
   parser = cli.build_parser(build_registry())
   return parser.parse_args(["get-journey-times", "--city", "portvale", *extra_argv]).signatures


def test_one_json_signature_stays_one_item_through_argv():
   assert parse_signatures("--signatures", JOURNEY_SIGNATURE) == [JOURNEY_SIGNATURE]


def test_signatures_can_be_repeated_or_given_as_a_json_array():
   other_signature = JOURNEY_SIGNATURE.replace("a", "b", 1)
   as_array = json.dumps([JOURNEY_SIGNATURE, other_signature])

   assert parse_signatures("--signatures", JOURNEY_SIGNATURE, "--signatures", other_signature) == [JOURNEY_SIGNATURE, other_signature]
   assert parse_signatures("--signatures", as_array) == [JOURNEY_SIGNATURE, other_signature]


def test_line_ids_still_split_on_commas():
   parser = cli.build_parser(build_registry())

   arguments = parser.parse_args(["get-lines", "--city", "portvale", "--lines", "1,2, A"])

   assert arguments.lines == ["1", "2", "A"]


@pytest.mark.parametrize("bad_limit", ["0", "-1", "abc"])
def test_a_limit_below_one_exits_2_with_a_json_error(capsys, bad_limit):
   with pytest.raises(SystemExit) as caught:
      cli.main(["search-places", "--city", "portvale", "--query", "Harbour", "--limit", bad_limit])

   error = json.loads(capsys.readouterr().err)
   assert caught.value.code == 2
   assert error["class"] == "UsageError"
   assert "--limit" in error["message"]


def run_whoami_that_raises(monkeypatch, make_context, error):
   context, _ = make_context()
   context.session.cookies["sessionid"] = "secret-cookie-value"
   monkeypatch.setattr(Context, "build", classmethod(lambda cls, **options: context))

   def failing_function(context, values):
      raise error

   registry = build_registry()
   registry["whoami"] = dataclasses.replace(registry["whoami"], function=failing_function)
   monkeypatch.setattr(cli, "build_registry", lambda: registry)

   return cli.main(["whoami"])


def test_exit_14_names_the_command_and_the_failing_message(capsys, make_context, monkeypatch):
   exit_code = run_whoami_that_raises(monkeypatch, make_context, KeyError("missing_field"))

   detail = json.loads(capsys.readouterr().err)["detail"]
   assert exit_code == 14
   assert detail["command"] == "whoami"
   assert detail["error"] == "KeyError"
   assert "missing_field" in detail["message"]


def test_exit_14_message_hides_session_cookie_values(capsys, make_context, monkeypatch):
   exit_code = run_whoami_that_raises(monkeypatch, make_context, ValueError("bad header secret-cookie-value"))

   error_text = capsys.readouterr().err
   assert exit_code == 14
   assert "secret-cookie-value" not in error_text
   assert "[redacted]" in error_text


def test_an_unreadable_env_file_is_a_usage_error_naming_the_file(capsys, tmp_path):
   env_file = tmp_path / "broken.env"
   env_file.write_bytes(b"\xff\xfe\x00bad")

   exit_code = cli.main(["--env-file", str(env_file), "help"])

   error = json.loads(capsys.readouterr().err)
   assert exit_code == 2
   assert error["class"] == "UsageError"
   assert error["detail"]["file"] == str(env_file)


def test_a_non_numeric_status_level_names_the_field():
   with pytest.raises(ContractBroken) as caught:
      Status.from_api({"level": None, "summary": "x"})

   assert caught.value.detail["field"] == "level"


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
FOREIGN_VENV = "/somewhere/else/.venv"


def stub_cryptography(monkeypatch):
   primitives = types.ModuleType("cryptography.hazmat.primitives")
   ciphers = types.ModuleType("cryptography.hazmat.primitives.ciphers")
   primitives.padding = object()
   ciphers.Cipher = ciphers.algorithms = ciphers.modes = object()

   for name, module in {"cryptography": types.ModuleType("cryptography"), "cryptography.hazmat": types.ModuleType("cryptography.hazmat"), "cryptography.hazmat.primitives": primitives, "cryptography.hazmat.primitives.ciphers": ciphers}.items():
      monkeypatch.setitem(sys.modules, name, module)


def load_script(monkeypatch, file_name):
   stub_cryptography(monkeypatch)
   monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
   spec = importlib.util.spec_from_file_location(file_name + "_under_test", SCRIPTS_DIR / (file_name + ".py"))
   module = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(module)
   return module


def capture_subprocess_run(monkeypatch):
   seen = {}

   def fake_run(command, **options):
      seen["command"] = command
      seen["env"] = options.get("env")
      return subprocess.CompletedProcess(args=command, returncode=0, stdout="{}", stderr="")

   monkeypatch.setattr(subprocess, "run", fake_run)
   monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", FOREIGN_VENV)
   return seen


@pytest.mark.parametrize("file_name, call", [
   ("live_check", lambda module: module.run_cli(["help"])),
   ("auto_adopt_session", lambda module: module.run_citymapper("/tmp/unused.env", ["help"])),
])
def test_scripts_pin_the_program_venv_before_calling_uv(monkeypatch, file_name, call):
   module = load_script(monkeypatch, file_name)
   seen = capture_subprocess_run(monkeypatch)

   call(module)

   assert seen["env"]["UV_PROJECT_ENVIRONMENT"] == str(module.PROGRAM_DIR / ".venv")
   assert "--frozen" in seen["command"]


def test_pending_approvals_pins_the_program_venv_before_calling_uv(monkeypatch):
   module = load_script(monkeypatch, "../../tools/engineer/pending_approvals")
   seen = capture_subprocess_run(monkeypatch)

   module.dry_run("sign-out", [])

   assert seen["env"]["UV_PROJECT_ENVIRONMENT"] == str(module.PROGRAM / ".venv")
   assert "--frozen" in seen["command"]


def test_journey_times_live_check_fails_on_a_count_mismatch_or_an_entry_error(monkeypatch):
   live_check = load_script(monkeypatch, "live_check")
   clean = {"times": [{"signature_index": 0, "time": "t", "error": None}]}
   errored = {"times": [{"signature_index": 0, "time": None, "error": "no time"}]}
   fragments = {"times": [{"signature_index": index, "time": "t", "error": None} for index in range(3)]}

   assert live_check.one_clean_time_per_signature(clean) == []
   assert live_check.one_clean_time_per_signature(errored) == ["signature 0: no time"]
   assert live_check.one_clean_time_per_signature(fragments) == ["sent 1 signature, got 3 times"]
