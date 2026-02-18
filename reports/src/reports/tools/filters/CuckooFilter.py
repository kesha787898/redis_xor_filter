from typing import List

from reports.src.reports.tools.filters.IFilter import IFilter


class CuckooFilter(IFilter):
    def __init__(self, reddis, name: str, bucketsize):
        super().__init__(reddis, name, "CF")
        self.bucketsize = bucketsize

    def add_many(self, data: List, lowmem=True):
        self.reddis.execute_command(
            "CF.RESERVE",
            self.name,
            len(data),
            "BUCKETSIZE",
            self.bucketsize,
        )
        self.reddis.execute_command(
            "CF.INSERT",
            self.name,
            "ITEMS",
            *data)
