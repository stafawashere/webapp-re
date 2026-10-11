import pytest

from citymapper_client.errors import ChallengeRequired, RateLimited
from citymapper_client.pacing import HALT_SECONDS_AFTER_THROTTLE, UNREADABLE_REASON, Pacer

FIXED_JITTER = 0.3


class FakeClock:
   def __init__(self, start=1_000_000.0):
      self.now = start
      self.sleeps = []

   def __call__(self):
      return self.now

   def sleep(self, seconds):
      self.sleeps.append(seconds)
      self.now += seconds


def build_pacer(tmp_path, clock, jitter_calls=None):
   def fixed_jitter(low, high):
      if jitter_calls is not None:
         jitter_calls.append((low, high))

      return FIXED_JITTER

   return Pacer(tmp_path / "state" / "pacer.json", minimum_gap=3.0, jitter_range=(0.2, 0.4), clock=clock, sleeper=clock.sleep, randomness=fixed_jitter)


def take_turn(pacer):
   with pacer.turn():
      pass


def test_first_turn_does_not_wait(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)

   take_turn(pacer)

   assert clock.sleeps == []


def test_back_to_back_turns_wait_the_gap_with_jitter(tmp_path):
   clock = FakeClock()
   jitter_calls = []
   pacer = build_pacer(tmp_path, clock, jitter_calls)

   take_turn(pacer)
   take_turn(pacer)

   assert clock.sleeps == [pytest.approx(3.0 * (1 + FIXED_JITTER))]
   assert jitter_calls[-1] == (0.2, 0.4)


def test_wait_counts_time_already_elapsed(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)

   take_turn(pacer)
   clock.now += 1.0
   take_turn(pacer)

   assert clock.sleeps == [pytest.approx(3.0 * (1 + FIXED_JITTER) - 1.0)]


def test_no_wait_once_the_gap_has_passed(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)

   take_turn(pacer)
   clock.now += 10.0
   take_turn(pacer)

   assert clock.sleeps == []


def test_gap_is_shared_through_the_state_file(tmp_path):
   clock = FakeClock()
   first_process = build_pacer(tmp_path, clock)
   second_process = build_pacer(tmp_path, clock)

   take_turn(first_process)
   take_turn(second_process)

   assert len(clock.sleeps) == 1


def test_throttle_halt_makes_turn_raise_rate_limited(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)

   pacer.halt("throttle")

   with pytest.raises(RateLimited) as caught:
      take_turn(pacer)

   assert caught.value.detail["reason"] == "throttle"
   assert pacer.status()["halted"] is True


def test_challenge_halt_makes_turn_raise_challenge_required(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)

   pacer.halt("challenge")

   with pytest.raises(ChallengeRequired):
      take_turn(pacer)


def test_halt_expires_after_the_halt_window(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)

   pacer.halt("throttle")
   clock.now += HALT_SECONDS_AFTER_THROTTLE + 1
   take_turn(pacer)

   assert pacer.status()["halted"] is False


@pytest.mark.parametrize("damaged_state", ["{\"last_request_at\": 12", "[1, 2, 3]", "null"])
def test_unreadable_state_file_fails_closed(tmp_path, damaged_state):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)
   pacer.state_file.parent.mkdir(parents=True, exist_ok=True)
   pacer.state_file.write_text(damaged_state)

   with pytest.raises(RateLimited) as caught:
      take_turn(pacer)

   assert caught.value.detail["reason"] == UNREADABLE_REASON
   assert pacer.status()["halted"] is True


def test_unreadable_state_file_halts_once_then_expires(tmp_path):
   clock = FakeClock()
   pacer = build_pacer(tmp_path, clock)
   pacer.state_file.parent.mkdir(parents=True, exist_ok=True)
   pacer.state_file.write_text("{not json")

   with pytest.raises(RateLimited):
      take_turn(pacer)

   clock.now += 100
   assert pacer.status()["seconds_remaining"] == HALT_SECONDS_AFTER_THROTTLE - 100

   clock.now += HALT_SECONDS_AFTER_THROTTLE
   take_turn(pacer)

   assert pacer.status()["halted"] is False
