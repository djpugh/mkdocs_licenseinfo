from datetime import datetime
from functools import wraps
import json
from pathlib import Path
import sys
import traceback as tb
import unittest
from unittest.mock import MagicMock, patch
import webbrowser

from click.testing import CliRunner
from mkdocs.__main__ import build_command
from nskit.common.contextmanagers import ChDir

from mkdocs_licenseinfo import get_licenses

# Offline test without licensecheck call

# Online test with licensecheck call


def mock_licensecheck(func):

    @patch.object(get_licenses, 'licensecheck', autospec=True)
    @wraps(func)
    def mocked_call(self, licensecheck):
        # Patch licensecheck

        def cli(*args, **kwargs):
            licensecheck.stdout.write(json.dumps(
                {'packages':[
                    {"name": "orjson",
                    "version": "3.9.10",
                    "size": 594514,
                    "homePage": "https://github.com/ijl/orjson",
                    "author": "ijl <ijl@mailbox.org>",
                    "license": "APACHE SOFTWARE LICENSE;; MIT LICENSE",
                    "licenseCompat": True,
                    "errorCode": 0,
                    "namever": "orjson-3.9.10"},
                    {'name': 'aenum',
                    'version': '3.1.15',
                    'size': 728565,
                    'homePage': 'https://github.com/ethanfurman/aenum',
                    'author': 'Ethan Furman',
                    'license': 'BSD LICENSE',
                    'licenseCompat': True,
                    'errorCode': 0,
                    'namever': 'aenum-3.1.15'}
                ]}
            ))
        licensecheck.cli.side_effect = cli
        return func(self, licensecheck)

    return mocked_call



class OfflineTest(unittest.TestCase):

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

    @mock_licensecheck
    def test_mkdocs(self, *args):
        with ChDir():
            mkdocs_config = Path('mkdocs.yml')
            mkdocs_config.write_text(self.mkdocs_yml)
            index = Path('source/index.md')
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(self.index_md_ok)
            runner = CliRunner(echo_stdin=True)
            resp = runner.invoke(build_command, catch_exceptions=False)
            self.assertEqual(resp.exit_code, 0, resp.exc_info)
            self.assertTrue(Path('html').exists())
            index_html = Path('html', 'index.html')
            webbrowser.open(str(index_html.absolute()))
            contents = index_html.read_text(encoding="utf8")
            self.assertIn('<h3 id="orjson"><a href="https://github.com/ijl/orjson">orjson</a></h3>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertIn('<h4 id="orjson_1"><a href="https://github.com/ijl/orjson">orjson</a></h4>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertIn('<h1 id="orjson_2"><a href="https://github.com/ijl/orjson">orjson</a></h1>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertIn('<h3 id="aenum"><a href="https://github.com/ethanfurman/aenum">aenum</a></h3>\n<p><code>BSD LICENSE</code><br />', contents)
            self.assertIn('<h4 id="aenum_1"><a href="https://github.com/ethanfurman/aenum">aenum</a></h4>\n<p><code>BSD LICENSE</code><br />', contents)
            self.assertIn('<h1 id="aenum_2"><a href="https://github.com/ethanfurman/aenum">aenum</a></h1>\n<p><code>BSD LICENSE</code><br />', contents)


    @mock_licensecheck
    def test_mkdocs_no_block(self, *args):
        with ChDir():
            mkdocs_config = Path('mkdocs.yml')
            mkdocs_config.write_text(self.mkdocs_yml)
            index = Path('source/index.md')
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(self.index_md_error)
            runner = CliRunner(echo_stdin=True)
            resp = runner.invoke(build_command, catch_exceptions=False)
            self.assertEqual(resp.exit_code, 0, resp.exc_info)
            self.assertTrue(Path('html').exists())
            index_html = Path('html', 'index.html')
            webbrowser.open(str(index_html.absolute()))
            contents = index_html.read_text(encoding="utf8")
            self.assertNotIn('<h3 id="orjson"><a href="https://github.com/ijl/orjson">orjson</a></h3>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertNotIn('<h4 id="orjson_1"><a href="https://github.com/ijl/orjson">orjson</a></h4>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertNotIn('<h1 id="orjson_2"><a href="https://github.com/ijl/orjson">orjson</a></h1>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertNotIn('<h3 id="aenum"><a href="https://github.com/ethanfurman/aenum">aenum</a></h3>\n<p><code>BSD LICENSE</code><br />', contents)
            self.assertNotIn('<h4 id="aenum_1"><a href="https://github.com/ethanfurman/aenum">aenum</a></h4>\n<p><code>BSD LICENSE</code><br />', contents)
            self.assertNotIn('<h1 id="aenum_2"><a href="https://github.com/ethanfurman/aenum">aenum</a></h1>\n<p><code>BSD LICENSE</code><br />', contents)


class OnlineTest(unittest.TestCase):

    @property
    def pyproject_toml(self):
        return """
[project]
classifiers = [
        "Environment :: Console",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Intended Audience :: Developers",
    	"License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Natural Language :: English"
        # "Development Status :: 6 - Mature"
]
dependencies = [
    'aenum==3.1.15',
    'orjson==3.9.10'
]
[project.optional-dependencies]
dev = [
    "setuptools_scm[toml]",
    'importlib_metadata; python_version < "3.8"',
    "nox"
]
dev-test= [
    "pytest>=7.3.1",
    "pytest-cov>=4",
    "pytest-subtests",
]

[tool.setuptools.packages.find]
where = ["src"]
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
        with ChDir():
            pyproject = Path('pyproject.toml')
            pyproject.write_text(self.pyproject_toml)
            mkdocs_config = Path('docs/mkdocs.yml')
            mkdocs_config.parent.mkdir(parents=True, exist_ok=True)
            mkdocs_config.write_text(self.mkdocs_yml)
            index = Path('docs/source/index.md')
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(self.index_md)
            runner = CliRunner(echo_stdin=True)
            resp = runner.invoke(build_command, ['-f', str(mkdocs_config)], catch_exceptions=False)
            if sys.version_info.major <=3 and sys.version_info.minor < 10:
                traceback =  tb.format_exception(etype=resp.exc_info[0], value=resp.exc_info[1], tb=resp.exc_info[2])
            else:
                traceback =  tb.format_exception(resp.exc_info[1])
            self.assertTrue(Path('docs', 'html').exists())
            self.assertEqual(resp.exit_code, 0, (resp.exc_info[0], resp.exc_info[1], '\n'.join(traceback)))
            self.assertTrue(Path('docs', 'html').exists())

            index_html = Path('docs', 'html', 'index.html')
            webbrowser.open(str(index_html.absolute()))
            contents = index_html.read_text(encoding="utf8")
            self.assertIn('<h3 id="orjson"><a href="https://github.com/ijl/orjson">orjson</a></h3>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertIn('<h4 id="orjson_1"><a href="https://github.com/ijl/orjson">orjson</a></h4>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertIn('<h1 id="orjson_2"><a href="https://github.com/ijl/orjson">orjson</a></h1>\n<p><code>APACHE SOFTWARE LICENSE</code> <code>MIT LICENSE</code><br />', contents)
            self.assertIn('<h3 id="aenum"><a href="https://github.com/ethanfurman/aenum">aenum</a></h3>\n<p><code>BSD LICENSE</code><br />', contents)
            self.assertIn('<h4 id="aenum_1"><a href="https://github.com/ethanfurman/aenum">aenum</a></h4>\n<p><code>BSD LICENSE</code><br />', contents)
            self.assertIn('<h1 id="aenum_2"><a href="https://github.com/ethanfurman/aenum">aenum</a></h1>\n<p><code>BSD LICENSE</code><br />', contents)

    # Include handling for env based token handling (if os.environ.GITHUB_TOKEN)
