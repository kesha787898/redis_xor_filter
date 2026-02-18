from time import sleep

import redis
import pandas as pd

from reports.src.reports.cmd_tools import get_peak, start_container, stop_container
from reports.src.reports.load_data import load_data
from reports.src.reports.tools.filters.BloomFilter import BloomFilter
from reports.src.reports.tools.filters.CuckooFilter import CuckooFilter
from reports.src.reports.tools.filters.IFilter import IFilter
from reports.src.reports.tools.filters.XorFilter import XorFilter
from reports.src.reports.tools.metric_evaluator import eval_latency, eval_quality
from reports.src.reports.tools.time_eval import eval_time

DEBUG = False
if DEBUG:
    MILLION = 10 ** 6
    sizes_millions = [0.1]
    TEST_SIZE_PRESENTED_TIME = 2 * 10 ** 2
    TEST_SIZE_NOT_PRESENTED_TIME = 2 * 10 ** 2
    TEST_SIZE_PRESENTED_QUALITY = 10 ** 2
    TEST_SIZE_NOT_PRESENTED_QUALITY = 10 ** 2
    err_rates_bloom = [
        1 / 15,  # XOR FP4
        1 / 255,  # XOR FP8
        1 / 65535,  # XOR FP16
        1 / (2 ** 32 - 1),  # XOR FP32
    ]
    fp_sizes_xor = [4, 8, 16, 32]
    cuckoo_bucket_sizes = [1, 2, 4, 8]

else:
    MILLION = 10 ** 6
    sizes_millions = [10, 100]
    TEST_SIZE_PRESENTED_TIME = 10 ** 6
    TEST_SIZE_NOT_PRESENTED_TIME = 10 ** 6
    TEST_SIZE_PRESENTED_QUALITY = 10 ** 7
    TEST_SIZE_NOT_PRESENTED_QUALITY = 10 ** 7
    err_rates_bloom = [
        1 / 15,  # XOR FP4
        1 / 255,  # XOR FP8
        1 / 65535,  # XOR FP16
        1 / (2 ** 32 - 1),  # XOR FP32
    ]
    fp_sizes_xor = [4, 8, 16, 32]
    cuckoo_bucket_sizes = [1, 2, 4, 8]

stop_container("reddis")
HOST = "localhost"
PORT = 6380
l_d_bloom = []
l_d_xor = []
l_d_cuckoo = []
l_d_ping = []
for size_millions in reversed(sizes_millions):
    ###xor
    for fpp_size in fp_sizes_xor:
        start_container("reddis")
        r = redis.Redis(host=HOST, port=PORT, decode_responses=True, socket_timeout=None)
        r.flushall()

        train = load_data("../../data/weakpass_4.txt", start=0, max_obj=size_millions * MILLION)

        sleep(15)
        xor = XorFilter(r, f"xor_{size_millions}M_{fpp_size}", fpp_size)
        time = eval_time(xor.add_many, train)
        mem = xor.get_mem_usage()
        additional_mem = xor.get_additional_memory()

        presented_data_latency = load_data("../../data/weakpass_4.txt",
                                           start=0,
                                           max_obj=min(size_millions * MILLION, TEST_SIZE_PRESENTED_TIME))
        not_presented_latency = load_data("../../data/weakpass_4.txt",
                                          start=size_millions * MILLION,
                                          max_obj=TEST_SIZE_NOT_PRESENTED_TIME)
        sleep(15)
        latency_metrics = eval_latency(xor, presented_data_latency, not_presented_latency)

        presented_data_quality = load_data("../../data/weakpass_4.txt",
                                           start=0,
                                           max_obj=min(size_millions * MILLION, TEST_SIZE_PRESENTED_QUALITY))
        not_presented_quality = load_data("../../data/weakpass_4.txt",
                                          start=size_millions * MILLION,
                                          max_obj=TEST_SIZE_NOT_PRESENTED_QUALITY)
        quality_metrics = eval_quality(xor, presented_data_quality, not_presented_quality)
        l_d_xor.append(
            {"size_millions": size_millions,
             "fpp_size": fpp_size,
             "time_sec": time,
             "mem_mb": mem,
             "info": xor.info(),
             "peak_memory_mb": get_peak("reddis"),
             "additional_mem_mb": additional_mem,
             **latency_metrics,
             **quality_metrics
             }
        )
        xor.save_to_file(f"output/{xor.name}",
                         redis.Redis(host=HOST, port=PORT, decode_responses=False, socket_timeout=10))
        stop_container('reddis')
    ###Bloom
    for err_rate in err_rates_bloom:
        start_container("reddis")
        r = redis.Redis(host=HOST, port=PORT, decode_responses=True, socket_timeout=None)
        r.flushall()

        train = load_data("../../data/weakpass_4.txt", start=0, max_obj=size_millions * MILLION)
        bloom = BloomFilter(reddis=r, name=f"bloom_{size_millions}M_{err_rate}", err_rate=err_rate)
        sleep(15)
        time = eval_time(bloom.add_many, train)
        mem = bloom.get_mem_usage()

        presented_data_latency = load_data("../../data/weakpass_4.txt",
                                           start=0,
                                           max_obj=min(size_millions * MILLION, TEST_SIZE_PRESENTED_TIME))
        not_presented_latency = load_data("../../data/weakpass_4.txt",
                                          start=size_millions * MILLION,
                                          max_obj=TEST_SIZE_NOT_PRESENTED_TIME)
        sleep(15)
        latency_metrics = eval_latency(bloom, presented_data_latency, not_presented_latency)

        presented_data_quality = load_data("../../data/weakpass_4.txt",
                                           start=0,
                                           max_obj=min(size_millions * MILLION, TEST_SIZE_PRESENTED_QUALITY))
        not_presented_quality = load_data("../../data/weakpass_4.txt",
                                          start=size_millions * MILLION,
                                          max_obj=TEST_SIZE_NOT_PRESENTED_QUALITY)

        quality_metrics = eval_quality(bloom, presented_data_quality, not_presented_quality)
        l_d_bloom.append(
            {"size_millions": size_millions,
             "err_rate": err_rate,
             "time_sec": time,
             "mem_mb": mem,
             "info": bloom.info(),
             "peak_memory_mb": get_peak("reddis"),
             **latency_metrics,
             **quality_metrics
             }
        )
        bloom.save_to_file(f"output/{bloom.name}",
                           redis.Redis(host=HOST, port=PORT, decode_responses=False, socket_timeout=10))
        stop_container('reddis')

    for bucketsize in cuckoo_bucket_sizes:
        start_container("reddis")
        r = redis.Redis(host=HOST, port=PORT, decode_responses=True, socket_timeout=None)
        r.flushall()

        train = load_data("../../data/weakpass_4.txt", start=0, max_obj=size_millions * MILLION)
        cuckoo = CuckooFilter(reddis=r, name=f"cuckoo_{size_millions}M_{bucketsize}", bucketsize=bucketsize)
        sleep(15)

        time = eval_time(cuckoo.add_many, train)
        mem = cuckoo.get_mem_usage()

        presented_data_latency = load_data("../../data/weakpass_4.txt",
                                           start=0,
                                           max_obj=min(size_millions * MILLION, TEST_SIZE_PRESENTED_TIME))
        not_presented_latency = load_data("../../data/weakpass_4.txt",
                                          start=size_millions * MILLION,
                                          max_obj=TEST_SIZE_NOT_PRESENTED_TIME)
        latency_metrics = eval_latency(cuckoo, presented_data_latency, not_presented_latency)
        sleep(15)
        presented_data_quality = load_data("../../data/weakpass_4.txt",
                                           start=0,
                                           max_obj=min(size_millions * MILLION, TEST_SIZE_PRESENTED_QUALITY))
        not_presented_quality = load_data("../../data/weakpass_4.txt",
                                          start=size_millions * MILLION,
                                          max_obj=TEST_SIZE_NOT_PRESENTED_QUALITY)

        quality_metrics = eval_quality(cuckoo, presented_data_quality, not_presented_quality)
        l_d_cuckoo.append(
            {"size_millions": size_millions,
             "bucketsize": bucketsize,
             "time_sec": time,
             "mem_mb": mem,
             "info": cuckoo.info(),
             "peak_memory_mb": get_peak("reddis"),
             **latency_metrics,
             **quality_metrics
             }
        )
        cuckoo.save_to_file(f"output/{cuckoo.name}",
                            redis.Redis(host=HOST, port=PORT, decode_responses=False, socket_timeout=10))
        stop_container('reddis')


class PingFilter(IFilter):

    def exists(self, obj) -> bool:
        return self.reddis.execute_command("ping")


start_container("reddis")
r = redis.Redis(host=HOST, port=PORT, decode_responses=True, socket_timeout=None)
r.flushall()
ping = PingFilter(r, "", "")
presented_data_latency = load_data("../../data/weakpass_4.txt",
                                   start=0,
                                   max_obj=min(100 * MILLION, TEST_SIZE_PRESENTED_TIME))
not_presented_latency = load_data("../../data/weakpass_4.txt",
                                  start=100 * MILLION,
                                  max_obj=TEST_SIZE_NOT_PRESENTED_TIME)
latency_metrics = eval_latency(ping, presented_data_latency, not_presented_latency)
l_d_ping.append(latency_metrics)
pd.DataFrame(l_d_xor).to_csv("xor.csv")
pd.DataFrame(l_d_bloom).to_csv("bloom.csv")
pd.DataFrame(l_d_cuckoo).to_csv("cuckoo.csv")
pd.DataFrame(l_d_ping).to_csv("ping.csv")
