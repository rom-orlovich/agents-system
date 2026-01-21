"""Generic registry pattern for extensible entities."""

from typing import TypeVar, Generic, Dict, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Registry(Generic[T]):
    """Type-safe registry for Pydantic models."""

    def __init__(self):
        self._items: Dict[str, T] = {}

    def register(self, name: str, item: T) -> None:
        """Register an item."""
        if name in self._items:
            raise ValueError(f"Item '{name}' already registered")
        self._items[name] = item

    def get(self, name: str) -> Optional[T]:
        """Get item by name."""
        return self._items.get(name)

    def list_all(self) -> list[T]:
        """List all registered items."""
        return list(self._items.values())

    def unregister(self, name: str) -> bool:
        """Unregister an item."""
        if name in self._items:
            del self._items[name]
            return True
        return False

    def exists(self, name: str) -> bool:
        """Check if item exists."""
        return name in self._items

    def count(self) -> int:
        """Count registered items."""
        return len(self._items)

    def clear(self) -> None:
        """Clear all registered items."""
        self._items.clear()
