import random
import time
from math import ceil
from typing import List

import numpy as np
from tqdm import tqdm

from reports.src.reports.tools.filters.IFilter import IFilter


def eval_latency(
        filt: IFilter,
        presented_data: List,
        not_presented_data: List,
):
    data = presented_data + not_presented_data

    random.seed(42)
    random.shuffle(data)

    batch_size = 1000 if len(data) > 10000 else 100
    batch_latencies = []
    n_batches = ceil(len(data) / batch_size)
    warmup_steps = max(1, int(n_batches * 0.1))
    idx = 0
    for start in tqdm(
            range(0, len(data), batch_size),
            desc="eval_latency",
    ):
        idx += 1
        batch = data[start:start + batch_size]
        start_ns = time.perf_counter_ns()

        for item in batch:
            filt.exists(item)

        end_ns = time.perf_counter_ns()
        if idx > warmup_steps:
            batch_latencies.append(
                (end_ns - start_ns) / len(batch)
            )

    latencies = np.array(batch_latencies)

    return {
        "latency_mean_ns": latencies.mean(),
        "latency_std_ns": latencies.std(ddof=1),
        "latency_p50_ns": np.percentile(latencies, 50),
        "latency_p90_ns": np.percentile(latencies, 90),
        "latency_p95_ns": np.percentile(latencies, 95),
        "latency_p99_ns": np.percentile(latencies, 99),
        "latency_min_ns": latencies.min(),
        "latency_max_ns": latencies.max(),
        "latency_n_object": len(data),
        "latency_n_batch": len(latencies),
        "latency_batch_size": batch_size,
    }


def eval_quality(filt: IFilter, presented_data: List, not_presented_data: List):
    t1 = time.perf_counter_ns()
    fn = len(presented_data) - filt.check_batch(presented_data)
    fp = filt.check_batch(not_presented_data)
    t2 = time.perf_counter_ns()
    return {
        "quality_FN": fn,
        "quality_FP": fp,
        "quality_FPR": fp / len(not_presented_data),
        "quality_FNR": fn / len(presented_data),
        "quality_presented_data": len(presented_data),
        "quality_not_presented_data": len(not_presented_data),
        "quality_debug_time": t2 - t1,
        "quality_debug_time_per_object": (t2 - t1) / (len(presented_data) + len(not_presented_data)),
    }
