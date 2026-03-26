import os
import sys
import tempfile
import traceback as tb
import unittest
import webbrowser
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from mkdocs.__main__ import build_command

from mkdocs_licenseinfo import get_licenses as get_licenses_module


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


def mock_get_licenses(func):
    """Mock get_licenses to return fixed test data."""

    @patch("mkdocs_licenseinfo.render_markdown.get_licenses")
    @wraps(func)
    def mocked_call(self, mock_get_licenses):
        mock_get_licenses.return_value = [
            {
                "name": "orjson",
                "version": "3.9.10",
                "homePage": "https://github.com/ijl/orjson",
                "author": "ijl",
                "license": "APACHE SOFTWARE LICENSE;; MIT LICENSE",
                "licenses": ["APACHE SOFTWARE LICENSE", "MIT LICENSE"],
                "neededBy": [],
                "direct": True,
            },
            {
                "name": "aenum",
                "version": "3.1.15",
                "homePage": "https://github.com/ethanfurman/aenum",
                "author": "Ethan Furman",
                "license": "BSD LICENSE",
                "licenses": ["BSD LICENSE"],
                "neededBy": [],
                "direct": True,
            },
        ]
        return func(self, mock_get_licenses)

    return mocked_call


class OfflineTest(unittest.TestCase):
    """Tests using mocked get_licenses (no network)."""

    @property
    def index_md_ok(self):
        return """# Test

## ::licenseinfo

### ::licenseinfo

::licenseinfo
    base_level: 4
"""

    @property
    def index_md_error(self):
        return """# Test

## ::licensesinfo abc/a123

### ::licensesinfo abc/a123

::licensesinfo abc/a123
    base_level: 4
"""

    @property
    def mkdocs_yml(self):
        return """
site_name: mkdocs_licenseinfo_test_repo
repo_url: https://github.com/djpugh/mkdocs_licenseinfo

edit_uri: blob/main/docs/source/

docs_dir: ./source
site_dir: ./html
nav:
 - index.md

theme:
  name: material

plugins:
  - search
  - mkdocs_licenseinfo
"""

    @mock_get_licenses
    def test_mkdocs(self, *args):
        with _tmpdir():
            mkdocs_config = Path("mkdocs.yml")
            mkdocs_config.write_text(self.mkdocs_yml)
            index = Path("source/index.md")
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(self.index_md_ok)
            runner = CliRunner(echo_stdin=True)
            resp = runner.invoke(build_command, catch_exceptions=False)
            self.assertEqual(resp.exit_code, 0, resp.exc_info)
            self.assertTrue(Path("html").exists())
            index_html = Path("html", "index.html")
            contents = index_html.read_text(encoding="utf8")
            self.assertIn(
                '<h3 id="orjson"><a href="https://github.com/ijl/orjson">orjson</a></h3>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />',
                contents,
            )
            self.assertIn(
                '<h4 id="orjson_1"><a href="https://github.com/ijl/orjson">orjson</a></h4>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />',
                contents,
            )
            self.assertIn(
                '<h1 id="orjson_2"><a href="https://github.com/ijl/orjson">orjson</a></h1>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />',
                contents,
            )
            self.assertIn(
                '<h3 id="aenum"><a href="https://github.com/ethanfurman/aenum">aenum</a></h3>\n<p><code>BSD LICENSE</code><br />',
                contents,
            )
            self.assertIn(
                '<h4 id="aenum_1"><a href="https://github.com/ethanfurman/aenum">aenum</a></h4>\n<p><code>BSD LICENSE</code><br />',
                contents,
            )
            self.assertIn(
                '<h1 id="aenum_2"><a href="https://github.com/ethanfurman/aenum">aenum</a></h1>\n<p><code>BSD LICENSE</code><br />',
                contents,
            )

    @mock_get_licenses
    def test_mkdocs_no_block(self, *args):
        with _tmpdir():
            mkdocs_config = Path("mkdocs.yml")
            mkdocs_config.write_text(self.mkdocs_yml)
            index = Path("source/index.md")
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(self.index_md_error)
            runner = CliRunner(echo_stdin=True)
            resp = runner.invoke(build_command, catch_exceptions=False)
            self.assertEqual(resp.exit_code, 0, resp.exc_info)
            self.assertTrue(Path("html").exists())
            index_html = Path("html", "index.html")
            contents = index_html.read_text(encoding="utf8")
            self.assertNotIn('<h3 id="orjson">', contents)
            self.assertNotIn('<h3 id="aenum">', contents)


class OnlineTest(unittest.TestCase):
    """Tests using real dependency resolution (requires network/uv)."""

    @property
    def pyproject_toml(self):
        return """
[project]
name = "test-project"
version = "0.0.1"
requires-python = ">=3.9"
classifiers = [
    "License :: OSI Approved :: MIT License"
]
dependencies = [
    'aenum==3.1.15',
    'orjson==3.9.10'
]
[project.optional-dependencies]
dev = [
    "nox"
]
dev-test= [
    "pytest>=7.3.1",
    "pytest-cov>=4",
    "pytest-subtests",
]
"""

    @property
    def index_md(self):
        return """# Test

## ::licenseinfo

### ::licenseinfo
    using: "PEP631:dev;dev-test"

::licenseinfo
    base_level: 4
"""

    @property
    def mkdocs_yml(self):
        return """
site_name: mkdocs_licenseinfo_test_repo
repo_url: https://github.com/djpugh/mkdocs_licenseinfo

edit_uri: blob/main/docs/source/

docs_dir: ./source
site_dir: ./html
nav:
 - index.md

theme:
  name: material

plugins:
  - search
  - mkdocs_licenseinfo
"""

    def test_mkdocs(self, *args):
        with _tmpdir():
            pyproject = Path("pyproject.toml")
            pyproject.write_text(self.pyproject_toml)
            mkdocs_config = Path("docs/mkdocs.yml")
            mkdocs_config.parent.mkdir(parents=True, exist_ok=True)
            mkdocs_config.write_text(self.mkdocs_yml)
            index = Path("docs/source/index.md")
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(self.index_md)
            runner = CliRunner(echo_stdin=True)
            resp = runner.invoke(build_command, ["-f", str(mkdocs_config)], catch_exceptions=False)
            if sys.version_info >= (3, 10):
                traceback = tb.format_exception(resp.exc_info[1])
            else:
                traceback = tb.format_exception(etype=resp.exc_info[0], value=resp.exc_info[1], tb=resp.exc_info[2])
            self.assertTrue(Path("docs", "html").exists())
            self.assertEqual(resp.exit_code, 0, (resp.exc_info[0], resp.exc_info[1], "\n".join(traceback)))

            index_html = Path("docs", "html", "index.html")
            contents = index_html.read_text(encoding="utf8")
            self.assertIn('<h3 id="orjson">', contents)
            self.assertIn('<h3 id="aenum">', contents)
