"""Run model calls on several threads while keeping results in item order."""

from collections.abc import Callable, Hashable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_all[T, R](
    items: Sequence[T],
    call: Callable[[T], R],
    *,
    jobs: int = 1,
    warm_key: Callable[[T], Hashable] | None = None,
    done: Callable[[T, R], None] = lambda item, result: None,
) -> list[R]:
    """Call `call` on every item and return the results in the order of `items`, whatever order the calls finish in.

    `jobs=1` runs the items one after another, in order. With more jobs, up to that many calls run at once.

    `warm_key` is for prompt caching. A call can only read a cached prompt once an earlier call has written it, so the
    first item of each distinct key runs on its own first, and the remaining items start after those finish.

    `done(item, result)` is called on the calling thread as each call finishes, so it can print progress safely.

    An exception from `call` stops new calls from starting, waits for the calls already running, and is raised.
    """
    results: list[R | None] = [None] * len(items)

    if jobs <= 1:
        for index, item in enumerate(items):
            results[index] = call(item)
            done(item, results[index])
        return results

    first_of_each_key, rest = list(range(len(items))), []
    if warm_key is not None:
        seen = set()
        first_of_each_key, rest = [], []
        for index, item in enumerate(items):
            key = warm_key(item)
            (rest if key in seen else first_of_each_key).append(index)
            seen.add(key)

    for wave in (first_of_each_key, rest):
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(call, items[index]): index for index in wave}
            try:
                for future in as_completed(futures):
                    index = futures[future]
                    results[index] = future.result()
                    done(items[index], results[index])
            except BaseException:
                for pending in futures:
                    pending.cancel()
                raise
    return results
