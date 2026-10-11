import fcntl
import json
import math
import os
import random
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .errors import ChallengeRequired, RateLimited

DEFAULT_MINIMUM_GAP_SECONDS = 3.0
DEFAULT_JITTER_RANGE = (0.2, 0.4)
HALT_SECONDS_AFTER_THROTTLE = 900
UNREADABLE_REASON = "unreadable pacer state"


class Pacer:
   def __init__(self, state_file, minimum_gap=DEFAULT_MINIMUM_GAP_SECONDS, jitter_range=DEFAULT_JITTER_RANGE, clock=time.time, sleeper=time.sleep, randomness=random.uniform):
      self.state_file = Path(state_file)
      self.lock_file = self.state_file.with_suffix(".lock")
      self.minimum_gap = minimum_gap
      self.jitter_range = jitter_range
      self.clock = clock
      self.sleeper = sleeper
      self.randomness = randomness

   def _load_state(self, persist_unreadable=False):
      try:
         state = json.loads(self.state_file.read_text())
      except FileNotFoundError:
         return {}
      except ValueError:
         state = None

      if isinstance(state, dict):
         return state

      # A torn or hand-edited file may have held a halt, so it fails closed. The halt is written back
      # under the lock so it expires once, instead of restarting its window on every read.
      now = self.clock()
      fail_closed_state = {"last_request_at": now, "halted_until": now + HALT_SECONDS_AFTER_THROTTLE, "halt_reason": UNREADABLE_REASON}

      if persist_unreadable:
         self._write_state(fail_closed_state)

      return fail_closed_state

   def _write_state(self, state):
      self.state_file.parent.mkdir(parents=True, exist_ok=True)
      descriptor, temporary_path = tempfile.mkstemp(dir=self.state_file.parent, prefix=self.state_file.name + ".", suffix=".tmp")

      try:
         with os.fdopen(descriptor, "w") as handle:
            handle.write(json.dumps(state))

         os.replace(temporary_path, self.state_file)
      except BaseException:
         Path(temporary_path).unlink(missing_ok=True)
         raise

   @contextmanager
   def _exclusive_lock(self):
      self.lock_file.parent.mkdir(parents=True, exist_ok=True)

      with open(self.lock_file, "a") as lock_handle:
         fcntl.flock(lock_handle, fcntl.LOCK_EX)

         try:
            yield
         finally:
            fcntl.flock(lock_handle, fcntl.LOCK_UN)

   def _raise_if_halted(self, state):
      halted_until = state.get("halted_until", 0)
      seconds_left = halted_until - self.clock()

      if seconds_left <= 0:
         return

      reason = state.get("halt_reason", "throttle")
      error_type = ChallengeRequired if reason == "challenge" else RateLimited
      raise error_type("The client stopped itself after a {0} and stays stopped for {1} more seconds.".format(reason, math.ceil(seconds_left)), {"halted_until": halted_until, "reason": reason})

   @contextmanager
   def turn(self):
      # The lock is held from the wait until the response is back, so several CLI processes still
      # keep one request in flight and the gap runs from the end of the previous response.
      with self._exclusive_lock():
         state = self._load_state(persist_unreadable=True)
         self._raise_if_halted(state)
         jitter = self.randomness(*self.jitter_range) if self.minimum_gap else 0
         required_gap = self.minimum_gap * (1 + jitter)
         elapsed = self.clock() - state.get("last_request_at", 0)

         if elapsed < required_gap:
            self.sleeper(required_gap - elapsed)

         try:
            yield
         finally:
            state = self._load_state(persist_unreadable=True)
            state["last_request_at"] = self.clock()
            self._write_state(state)

   def halt(self, reason):
      with self._exclusive_lock():
         state = self._load_state(persist_unreadable=True)
         state["halted_until"] = self.clock() + HALT_SECONDS_AFTER_THROTTLE
         state["halt_reason"] = reason
         self._write_state(state)

   def status(self):
      state = self._load_state()
      seconds_left = state.get("halted_until", 0) - self.clock()
      is_halted = seconds_left > 0

      return {
         "halted": is_halted,
         "halt_reason": state.get("halt_reason") if is_halted else None,
         "seconds_remaining": math.ceil(seconds_left) if is_halted else 0,
         "minimum_gap_seconds": self.minimum_gap,
      }
