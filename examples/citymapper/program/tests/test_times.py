from datetime import datetime, timezone

import pytest

TOKYO_EVENING = datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc)


@pytest.fixture
def portvale(make_context):
   context, _ = make_context()
   return context, context.region("portvale")


def test_a_clock_time_already_past_today_means_tomorrow(portvale):
   context, region = portvale

   assert context.to_utc_iso(region, "07:00", now=TOKYO_EVENING) == "2026-10-10T22:00:00.000Z"


def test_a_clock_time_later_today_stays_today(portvale):
   context, region = portvale

   assert context.to_utc_iso(region, "22:30", now=TOKYO_EVENING) == "2026-10-10T13:30:00.000Z"


def test_a_clock_time_that_just_passed_stays_today(portvale):
   context, region = portvale

   assert context.to_utc_iso(region, "19:50", now=TOKYO_EVENING) == "2026-10-10T10:50:00.000Z"


def test_an_iso_date_is_never_moved(portvale):
   context, region = portvale

   assert context.to_utc_iso(region, "2026-10-09T07:00", now=TOKYO_EVENING) == "2026-10-08T22:00:00.000Z"
