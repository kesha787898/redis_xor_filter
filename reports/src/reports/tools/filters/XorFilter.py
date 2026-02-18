from typing import List

from reports.src.reports.tools.filters.IFilter import IFilter


class XorFilter(IFilter):
    def __init__(self, reddis, name: str, fp_size):
        super().__init__(reddis, name, "XOR")
        self.fp_size = fp_size
        self.additional_memory = 0

    def add_many(self, data: List, lowmem=True):
        set_name = self.name + "_set"
        self.reddis.sadd(
            set_name,
            *data
        )
        if lowmem:
            del data
        self.reddis.execute_command("XOR.BUILD", self.name, set_name, self.fp_size)
        self.additional_memory=self.reddis.memory_usage(set_name)
        self.reddis.delete(set_name)

    def info(self):
        return self.reddis.execute_command("XOR.INFO", self.name)

    def get_additional_memory(self):
        return self.additional_memory/ 2 ** 20
