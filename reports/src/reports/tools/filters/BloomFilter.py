from typing import List

from reports.src.reports.tools.filters.IFilter import IFilter


class BloomFilter(IFilter):
    def __init__(self, reddis, name: str, err_rate):
        super().__init__(reddis, name, "BF")
        self.err_rate = err_rate

    def add_many(self, data: List, lowmem=True):
        self.reddis.execute_command(
            "BF.RESERVE",
            self.name,
            self.err_rate,
            len(data)
        )
        self.reddis.execute_command(
            "BF.MADD",
            self.name,
            *data)
