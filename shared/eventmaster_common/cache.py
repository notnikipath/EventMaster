from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _CacheItem(Generic[T]):
    value: T
    expires_at: datetime


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._storage: dict[str, _CacheItem[T]] = {}

    def get(self, key: str) -> T | None:
        item = self._storage.get(key)
        if item is None:
            return None
        if item.expires_at < datetime.now(UTC):
            self._storage.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: T) -> None:
        self._storage[key] = _CacheItem(
            value=value,
            expires_at=datetime.now(UTC) + timedelta(seconds=self.ttl_seconds),
        )

    def clear(self) -> None:
        self._storage.clear()
