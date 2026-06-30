"""
priority_queue.py — Generic min-heap priority queue for AI algorithms.

Wraps ``heapq`` with a stable tie-breaking counter so equal-priority
items maintain FIFO order — required for deterministic BFS/UCS/A* results.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Generic, Iterator, List, Optional, Tuple, TypeVar

T = TypeVar("T")


class PriorityQueue(Generic[T]):
    """Min-priority queue with stable FIFO tie-breaking.

    Args:
        items: Optional iterable of ``(priority, item)`` pairs to pre-load.

    Example::

        pq: PriorityQueue[str] = PriorityQueue()
        pq.push(1.0, "low cost node")
        pq.push(0.5, "high priority node")
        item = pq.pop()   # "high priority node"
    """

    def __init__(self, items: Optional[List[Tuple[float, T]]] = None) -> None:
        self._counter: Iterator[int] = itertools.count()
        self._heap: List[Tuple[float, int, T]] = []

        if items:
            for priority, item in items:
                self.push(priority, item)

    # ------------------------------------------------------------------
    def push(self, priority: float, item: T) -> None:
        """Insert *item* with the given *priority* (lower = higher priority)."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self) -> T:
        """Remove and return the item with the lowest priority value.

        Raises:
            IndexError: If the queue is empty.
        """
        _, _, item = heapq.heappop(self._heap)
        return item

    def peek(self) -> T:
        """Return the item with the lowest priority without removing it.

        Raises:
            IndexError: If the queue is empty.
        """
        _, _, item = self._heap[0]
        return item

    def peek_priority(self) -> float:
        """Return the priority of the top item without removing it."""
        return self._heap[0][0]

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)

    def __contains__(self, item: object) -> bool:
        return any(i == item for _, _, i in self._heap)

    def is_empty(self) -> bool:
        """Return ``True`` if the queue has no elements."""
        return not self._heap

    def clear(self) -> None:
        """Remove all elements."""
        self._heap.clear()
        self._counter = itertools.count()
