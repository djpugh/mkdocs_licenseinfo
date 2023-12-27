"""Get licenseinfo."""
from __future__ import annotations

from contextlib import ContextDecorator
from io import StringIO
import json
import os
from pathlib import Path
import sys

import licensecheck

from mkdocs_licenseinfo import logger


class UnclosableIO(StringIO):
    """StringIO object that cannot be closed."""

    def close(self):
        """Don't close it."""
        pass

    def force_close(self):
        """Force close it."""
        super().close()

    def __del__(self, *args, **kwargs):
        """Make sure it closes."""
        self.force_close()
        super().__del__(*args, **kwargs)


class LicenseCheckArgs(ContextDecorator):
    """Context manager for setting licensecheck args."""

    def __init__(
        self,
        using='PEP631',
        format='json',
        ignore_packages=None,
        fail_packages=None,
        skip_packages=None,
        ignore_licenses=None,
        fail_licenses=None,
        output=None,
        path=None
    ):
        """Initialise the context manager.

        Keyword Args:
            target_dir (Optional[Path]): the target directory
        """
        self._original_args = None
        if output is None:
            output = UnclosableIO()
        self._output = output
        self._stdout = None
        self._using = using
        self._format = format
        if ignore_packages is None:
            ignore_packages = []
        self._ignore_packages = ignore_packages
        if fail_packages is None:
            fail_packages = []
        self._fail_packages = fail_packages
        if skip_packages is None:
            skip_packages = []
        self._skip_packages = skip_packages
        if ignore_licenses is None:
            ignore_licenses = []
        self._ignore_licenses = ignore_licenses
        if fail_licenses is None:
            fail_licenses = []
        self._fail_licenses = fail_licenses
        self._original_path = None
        if path:
            path = Path(path)
        self._path = path

    def __enter__(self):
        """Change to the set argv."""
        self._original_args = sys.argv[:]
        new_args = [
            'licensecheck',
            '-u',
            self._using,
            '--format',
            self._format]
        for package in self._ignore_packages:
            new_args.append('--ignore-packages')
            new_args.append(package)
        for package in self._fail_packages:
            new_args.append('--fail-packages')
            new_args.append(package)
        for package in self._skip_packages:
            new_args.append('--skip-dependencies')
            new_args.append(package)
        for package in self._ignore_licenses:
            new_args.append('--ignore-licenses')
            new_args.append(package)
        for package in self._fail_licenses:
            new_args.append('--fail-licenses')
            new_args.append(package)
        self._stdout = licensecheck.stdout
        licensecheck.stdout = self._output
        sys.argv = new_args
        if self._path:
            self._original_path = Path.cwd()
            os.chdir(str(self._path))

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: U100
        """Reset to the original argv."""
        sys.argv = self._original_args[:]
        licensecheck.stdout = self._stdout
        if self._path:
            os.chdir(str(self._original_path))
        # Handle SystemExit
        if isinstance(exc_val, SystemExit) and exc_val.code == 0:
            return True


def _split_licenses(package):
    package['licenses'] = [u.strip() for u in package['license'].split(';;')]


def get_licenses(
    using='PEP631',
    ignore_packages=None,
    fail_packages=None,
    skip_packages=None,
    ignore_licenses=None,
    fail_licenses=None,
    path=None
):
    """Get the licenses using licensecheck."""
    output = UnclosableIO()
    if using is None:
        using = 'PEP631'
    with LicenseCheckArgs(
        using=using,
        format='json',
        ignore_packages=ignore_packages,
        fail_packages=fail_packages,
        skip_packages=skip_packages,
        ignore_licenses=ignore_licenses,
        fail_licenses=fail_licenses,
        output=output,
        path=path
    ):
        logger.info(f'Getting licenses for: {using} in path: {path}')
        licensecheck.cli()
    result = json.loads(output.getvalue())
    output.force_close()
    # Loop over the results and clean the licenses
    packages = result['packages']
    for package in packages:
        _split_licenses(package)
    return packages
