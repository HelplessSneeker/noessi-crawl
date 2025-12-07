"""Efficient top-N apartment tracking using min-heap."""

import heapq
from typing import List, Tuple

from models.apartment import ApartmentListing


class TopNTracker:
    """
    Track top N apartments by investment score using a min-heap.

    Provides O(log N) insertion complexity for efficient real-time tracking
    of the best apartments without needing to sort all apartments.

    The heap stores tuples of (negative_score, apartment) to create a
    max-heap behavior (highest scores maintained).
    """

    def __init__(self, n: int):
        """
        Initialize tracker for top N apartments.

        Args:
            n: Number of top apartments to track
        """
        self.n = n
        self.heap: List[Tuple[float, ApartmentListing]] = []

    def add(self, apartment: ApartmentListing) -> bool:
        """
        Add apartment to top N tracker.

        Args:
            apartment: The apartment to potentially add

        Returns:
            True if apartment made it into top N, False otherwise
        """
        score = apartment.investment_score or 0.0

        if len(self.heap) < self.n:
            # Heap not full - always add
            # Use negative score to create max-heap behavior
            heapq.heappush(self.heap, (-score, apartment))
            return True
        else:
            # Check if better than worst in heap
            worst_score = -self.heap[0][0]  # Negative of negative
            if score > worst_score:
                # Replace worst with new apartment
                heapq.heapreplace(self.heap, (-score, apartment))
                return True
            return False

    def get_sorted_apartments(self) -> List[ApartmentListing]:
        """
        Get top N apartments sorted by score (highest first).

        Returns:
            List of ApartmentListing objects sorted by investment_score descending
        """
        # Sort by negative score (ascending = descending actual scores)
        sorted_heap = sorted(self.heap, key=lambda x: x[0])
        return [apt for _, apt in sorted_heap]

    def is_full(self) -> bool:
        """
        Check if tracker has N apartments.

        Returns:
            True if tracker contains N apartments
        """
        return len(self.heap) >= self.n

    def min_score(self) -> float:
        """
        Get minimum score currently in top N.

        Returns:
            Minimum score in top N, or -inf if not full
        """
        if not self.is_full():
            return float('-inf')
        return -self.heap[0][0]

    def __len__(self) -> int:
        """Return number of apartments currently tracked."""
        return len(self.heap)
