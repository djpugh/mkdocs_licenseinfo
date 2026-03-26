import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from mkdocs_licenseinfo.get_licenses import get_licenses


@contextmanager
def _tmpdir():
    """Stdlib replacement for broken nskit ChDir."""
    original = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    try:
        yield Path(tmp)
    finally:
        os.chdir(original)


class GetLicensesTestCase(unittest.TestCase):
    """Functional test for get_licenses."""

    def test_get_licenses(self):
        with _tmpdir():
            with open("requirements.txt", "w") as f:
                f.write("aenum\norjson\nnskit")
            licenses = get_licenses(using="requirements:requirements.txt")
            self.assertGreaterEqual(len(licenses), 3)
            package_names = [u["name"] for u in licenses]
            self.assertIn("orjson", package_names)
            self.assertIn("aenum", package_names)
            self.assertIn("nskit", package_names)
