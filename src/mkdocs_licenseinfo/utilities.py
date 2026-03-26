"""Test helper context managers, replacing nskit dependencies."""

from __future__ import annotations

import os
import sys
from contextlib import ContextDecorator
from importlib.metadata import Distribution, EntryPoint, MetadataPathFinder
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

    def __exit__(self, *args, **kwargs):
        """Reset to the original environment variables."""
        if self._original is not None:
            os.environ.clear()
            os.environ.update(self._original)


class _TestEntrypoint(EntryPoint):
    """A fake entry point for testing."""

    def __init__(self, name: str, group: str, entrypoint: type):
        super().__init__(name, f"{entrypoint.__module__}:{entrypoint.__name__}", group)
        self._entrypoint = entrypoint
        self._sys_meta_path: list | None = None

    def __setattr__(self, name: str, value: Any) -> None:
        return object.__setattr__(self, name, value)

    def load(self):
        """Return the entrypoint object."""
        return self._entrypoint

    def start(self):
        """Register the fake entry point."""
        self._sys_meta_path = sys.meta_path[:]
        nested = [u for u in sys.meta_path if isinstance(u, _TestExtensionFinder)]
        if nested:
            nested[0]._entrypoints.append(self)
        else:
            sys.meta_path.append(_TestExtensionFinder(self))

    def stop(self):
        """Unregister the fake entry point."""
        if self._sys_meta_path is not None:
            sys.meta_path = self._sys_meta_path[:]


class _DummyDistribution(Distribution):
    """A fake distribution for testing."""

    def __init__(self, i: int, entrypoint: EntryPoint):
        self._entrypoint = entrypoint
        self._i = i

    @property
    def metadata(self):
        """Return fake metadata."""
        return {"Name": f"DummyDistribution{self._i}"}

    @property
    def entry_points(self):
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

    def __init__(self, entrypoint: EntryPoint):
        self._entrypoints = [entrypoint]

    def find_distributions(self, *args, **kwargs):
        """Return fake distributions."""
        return [_DummyDistribution(i, ep) for i, ep in enumerate(self._entrypoints)]


class TestExtension(ContextDecorator):
    """Context manager for faking an entry point in tests."""

    def __init__(self, name: str, group: str, entrypoint: type):
        """Initialise the context manager."""
        self.ep = _TestEntrypoint(name=name, group=group, entrypoint=entrypoint)

    def __enter__(self):
        """Add the fake entry point."""
        self.ep.start()

    def __exit__(self, *args, **kwargs):
        """Remove the fake entry point."""
        self.ep.stop()
