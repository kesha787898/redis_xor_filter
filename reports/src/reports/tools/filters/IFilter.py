from typing import List

from tqdm import tqdm


class IFilter:
    def __init__(self, reddis, name: str, alias):
        self.reddis = reddis
        self.name = name
        self.alias = alias

    def add_many(self, data: List, low_mem=True):
        raise NotImplemented()

    def exists(self, obj) -> bool:
        return self.reddis.execute_command(
            f"{self.alias}.EXISTS",
            self.name,
            obj
        ) == 1

    # def __del__(self):
    #    self.reddis.delete(self.name)

    def save_to_file(self, filename: str, reddis_binary):
        cursor = 0

        with open(filename, "wb") as f:
            while True:
                cursor, chunk = reddis_binary.execute_command(
                    f"{self.alias}.SCANDUMP",
                    self.name,
                    cursor,
                )
                if chunk is None:
                    chunk = b""

                f.write(cursor.to_bytes(8, "big"))
                f.write(len(chunk).to_bytes(8, "big"))
                f.write(chunk)
                if cursor == 0:
                    break

    def load(self, filename: str, reddis_binary):
        with open(filename, "rb") as f:
            while True:
                cursor_data = f.read(8)

                if not cursor_data:
                    break
                cursor = int.from_bytes(cursor_data, "big")
                size = int.from_bytes(f.read(8), "big")
                chunk = f.read(size)
                reddis_binary.execute_command(
                    f"{self.alias}.LOADCHUNK",
                    self.name,
                    cursor,
                    chunk,
                )

                if cursor == 0:
                    break

    def info(self):
        return self.reddis.execute_command(f"{self.alias}.INFO", self.name)

    def check_batch(self, data, batch_size=10_000):
        total = 0

        for i in tqdm(range(0, len(data), batch_size), desc="eval_quality"):
            batch = data[i:i + batch_size]

            pipe = self.reddis.pipeline(transaction=False)

            for key in batch:
                pipe.execute_command(f"{self.alias}.EXISTS", self.name, key)

            total += sum(pipe.execute())

        return total

    def get_mem_usage(self):
        return self.reddis.memory_usage(self.name) / 2 ** 20  # MB
