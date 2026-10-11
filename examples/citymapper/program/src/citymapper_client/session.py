import os
from pathlib import Path

from .errors import UsageError

COOKIE_KEY = "CITYMAPPER_COOKIES"
USER_AGENT_KEY = "CITYMAPPER_USER_AGENT"
KEPT_COOKIE_NAMES = ("sessionid", "csrftoken", "uid", "uid_set", "cm_region", "_locale")
SESSION_COOKIE = "sessionid"


def parse_cookie_header(text):
   cookies = {}

   for part in text.replace("\n", ";").split(";"):
      name, separator, value = part.strip().partition("=")
      has_pair = bool(separator) and bool(name.strip())

      if has_pair:
         cookies[name.strip()] = value.strip()

   return cookies


def read_env_file(path):
   values = {}

   if not path.exists():
      return values

   for line in path.read_text().splitlines():
      stripped = line.strip()
      is_assignment = "=" in stripped and not stripped.startswith("#")

      if is_assignment:
         key, _, value = stripped.partition("=")
         values[key.strip()] = value.strip().strip('"')

   return values


class Session:
   def __init__(self, cookies=None, user_agent=None):
      self.cookies = dict(cookies or {})
      self.user_agent = user_agent

   @classmethod
   def from_env(cls, path):
      values = read_env_file(Path(path))
      cookies = parse_cookie_header(values.get(COOKIE_KEY, ""))
      return cls(cookies=cookies, user_agent=values.get(USER_AGENT_KEY) or None)

   @property
   def signed_in(self):
      return bool(self.cookies.get(SESSION_COOKIE))

   def cookie_header(self):
      return "; ".join("{0}={1}".format(name, value) for name, value in self.cookies.items())

   def describe(self):
      return {
         "cookies": {name: "len={0}".format(len(value)) for name, value in self.cookies.items()},
         "has_session_cookie": self.signed_in,
         "user_agent_set": bool(self.user_agent),
      }

   def __repr__(self):
      names = ", ".join("{0}(len={1})".format(name, len(value)) for name, value in self.cookies.items())
      return "Session({0})".format(names)

   def save(self, path):
      path = Path(path)
      kept = {name: value for name, value in self.cookies.items() if name in KEPT_COOKIE_NAMES}

      if SESSION_COOKIE not in kept:
         raise UsageError("No sessionid cookie in the input. Sign in on citymapper.com in your browser, then copy the Cookie header of a citymapper.com request.")

      existing = read_env_file(path)
      existing[COOKIE_KEY] = "; ".join("{0}={1}".format(name, value) for name, value in kept.items())

      if self.user_agent:
         existing[USER_AGENT_KEY] = self.user_agent

      lines = ["{0}={1}".format(key, value) for key, value in existing.items()]
      path.parent.mkdir(parents=True, exist_ok=True)
      descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

      with os.fdopen(descriptor, "w") as handle:
         handle.write("\n".join(lines) + "\n")

      os.chmod(path, 0o600)
      return sorted(kept)
