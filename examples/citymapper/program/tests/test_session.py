import stat

import pytest

from citymapper_client.errors import UsageError
from citymapper_client.session import COOKIE_KEY, Session, parse_cookie_header, read_env_file


def test_parse_cookie_header_reads_pairs_across_separators():
   header = "sessionid=abc123; csrftoken=tok=en==\nuid=dev-9;  junk ; =orphan; _ga=GA1.2.3"

   cookies = parse_cookie_header(header)

   assert cookies == {"sessionid": "abc123", "csrftoken": "tok=en==", "uid": "dev-9", "_ga": "GA1.2.3"}


def test_parse_cookie_header_of_empty_text_is_empty():
   assert parse_cookie_header("") == {}


def test_save_keeps_only_allowed_cookies_with_owner_only_mode(tmp_path):
   env_file = tmp_path / "site" / ".env"
   session = Session(cookies={"sessionid": "s-value", "csrftoken": "c-value", "_ga": "tracker", "cf_clearance": "cf-value"}, user_agent="TestAgent/1.0")

   stored = session.save(env_file)

   saved_cookies = parse_cookie_header(read_env_file(env_file)[COOKIE_KEY])
   assert stored == ["csrftoken", "sessionid"]
   assert saved_cookies == {"sessionid": "s-value", "csrftoken": "c-value"}
   assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_save_tightens_an_existing_world_readable_file_and_keeps_other_keys(tmp_path):
   env_file = tmp_path / ".env"
   env_file.write_text("OTHER_SETTING=keep-me\n")
   env_file.chmod(0o644)

   Session(cookies={"sessionid": "s-value"}).save(env_file)

   values = read_env_file(env_file)
   assert values["OTHER_SETTING"] == "keep-me"
   assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_save_refuses_input_without_sessionid(tmp_path):
   env_file = tmp_path / ".env"
   session = Session(cookies={"csrftoken": "c-value", "uid": "u-value"})

   with pytest.raises(UsageError):
      session.save(env_file)

   assert not env_file.exists()


def test_repr_shows_names_and_lengths_but_not_values():
   session = Session(cookies={"sessionid": "secret-session-value", "uid": "secret-uid"})

   text = repr(session)

   assert "sessionid(len=20)" in text
   assert "uid(len=10)" in text
   assert "secret" not in text


def test_describe_shows_lengths_but_not_values():
   session = Session(cookies={"sessionid": "secret-session-value"})

   description = session.describe()

   assert description["cookies"] == {"sessionid": "len=20"}
   assert description["has_session_cookie"] is True
   assert "secret" not in str(description)


def test_save_preserves_comments_blank_lines_and_quotes_in_other_lines(tmp_path):
   env_file = tmp_path / ".env"
   env_file.write_text('# my notes\nOTHER="a b"\n\nCITYMAPPER_COOKIES=sessionid=old\n')

   Session(cookies={"sessionid": "abc"}).save(env_file)

   assert env_file.read_text() == '# my notes\nOTHER="a b"\n\nCITYMAPPER_COOKIES=sessionid=abc\n'


def test_save_failure_leaves_previous_env_file_intact(tmp_path, monkeypatch):
   env_file = tmp_path / ".env"
   env_file.write_text("CITYMAPPER_COOKIES=sessionid=old\n")

   def failing_replace(source, destination):
      raise OSError("disk full")

   monkeypatch.setattr("citymapper_client.session.os.replace", failing_replace)

   with pytest.raises(OSError):
      Session(cookies={"sessionid": "new"}).save(env_file)

   assert env_file.read_text() == "CITYMAPPER_COOKIES=sessionid=old\n"
   assert [entry.name for entry in tmp_path.iterdir()] == [".env"]


@pytest.mark.parametrize("header", ["\nCookie: sessionid=a; csrftoken=b", "  cookie: sessionid=a; csrftoken=b\n"])
def test_parse_cookie_header_ignores_surrounding_whitespace_and_prefix(header):
   cookies = parse_cookie_header(header)

   assert cookies["sessionid"] == "a"
   assert cookies["csrftoken"] == "b"
