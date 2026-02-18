from random import Random
from typing import List, Tuple
from tqdm import tqdm


def load_data(path: str, start: int, max_obj: int) -> List[str]:
    data = []
    with open(path, "rb") as f:
        for idx, line in enumerate(tqdm(f, desc="loading", total=max_obj)):
            if idx < start:
                continue
            if idx >= start + max_obj:
                break
            data.append(line.rstrip(b"\r\n"))
    return data
