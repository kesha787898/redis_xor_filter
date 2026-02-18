import time
from collections.abc import Callable
from typing import Dict, List, Any


def eval_time(func: Callable, *args: List[Any], **kwargs: Dict[str, Any]):
    t1 = time.perf_counter_ns()
    func(*args, **kwargs)
    t2 = time.perf_counter_ns()
    dt = t2 - t1
    return dt / 10 ** 9
