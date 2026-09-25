"""Regression test: personalization_lookup must never introduce a delay that
can exceed the 200 ms request budget.

The defect (deploy 36154305921) added a random sleep of 150-300 ms on ~30%
of calls via SLOW_LOOKUP_RATE / SLOW_LOOKUP_RANGE_S.  This test catches that
by running the *real* (un-monkeypatched) personalization_lookup many times and
asserting every call finishes well within the budget.
"""

import time

from app.api import BUDGET_MS, personalization_lookup


def test_personalization_lookup_never_exceeds_budget() -> None:
    """personalization_lookup must always complete in < BUDGET_MS (200 ms).

    With a 30 % slow-path probability, 50 iterations gives a >99.99 % chance
    of triggering at least one slow call if the defect is present.
    """
    max_allowed_s = BUDGET_MS / 1000          # 0.200 s
    iterations = 50

    for i in range(iterations):
        start = time.perf_counter()
        personalization_lookup(str(i))
        elapsed = time.perf_counter() - start

        assert elapsed < max_allowed_s, (
            f"personalization_lookup('{i}') took {elapsed * 1000:.1f} ms, "
            f"which exceeds the {BUDGET_MS} ms request budget"
        )
