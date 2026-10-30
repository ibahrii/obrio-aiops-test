import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.simulate_failures import SCENARIOS, check, run_scenario  # noqa: E402


@pytest.mark.parametrize("name,plan,expect", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_failure_scenario(name, plan, expect):
    res, calls, sleeps, logged = run_scenario(plan)
    assert check(res, sleeps, expect) == []
    if expect.get("category") != "unclassified" and len(calls) > 1:
        assert logged, "every failure must be logged"
