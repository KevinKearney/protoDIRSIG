"""C-06's position as built: DIRSIG's `--log_info` JSON is a disagreement flag, never authoritative over the run spec.
`Simulation._check_log` (the DIRSIG dry run's check) reports a log whose captures, task windows or reference time
disagree with the run spec as problems, and leaves the run spec as it was. Synthetic logs; no DIRSIG needed."""
import copy
from types import SimpleNamespace

from manifold.engines.dirsig.simulation import Simulation

SPEC = {"descriptor": {"collection": {"epoch": "2009-07-27T19:29:32Z"}},
        "engine": {"tasks": {"windows": [{"start": 0.0, "stop": 0.0}, {"start": 10.0, "stop": 12.0}]}}}


def _log(captures=((0, 0.0), (1, 10.5)), reference="2009-07-27T19:29:32+00:00"):
    return {"capture_list": [{"capture_index": i, "task_index": t, "relative_time_window": [t0, t0]}
                             for i, (t, t0) in enumerate(captures)],
            "run_info": {"reference_date_time": reference}}


def _check(log):
    holder = SimpleNamespace(spec=copy.deepcopy(SPEC))
    problems = Simulation._check_log(holder, log)
    assert holder.spec == SPEC                                       # the run spec stays authoritative
    return problems


def test_a_log_that_agrees_raises_no_flag():
    assert _check(_log()) == []


def test_each_disagreement_is_flagged():
    assert any("expected 2 capture(s)" in p for p in _check(_log(captures=((0, 0.0),))))
    assert any("outside window" in p for p in _check(_log(captures=((0, 0.0), (1, 13.0)))))
    assert any("task_index 5" in p for p in _check(_log(captures=((0, 0.0), (5, 10.0)))))
    assert any("reference datetime" in p for p in _check(_log(reference="2009-07-27T19:29:33+00:00")))
