import heapq
from itertools import count
from typing import Iterator


class BatchIterator:
    def __init__(self, iter: Iterator[any], batch_size: int):
        self.iter = iter
        self.batch_size = batch_size
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= self.batch_size:
            raise StopIteration

        item = next(self.iter)
        self.index += 1

        return item


class TopKPriorityQueue:
    def __init__(self, k=20):
        self.k = k
        self.heap = []
        self.counter = count()

    def to_dict(self):
        return {
            "k": self.k,
            "heap": self.heap,
            "counter": next(self.counter),
        }

    @classmethod
    def from_dict(cls, data):
        queue = cls(data["k"])
        queue.heap = [tuple(item) for item in data["heap"]]
        queue.counter = count(data["counter"])
        return queue

    def add(self, item, score):
        """
        Add an item with its score to the queue, maintaining only the top k items.
        """

        # Use a tuple (score, counter, item) to avoid comparing items directly
        entry = (score, next(self.counter), item)
        if len(self.heap) < self.k:
            heapq.heappush(self.heap, entry)
        else:
            # Replace the smallest element if the new score is larger
            if score > self.heap[0][0]:
                heapq.heappushpop(self.heap, entry)

    def scores(self):
        return [entry[0] for entry in self.heap]

    def items(self):
        return [entry[2] for entry in self.heap]

    def remove(self, item):
        for i in reversed(range((len(self.heap)))):
            entry = self.heap[i]

            if item != entry[2]:
                continue

            self.heap.remove(entry)
            heapq.heapify(self.heap)
            break

    def reset(self):
        """
        Reset the queue to an empty state and reset the insertion order counter.
        """

        self.heap = []
        self.counter = count()

    def get_top_item(self):
        return self.heap[-1][2], self.heap[-1][0]

    def get_top_items(self):
        """
        Retrieve the top items sorted descending by score, then by insertion order.
        """

        # Extract items sorted by highest score first, using insertion order for ties
        sorted_items = sorted(self.heap, key=lambda x: (-x[0], x[1]))
        return [(item, score) for (score, cnt, item) in sorted_items]

    def get_unsorted_items(self):
        return [(item, score) for (score, cnt, item) in self.heap]

    def __getitem__(self, idx):
        return self.heap[idx]

    def __len__(self):
        return len(self.heap)
