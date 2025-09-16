import heapq

class PriorityTaskQueue:
    def __init__(self):
        self._queue = []
        self._index = 0

    def put(self, task, priority=0):
        heapq.heappush(self._queue, (-priority, self._index, task))
        self._index += 1

    def get(self):
        if self._queue:
            return heapq.heappop(self._queue)[-1]
        return None

    def empty(self):
        return not self._queue

    def __len__(self):
        return len(self._queue) 