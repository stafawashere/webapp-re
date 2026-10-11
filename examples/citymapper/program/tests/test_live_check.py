import importlib.util
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from citymapper_client import config
from support import signed_in_session
from test_commands import READ_CASES, run_command

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
CONTRACT_BROKEN = json.dumps({"class": "ContractBroken", "message": "the site changed"})


@pytest.fixture
def decoy_default_root(monkeypatch, tmp_path):
   decoy_root = tmp_path / "decoy-default-root"
   monkeypatch.setattr(config, "DEFAULT_SITE_ROOT", decoy_root)
   return decoy_root


@pytest.fixture
def live_check(monkeypatch, tmp_path, decoy_default_root):
   monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
   spec = importlib.util.spec_from_file_location("live_check_under_test", SCRIPTS_DIR / "live_check.py")
   module = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(module)
   monkeypatch.setenv("CITYMAPPER_ROOT", str(tmp_path / "live-root"))
   return module


def current_readiness_file():
   return Path(os.environ["CITYMAPPER_ROOT"]) / "var/state/readiness.json"


def fixture_stdout(make_context, name):
   arguments, responses = READ_CASES[name]
   context, _ = make_context(responses, session=signed_in_session())
   return json.dumps(run_command(context, name, arguments))


def completed(returncode, stdout="", stderr=""):
   return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def seed_readiness(commands):
   current_readiness_file().parent.mkdir(parents=True, exist_ok=True)
   current_readiness_file().write_text(json.dumps({command: {"status": "verified live", "verified_at": "old"} for command in commands}))


def run_live_check(module, only):
   with pytest.raises(SystemExit):
      module.main(["--only", only])

   return json.loads(current_readiness_file().read_text())


def test_failing_commands_lose_their_verified_status(live_check, make_context, monkeypatch):
   seed_readiness(["get-line", "get-lines", "plan-journey", "get-route-paths"])
   results = {
      "get-line": completed(14, stderr=CONTRACT_BROKEN),
      "get-lines": completed(0, stdout=fixture_stdout(make_context, "get-lines")),
      "get-route-paths": completed(0, stdout=fixture_stdout(make_context, "get-route-paths")),
   }
   plan_journey_results = [completed(0, stdout=fixture_stdout(make_context, "plan-journey")), completed(14, stderr=CONTRACT_BROKEN)]

   def fake_run_cli(argv):
      result = plan_journey_results.pop(0) if argv[0] == "plan-journey" else results[argv[0]]
      return result, 1

   monkeypatch.setattr(live_check, "run_cli", fake_run_cli)

   readiness = run_live_check(live_check, "get-line,get-lines,plan-journey,get-route-paths")

   assert readiness["get-line"]["status"] == "failing live: ContractBroken (exit 14)"
   assert readiness["get-lines"]["status"] == "failing live: expected 3 lines"
   assert readiness["plan-journey"]["status"] == "failing live: ContractBroken (exit 14)"
   assert readiness["get-route-paths"]["status"] == "verified live"
   assert readiness["get-route-paths"]["verified_at"] != "old"


def test_a_crash_mid_run_still_records_the_failures_so_far(live_check, monkeypatch):
   seed_readiness(["get-line", "get-lines"])

   def fake_run_cli(argv):
      if argv[0] == "get-lines":
         raise RuntimeError("uv went away")

      return completed(14, stderr=CONTRACT_BROKEN), 1

   monkeypatch.setattr(live_check, "run_cli", fake_run_cli)

   with pytest.raises(RuntimeError):
      live_check.main(["--only", "get-line,get-lines"])

   readiness = json.loads(current_readiness_file().read_text())
   assert readiness["get-line"]["status"] == "failing live: ContractBroken (exit 14)"
   assert readiness["get-lines"]["status"] == "verified live"


def test_a_session_read_that_answers_is_verified_instead_of_left_blocked(live_check, make_context, monkeypatch):
   saved_places = completed(0, stdout=fixture_stdout(make_context, "list-saved-places"))
   monkeypatch.setattr(live_check, "run_cli", lambda argv: (saved_places if argv[0] == "list-saved-places" else completed(10), 1))

   readiness = run_live_check(live_check, "list-saved-places,list-favourites")

   assert readiness["list-saved-places"]["status"] == "verified live"
   assert readiness["list-favourites"]["status"] == "needs session: not yet verified live"


def logging_run_cli(make_context, site_root):
   route_paths = completed(0, stdout=fixture_stdout(make_context, "get-route-paths"))
   request_log = site_root / "var/logs" / "requests-{0}.jsonl".format(datetime.now().strftime("%Y-%m-%d"))

   def fake_run_cli(argv):
      request_log.parent.mkdir(parents=True, exist_ok=True)

      with request_log.open("a") as log:
         log.write(json.dumps({"url": "logged by the CLI under its own root", "run": os.environ.get("CITYMAPPER_RUN_ID")}) + "\n")
         log.write(json.dumps({"url": "logged by another program run at the same time", "run": "someone-else"}) + "\n")

      return route_paths, 1

   return fake_run_cli


def verify_records(site_root):
   verify_logs = list((site_root / "var/logs").glob("verify-*.json"))
   assert len(verify_logs) == 1
   return [json.loads(line) for line in verify_logs[0].read_text().splitlines()]


def test_readiness_logs_and_request_counts_follow_citymapper_root(live_check, make_context, monkeypatch, tmp_path, decoy_default_root):
   site_root = tmp_path / "live-root"
   monkeypatch.setattr(live_check, "run_cli", logging_run_cli(make_context, site_root))

   readiness = run_live_check(live_check, "get-route-paths")

   assert readiness["get-route-paths"]["status"] == "verified live"
   assert [record["requests"] for record in verify_records(site_root)] == [1]
   assert not decoy_default_root.exists()


def test_root_flag_moves_the_run_and_the_child_cli_to_that_root(live_check, make_context, monkeypatch, tmp_path, decoy_default_root):
   flag_root = tmp_path / "flag-root"
   monkeypatch.setattr(live_check, "run_cli", logging_run_cli(make_context, flag_root))

   with pytest.raises(SystemExit):
      live_check.main(["--root", str(flag_root), "--only", "get-route-paths"])

   assert os.environ["CITYMAPPER_ROOT"] == str(flag_root.resolve())
   assert json.loads((flag_root / "var/state/readiness.json").read_text())["get-route-paths"]["status"] == "verified live"
   assert [record["requests"] for record in verify_records(flag_root)] == [1]
   assert not (tmp_path / "live-root").exists()
   assert not decoy_default_root.exists()


def test_an_empty_citymapper_root_refuses_to_start(live_check, monkeypatch, decoy_default_root):
   monkeypatch.setenv("CITYMAPPER_ROOT", "")
   cli_calls = []
   monkeypatch.setattr(live_check, "run_cli", lambda argv: cli_calls.append(argv))

   with pytest.raises(SystemExit) as stopped:
      live_check.main(["--only", "get-route-paths"])

   assert "CITYMAPPER_ROOT is set but empty" in str(stopped.value)
   assert cli_calls == []
   assert not decoy_default_root.exists()
