import asyncio
from itertools import cycle


class UpstreamPool:
    def __init__(self, upstreams, max_connections):
        self._cycle = cycle(upstreams)
        self._sem = asyncio.Semaphore(max_connections)

    def next_upstream(self):
        return next(self._cycle)

    def limit(self):
        return self._sem