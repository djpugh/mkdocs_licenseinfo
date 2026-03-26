"""Test helper context managers, replacing nskit dependencies."""

from __future__ import annotations

import os
import sys
from contextlib import ContextDecorator
from importlib.metadata import Distribution, MetadataPathFinder
from pathlib import Path
from typing import Any


class Env(ContextDecorator):
    """Context manager for managing environment variables."""

    def __init__(
        self,
        environ: dict[str, str] | None = None,
        override: dict[str, str] | None = None,
        remove: list[str] | None = None,
    ):
        """Initialise the context manager."""
        self._environ = environ
        self._override = override
        self._remove = remove
        self._original: dict[str, str] | None = None

    def __enter__(self):
        """Change to the target environment variables."""
        if self._environ or self._override or self._remove:
            self._original = os.environ.copy()
            if self._environ is not None:
                os.environ.clear()
                os.environ.update(self._environ)
            if self._override:
                os.environ.update(self._override)
            if self._remove:
                for key in self._remove:
                    os.environ.pop(key, None)

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        """Reset to the original environment variables."""
        if self._original is not None:
            os.environ.clear()
            os.environ.update(self._original)


class _TestEntrypoint:
    """A fake entry point for testing."""

    def __init__(self, name: str, group: str, entrypoint: Any):
        self.name = name
        self.group = group
        self.value = f"{entrypoint.__module__}:{entrypoint.__name__}"
        self._entrypoint = entrypoint
        self._sys_meta_path: list[Any] | None = None

    def load(self) -> Any:
        """Return the entrypoint object."""
        return self._entrypoint

    def matches(self, **params: Any) -> bool:
        """Check if this entry point matches the given parameters."""
        for key, value in params.items():
            if getattr(self, key, None) != value:
                return False
        return True

    def start(self) -> None:
        """Register the fake entry point."""
        self._sys_meta_path = sys.meta_path[:]
        nested = [u for u in sys.meta_path if isinstance(u, _TestExtensionFinder)]
        if nested:
            nested[0]._entrypoints.append(self)
        else:
            sys.meta_path.append(_TestExtensionFinder(self))  # type: ignore[arg-type]

    def stop(self) -> None:
        """Unregister the fake entry point."""
        if self._sys_meta_path is not None:
            sys.meta_path = self._sys_meta_path[:]


class _DummyDistribution(Distribution):
    """A fake distribution for testing."""

    def __init__(self, i: int, entrypoint: _TestEntrypoint):
        self._entrypoint = entrypoint
        self._i = i

    @property
    def metadata(self) -> dict[str, str]:
        """Return fake metadata."""
        return {"Name": f"DummyDistribution{self._i}"}

    @property
    def entry_points(self) -> list[_TestEntrypoint]:
        """Return the fake entry points."""
        return [self._entrypoint]

    def read_text(self, filename: str) -> str | None:
        """Not implemented."""
        return None

    def locate_file(self, path: Path) -> None:
        """Not implemented."""
        return None


class _TestExtensionFinder(MetadataPathFinder):
    """A fake metadata finder for testing entry points."""

    def __init__(self, entrypoint: _TestEntrypoint):
        self._entrypoints: list[_TestEntrypoint] = [entrypoint]

    def find_distributions(self, *args: Any, **kwargs: Any) -> list[_DummyDistribution]:
        """Return fake distributions."""
        return [_DummyDistribution(i, ep) for i, ep in enumerate(self._entrypoints)]


class TestExtension(ContextDecorator):
    """Context manager for faking an entry point in tests."""

    def __init__(self, name: str, group: str, entrypoint: Any):
        """Initialise the context manager."""
        self.ep = _TestEntrypoint(name=name, group=group, entrypoint=entrypoint)

    def __enter__(self) -> None:
        """Add the fake entry point."""
        self.ep.start()

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        """Remove the fake entry point."""
        self.ep.stop()
