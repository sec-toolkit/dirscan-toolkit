import difflib
from difflib import SequenceMatcher

import xxhash


def content_hash(body):
    return xxhash.xxh64(body).hexdigest()


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


class Dedup:
    def __init__(self, sim_threshold=0.9):
        self._seen_hash = set()
        self._seen_sample = []
        self.sim_threshole = sim_threshold

    def is_duplicate(self, body):
        h = content_hash(body)
        if h in self._seen_hash:
            return True
        self._seen_hash.add(h)

        text = body.decode(errors="ignore")
        for sample in self._seen_sample:
            if similarity(text, sample) > self.sim_threshole:
                return True
        self._seen_sample.append(text)
        return False
