import threading
import time

import pytest

from evals.runner.client import FatalModelError
from evals.runner.parallel import run_all


class Gauge:
    """Counts how many calls are inside `enter()` at the same moment."""

    def __init__(self):
        self.lock = threading.Lock()
        self.now = 0
        self.peak = 0

    def enter(self, pause=0.05):
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)
        time.sleep(pause)
        with self.lock:
            self.now -= 1


def test_one_job_runs_the_items_in_order_one_at_a_time():
    seen, gauge = [], Gauge()

    def call(item):
        gauge.enter(0)
        seen.append(item)
        return item * 2

    assert run_all([1, 2, 3, 4], call, jobs=1) == [2, 4, 6, 8]
    assert seen == [1, 2, 3, 4]
    assert gauge.peak == 1


def test_several_calls_are_in_flight_at_once():
    gauge = Gauge()
    run_all(list(range(8)), lambda item: gauge.enter(), jobs=4)
    assert gauge.peak == 4


def test_no_more_than_the_given_number_of_calls_run_at_once():
    gauge = Gauge()
    run_all(list(range(12)), lambda item: gauge.enter(0.02), jobs=3)
    assert gauge.peak <= 3


def test_results_keep_the_item_order_whatever_order_the_calls_finish_in():
    finished = []

    def call(item):
        time.sleep((5 - item) * 0.03)  # the first item is the slowest
        finished.append(item)
        return f"result {item}"

    results = run_all([0, 1, 2, 3, 4], call, jobs=5)
    assert finished != [0, 1, 2, 3, 4]
    assert results == [f"result {i}" for i in range(5)]


def test_done_is_called_for_every_item_on_the_calling_thread():
    caller = threading.get_ident()
    seen = []

    def done(item, result):
        seen.append((item, result, threading.get_ident()))

    run_all([1, 2, 3], lambda item: item + 10, jobs=3, done=done)
    assert sorted((item, result) for item, result, _ in seen) == [(1, 11), (2, 12), (3, 13)]
    assert {thread for *_, thread in seen} == {caller}


def test_the_first_item_of_each_key_finishes_before_any_other_item_starts():
    events, lock = [], threading.Lock()

    def call(item):
        with lock:
            events.append(("start", item))
        time.sleep(0.05 if item in ("a1", "b1") else 0)
        with lock:
            events.append(("end", item))

    items = ["a1", "a2", "a3", "b1", "b2"]
    run_all(items, call, jobs=5, warm_key=lambda item: item[0])

    position = {event: n for n, event in enumerate(events)}
    first_wave_ends = max(position[("end", "a1")], position[("end", "b1")])
    for later in ("a2", "a3", "b2"):
        assert position[("start", later)] > first_wave_ends


def test_without_a_warm_key_every_item_may_start_at_once():
    gauge = Gauge()
    run_all(["a", "a", "a", "a"], lambda item: gauge.enter(), jobs=4)
    assert gauge.peak == 4


def test_a_fatal_error_stops_new_calls_and_is_raised():
    started = []

    def call(item):
        started.append(item)
        if item == 0:
            raise FatalModelError("bad key")
        time.sleep(0.05)

    with pytest.raises(FatalModelError, match="bad key"):
        run_all(list(range(20)), call, jobs=2)
    assert len(started) < 20


def test_a_fatal_error_in_the_first_wave_means_the_second_wave_never_starts():
    started = []

    def call(item):
        started.append(item)
        if item == "a1":
            raise FatalModelError("bad key")

    with pytest.raises(FatalModelError):
        run_all(["a1", "a2", "a3"], call, jobs=3, warm_key=lambda item: item[0])
    assert started == ["a1"]


def test_a_fatal_error_with_one_job_stops_at_once():
    started = []

    def call(item):
        started.append(item)
        raise FatalModelError("bad key")

    with pytest.raises(FatalModelError):
        run_all([1, 2, 3], call, jobs=1)
    assert started == [1]


def test_no_items_is_fine():
    assert run_all([], lambda item: item, jobs=4) == []
