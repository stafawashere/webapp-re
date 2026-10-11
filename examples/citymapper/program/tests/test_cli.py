import json

import pytest

from citymapper_client import cli
from citymapper_client.context import Context
from citymapper_client.session import Session

from support import load_fixture, signed_in_session
from test_commands import READ_CASES, run_command

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


@pytest.mark.parametrize("argv, responses, expected_detail", [
   (["search-places", "--city", "portvale", "--query", "Harbour"], {"searchpost": []}, {"field": "results"}),
   (["search-places", "--city", "portvale", "--query", "Harbour"], {"searchpost": {"elapsed": 12}}, {"field": "results"}),
   (["plan-journey", "--city", "portvale", "--from", "Harbour", "--to", "10.5,20.5"], {"searchpost": {"elapsed": 12}}, {"field": "results"}),
   (["get-disruptions", "--city", "portvale"], {"routestatus": routestatus_with_a_null_level()}, {"error": ("AttributeError", "TypeError")}),
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
