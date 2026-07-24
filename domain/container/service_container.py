# domain/container/service_container.py - Service Container Interface
"""Domain-layer interface for the service container.

Only contains the abstract interface (IServiceContainer), type aliases, and protocols.
The concrete implementation (ServiceContainer) lives in application/container/service_container.py,
since it depends on infrastructure and application layers.
"""

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar

T = TypeVar("T")


# Service factory protocol for better type safety
class ServiceFactory(Protocol):
    """Protocol for service factories."""

    def __call__(self) -> object:
        """Create and return a service instance."""
        ...


# Service key type - either a type or string identifier
ServiceKey = type[object] | str


class IServiceContainer(ABC):
    """Simple service container interface."""

    @abstractmethod
    def get(self, interface: type[T] | str) -> T:
        """Get a service instance."""

    @abstractmethod
    def has(self, interface: type[T] | str) -> bool:
        """Check if service is registered."""
