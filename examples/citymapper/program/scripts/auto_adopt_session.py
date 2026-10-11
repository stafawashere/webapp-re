# /// script
# requires-python = ">=3.13"
# dependencies = ["cryptography>=43"]
# ///
"""Copy the Citymapper session from the Helium browser into the program's .env.

Reads the citymapper.com cookies from Helium's cookie store, decrypts them with Helium's storage
key from the login keychain, and pipes the Cookie header into `citymapper adopt-session --stdin`.
When Helium holds no live session, it opens citymapper.com in Helium and waits for you to sign in.
Cookie values never reach argv or stdout; only cookie names and lengths are printed.

   uv run --script scripts/auto_adopt_session.py [--profile Default] [--wait 300]

The first run makes macOS ask whether this may read Helium's storage key. "Always Allow" makes
later runs silent.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PROGRAM_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = PROGRAM_DIR.parent
HELIUM_APP = "Helium"
HELIUM_DATA_DIR = Path.home() / "Library/Application Support/net.imput.helium"
KEYCHAIN_SERVICES = ("Helium Safe Storage", "Helium Storage Key")
SIGN_IN_URL = "https://citymapper.com/"
COOKIE_DOMAIN = "citymapper.com"
SESSION_COOKIE = "sessionid"
ENCRYPTED_PREFIX = b"v10"
KEY_SALT = b"saltysalt"
KEY_ITERATIONS = 1003
KEY_LENGTH = 16
CBC_IV = b" " * 16
HOST_DIGEST_LENGTH = 32
CHROMIUM_EPOCH_OFFSET_SECONDS = 11644473600
POLL_SECONDS = 5
STOP_EXIT_CODES = {11: "ChallengeRequired", 12: "RateLimited"}


class AdoptError(Exception):
   pass


def keychain_keys(services):
   keys = []

   for service in services:
      result = subprocess.run(
         ["security", "find-generic-password", "-w", "-s", service],
         capture_output=True,
         text=True,
      )

      if result.returncode == 0:
         keys.append((service, derive_key(result.stdout.strip())))

   if not keys:
      tried = ", ".join(services)
      raise AdoptError(
         "No Helium storage key in the login keychain (tried {0}). Open Keychain Access, search for "
         "Helium, and pass its name with --keychain-service.".format(tried)
      )

   return keys


def derive_key(password):
   return hashlib.pbkdf2_hmac("sha1", password.encode(), KEY_SALT, KEY_ITERATIONS, KEY_LENGTH)


def decrypt_value(encrypted_value, key, host_key):
   if not encrypted_value.startswith(ENCRYPTED_PREFIX):
      raise AdoptError("unknown encryption prefix {0!r}".format(encrypted_value[:3]))

   ciphertext = encrypted_value[len(ENCRYPTED_PREFIX):]
   decryptor = Cipher(algorithms.AES(key), modes.CBC(CBC_IV)).decryptor()
   unpadder = padding.PKCS7(128).unpadder()

   try:
      padded = decryptor.update(ciphertext) + decryptor.finalize()
      plain = unpadder.update(padded) + unpadder.finalize()
   except ValueError as error:
      raise AdoptError("bad padding, so the key is wrong") from error

   host_digest = hashlib.sha256(host_key.encode()).digest()
   has_host_digest = plain[:HOST_DIGEST_LENGTH] == host_digest

   if has_host_digest:
      plain = plain[HOST_DIGEST_LENGTH:]

   try:
      return plain.decode()
   except UnicodeDecodeError as error:
      raise AdoptError("decrypted to non-text, so the key is wrong") from error


def decrypt_with_any_key(encrypted_value, keys, host_key, name):
   failures = []

   for service, key in keys:
      try:
         return decrypt_value(encrypted_value, key, host_key)
      except AdoptError as error:
         failures.append("{0}: {1}".format(service, error))

   raise AdoptError("Could not decrypt the {0} cookie for {1} ({2}). Run with --diagnose.".format(name, host_key, "; ".join(failures)))


def cookie_database(profile):
   profile_dir = HELIUM_DATA_DIR / profile
   candidates = (profile_dir / "Cookies", profile_dir / "Network" / "Cookies")

   for candidate in candidates:
      if candidate.exists():
         return candidate

   raise AdoptError("No Helium cookie store under {0}. Pass --profile with your profile's folder name.".format(profile_dir))


def read_cookie_rows(database):
   with tempfile.TemporaryDirectory() as scratch:
      copy = Path(scratch) / database.name
      shutil.copy2(database, copy)
      write_ahead_log = database.with_name(database.name + "-wal")

      if write_ahead_log.exists():
         shutil.copy2(write_ahead_log, copy.with_name(copy.name + "-wal"))

      connection = sqlite3.connect(copy)

      try:
         version_row = connection.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()
         rows = connection.execute(
            "SELECT host_key, name, value, encrypted_value, expires_utc FROM cookies "
            "WHERE host_key = ? OR host_key LIKE ?",
            (COOKIE_DOMAIN, "%." + COOKIE_DOMAIN),
         ).fetchall()
      finally:
         connection.close()

   return int(version_row[0]), rows


def is_expired(expires_utc, now):
   is_browser_session_cookie = expires_utc == 0
   expires_at = expires_utc / 1_000_000 - CHROMIUM_EPOCH_OFFSET_SECONDS
   has_passed = expires_at <= now
   return has_passed and not is_browser_session_cookie


def helium_cookies(profile, keys):
   _, rows = read_cookie_rows(cookie_database(profile))
   now = time.time()
   cookies = {}

   for host_key, name, value, encrypted_value, expires_utc in rows:
      if is_expired(expires_utc, now):
         continue

      cookies[name] = value or decrypt_with_any_key(encrypted_value, keys, host_key, name)

   return cookies


def diagnose(profile, services):
   report = {"profile": profile, "keychain": {}, "cookies": []}

   for service in services:
      result = subprocess.run(["security", "find-generic-password", "-s", service], capture_output=True, text=True)
      report["keychain"][service] = "found" if result.returncode == 0 else "missing"

   database = cookie_database(profile)
   version, rows = read_cookie_rows(database)
   report["database"] = str(database)
   report["database_version"] = version
   keys = keychain_keys(services)
   now = time.time()

   for host_key, name, value, encrypted_value, expires_utc in rows:
      outcomes = {}

      for service, key in keys:
         try:
            outcomes[service] = "ok, length {0}".format(len(decrypt_value(encrypted_value, key, host_key)))
         except AdoptError as error:
            outcomes[service] = str(error)

      report["cookies"].append({
         "host": host_key,
         "name": name,
         "plain_value_length": len(value),
         "prefix": encrypted_value[:3].decode("latin-1"),
         "encrypted_length": len(encrypted_value),
         "expired": is_expired(expires_utc, now),
         "decrypt": "not encrypted" if value else outcomes,
      })

   return report


def run_citymapper(env_file, arguments, stdin_text=None):
   command = ["uv", "run", "--project", str(PROGRAM_DIR), "citymapper", "--env-file", str(env_file), *arguments]
   result = subprocess.run(command, input=stdin_text, capture_output=True, text=True)
   stopped_class = STOP_EXIT_CODES.get(result.returncode)

   if stopped_class:
      raise AdoptError("Citymapper answered {0}; run `citymapper help` for the pacer's wait before trying again.".format(stopped_class))

   if result.returncode != 0:
      raise AdoptError("citymapper {0} failed (exit {1}): {2}".format(arguments[0], result.returncode, result.stderr.strip()))

   return json.loads(result.stdout)


def adopt(env_file, cookies):
   header = "; ".join("{0}={1}".format(name, value) for name, value in cookies.items())
   run_citymapper(env_file, ["adopt-session", "--stdin"], stdin_text=header)
   whoami = run_citymapper(env_file, ["whoami"])
   return whoami.get("signed_in") is True


def wait_for_session(profile, keys, env_file, wait_seconds):
   deadline = time.monotonic() + wait_seconds
   rejected_session = None
   opened_sign_in = False

   while True:
      cookies = helium_cookies(profile, keys)
      session_value = cookies.get(SESSION_COOKIE)
      is_untried_session = session_value is not None and session_value != rejected_session

      if is_untried_session:
         if adopt(env_file, cookies):
            return cookies

         rejected_session = session_value

      if time.monotonic() >= deadline:
         raise AdoptError("No signed-in Citymapper session showed up in Helium within {0} s.".format(wait_seconds))

      if not opened_sign_in:
         subprocess.run(["open", "-a", HELIUM_APP, SIGN_IN_URL], check=False)
         print("Sign in to Citymapper in the Helium window; waiting up to {0} s.".format(wait_seconds), file=sys.stderr)
         opened_sign_in = True

      time.sleep(POLL_SECONDS)


def main():
   parser = argparse.ArgumentParser(description="Adopt the Citymapper session from the Helium browser.")
   parser.add_argument("--profile", default="Default", help="Helium profile folder, such as Default or 'Profile 1'")
   parser.add_argument("--env-file", default=str(SITE_DIR / ".env"))
   parser.add_argument("--wait", type=int, default=300, help="seconds to wait for you to sign in")
   parser.add_argument("--keychain-service", action="append", help="keychain item holding Helium's storage key")
   parser.add_argument("--diagnose", action="store_true", help="report why each cookie does or does not decrypt, without values; adopts nothing")
   options = parser.parse_args()

   services = tuple(options.keychain_service or KEYCHAIN_SERVICES)

   try:
      if options.diagnose:
         print(json.dumps(diagnose(options.profile, services), indent=3))
         return 0

      keys = keychain_keys(services)
      cookies = wait_for_session(options.profile, keys, Path(options.env_file), options.wait)
   except AdoptError as error:
      print(json.dumps({"adopted": False, "error": str(error)}))
      return 1

   lengths = {name: len(value) for name, value in cookies.items()}
   print(json.dumps({"adopted": True, "signed_in": True, "profile": options.profile, "cookies": lengths}))
   return 0


if __name__ == "__main__":
   sys.exit(main())
