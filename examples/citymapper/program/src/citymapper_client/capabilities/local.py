import sys
from pathlib import Path

from ..errors import UsageError
from ..session import Session, parse_cookie_header


def read_cookie_file(file_text):
   cookie_path = Path(file_text).expanduser()

   try:
      return cookie_path.read_text()
   except (OSError, UnicodeDecodeError) as error:
      has_os_reason = isinstance(error, OSError) and bool(error.strerror)
      reason = error.strerror if has_os_reason else type(error).__name__
      raise UsageError("Cannot read --from-file {0}: {1}".format(cookie_path, reason), {"from_file": str(cookie_path)}) from error


def adopt_session(context, arguments):
   if arguments.get("from_file"):
      text = read_cookie_file(arguments["from_file"])
   elif arguments.get("stdin"):
      text = sys.stdin.read()
   else:
      raise UsageError("Pass --stdin and pipe the Cookie header in, or pass --from-file with a file that holds it.")

   text = text.strip()

   if text.lower().startswith("cookie:"):
      text = text.split(":", 1)[1]

   session = Session(cookies=parse_cookie_header(text), user_agent=context.session.user_agent)
   stored = session.save(context.env_file)
   return {"stored": stored, "path": str(context.env_file), "lengths": {name: len(session.cookies[name]) for name in stored}}
