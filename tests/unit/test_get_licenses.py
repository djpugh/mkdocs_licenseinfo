import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from mkdocs_licenseinfo.get_licenses import (
    _get_licence_from_metadata,
    _get_package_info,
    _get_package_info_from_pypi,
    _parse_using,
    _split_licenses,
    get_licenses,
)


class ParseUsingTestCase(unittest.TestCase):
    """Tests for the _parse_using function."""

    def test_pep631_default(self):
        paths, groups, extras = _parse_using("PEP631")
        self.assertEqual(paths, ["pyproject.toml"])
        self.assertEqual(groups, [])

    def test_pep631_with_groups(self):
        paths, groups, extras = _parse_using("PEP631:dev;dev-test")
        self.assertEqual(paths, ["pyproject.toml"])
        self.assertEqual(groups, ["dev", "dev-test"])

    def test_requirements(self):
        paths, groups, extras = _parse_using("requirements:requirements.txt")
        self.assertEqual(paths, ["requirements.txt"])
        self.assertEqual(groups, [])

    def test_requirements_multiple(self):
        paths, groups, extras = _parse_using("requirements:reqs1.txt;reqs2.txt")
        self.assertEqual(paths, ["reqs1.txt", "reqs2.txt"])
        self.assertEqual(groups, [])


class SplitLicensesTestCase(unittest.TestCase):
    """Tests for the _split_licenses function."""

    def test_single_license(self):
        package = {"license": "MIT"}
        _split_licenses(package)
        self.assertEqual(package["licenses"], ["MIT"])

    def test_multiple_licenses(self):
        package = {"license": "APACHE SOFTWARE LICENSE;; MIT LICENSE"}
        _split_licenses(package)
        self.assertEqual(package["licenses"], ["APACHE SOFTWARE LICENSE", "MIT LICENSE"])


class GetLicenceFromMetadataTestCase(unittest.TestCase):
    """Tests for the _get_licence_from_metadata function."""

    def test_license_expression_pep639(self):
        """PEP 639 License-Expression takes priority."""
        meta = MagicMock()
        meta.get.side_effect = lambda k: {
            "License-Expression": "MIT",
            "License": "Some other thing",
        }.get(k)
        meta.get_all.return_value = ["License :: OSI Approved :: BSD License"]
        self.assertEqual(_get_licence_from_metadata(meta), "MIT")

    def test_license_field_fallback(self):
        """Falls back to License field when no License-Expression."""
        meta = MagicMock()
        meta.get.side_effect = lambda k: {
            "License-Expression": None,
            "License": "BSD License",
        }.get(k)
        meta.get_all.return_value = []
        self.assertEqual(_get_licence_from_metadata(meta), "BSD LICENSE")

    def test_license_field_long_ignored(self):
        """Long License fields (full licence text) are ignored."""
        meta = MagicMock()
        long_text = "A" * 250
        meta.get.side_effect = lambda k: {
            "License-Expression": None,
            "License": long_text,
        }.get(k)
        meta.get_all.return_value = ["License :: OSI Approved :: MIT License"]
        self.assertEqual(_get_licence_from_metadata(meta), "MIT LICENSE")

    def test_classifiers_fallback(self):
        """Falls back to classifiers when no License-Expression or License."""
        meta = MagicMock()
        meta.get.side_effect = lambda k: None
        meta.get_all.return_value = [
            "License :: OSI Approved :: MIT License",
            "License :: OSI Approved :: Apache Software License",
        ]
        self.assertEqual(
            _get_licence_from_metadata(meta),
            "MIT LICENSE;; APACHE SOFTWARE LICENSE",
        )

    def test_unknown_when_nothing(self):
        """Returns UNKNOWN when no licence info available."""
        meta = MagicMock()
        meta.get.side_effect = lambda k: None
        meta.get_all.return_value = []
        self.assertEqual(_get_licence_from_metadata(meta), "UNKNOWN")

    def test_empty_license_expression(self):
        """Empty/whitespace License-Expression is skipped."""
        meta = MagicMock()
        meta.get.side_effect = lambda k: {
            "License-Expression": "   ",
            "License": "MIT",
        }.get(k)
        meta.get_all.return_value = []
        self.assertEqual(_get_licence_from_metadata(meta), "MIT")

    def test_non_license_classifiers_ignored(self):
        """Non-licence classifiers are filtered out."""
        meta = MagicMock()
        meta.get.side_effect = lambda k: None
        meta.get_all.return_value = [
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Topic :: Software Development",
        ]
        self.assertEqual(_get_licence_from_metadata(meta), "MIT LICENSE")


class GetPackageInfoInstalledTestCase(unittest.TestCase):
    """Tests for _get_package_info with installed packages."""

    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_installed_with_homepage(self, mock_meta):
        """Installed package with Home-page field."""
        meta = MagicMock()
        meta.__getitem__ = lambda s, k: {"Name": "requests", "Version": "2.31.0"}[k]
        meta.get.side_effect = lambda k: {
            "Home-page": "https://requests.readthedocs.io",
            "Author": "Kenneth Reitz",
            "Author-email": None,
            "License-Expression": None,
            "License": "Apache 2.0",
        }.get(k)
        meta.get_all.side_effect = lambda k: {
            "Project-URL": [],
            "Classifier": [],
        }.get(k, [])
        mock_meta.return_value = meta

        result = _get_package_info("requests", "2.31.0")
        self.assertEqual(result["name"], "requests")
        self.assertEqual(result["version"], "2.31.0")
        self.assertEqual(result["homePage"], "https://requests.readthedocs.io")
        self.assertEqual(result["author"], "Kenneth Reitz")
        self.assertEqual(result["license"], "APACHE 2.0")

    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_installed_with_project_url(self, mock_meta):
        """Installed package using Project-URL when Home-page is empty."""
        meta = MagicMock()
        meta.__getitem__ = lambda s, k: {"Name": "pip", "Version": "25.0"}[k]
        meta.get.side_effect = lambda k: {
            "Home-page": None,
            "Author": None,
            "Author-email": "The pip developers <dev@pip.org>",
            "License-Expression": "MIT",
            "License": None,
        }.get(k)
        meta.get_all.side_effect = lambda k: {
            "Project-URL": [
                "Documentation, https://pip.pypa.io",
                "Homepage, https://pip.pypa.io",
                "Source, https://github.com/pypa/pip",
            ],
            "Classifier": [],
        }.get(k, [])
        mock_meta.return_value = meta

        result = _get_package_info("pip", "25.0")
        self.assertEqual(result["homePage"], "https://pip.pypa.io")
        self.assertEqual(result["author"], "The pip developers")
        self.assertEqual(result["license"], "MIT")

    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_installed_project_url_repository_fallback(self, mock_meta):
        """Falls back to Repository Project-URL."""
        meta = MagicMock()
        meta.__getitem__ = lambda s, k: {"Name": "foo", "Version": "1.0"}[k]
        meta.get.side_effect = lambda k: {
            "Home-page": None,
            "Author": "Foo Author",
            "Author-email": None,
            "License-Expression": None,
            "License": "MIT",
        }.get(k)
        meta.get_all.side_effect = lambda k: {
            "Project-URL": [
                "Repository, https://github.com/foo/foo",
            ],
            "Classifier": [],
        }.get(k, [])
        mock_meta.return_value = meta

        result = _get_package_info("foo", "1.0")
        self.assertEqual(result["homePage"], "https://github.com/foo/foo")

    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_installed_first_project_url_fallback(self, mock_meta):
        """Falls back to first Project-URL when no recognised label."""
        meta = MagicMock()
        meta.__getitem__ = lambda s, k: {"Name": "bar", "Version": "2.0"}[k]
        meta.get.side_effect = lambda k: {
            "Home-page": None,
            "Author": None,
            "Author-email": None,
            "License-Expression": None,
            "License": "MIT",
        }.get(k)
        meta.get_all.side_effect = lambda k: {
            "Project-URL": [
                "Changelog, https://example.com/changelog",
            ],
            "Classifier": [],
        }.get(k, [])
        mock_meta.return_value = meta

        result = _get_package_info("bar", "2.0")
        self.assertEqual(result["homePage"], "https://example.com/changelog")

    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_installed_no_urls(self, mock_meta):
        """Package with no URL info at all."""
        meta = MagicMock()
        meta.__getitem__ = lambda s, k: {"Name": "bare", "Version": "0.1"}[k]
        meta.get.side_effect = lambda k: {
            "Home-page": None,
            "Author": None,
            "Author-email": None,
            "License-Expression": None,
            "License": None,
        }.get(k)
        meta.get_all.side_effect = lambda k: {
            "Project-URL": [],
            "Classifier": [],
        }.get(k, [])
        mock_meta.return_value = meta

        result = _get_package_info("bare", "0.1")
        self.assertEqual(result["homePage"], "")
        self.assertEqual(result["author"], "")
        self.assertEqual(result["license"], "UNKNOWN")


class GetPackageInfoUninstalledTestCase(unittest.TestCase):
    """Tests for _get_package_info falling back to PyPI."""

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_uninstalled_pypi_success(self, mock_meta, mock_urlopen):
        """Uninstalled package fetched from PyPI."""
        import json
        from importlib.metadata import PackageNotFoundError

        mock_meta.side_effect = PackageNotFoundError("notinstalled")

        pypi_response = json.dumps(
            {
                "info": {
                    "author": "Some Author",
                    "author_email": "author@example.com",
                    "home_page": "https://example.com/notinstalled",
                    "project_url": None,
                    "license": "BSD-3-Clause",
                    "classifiers": [],
                }
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = pypi_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _get_package_info("notinstalled", "1.0.0")
        self.assertEqual(result["name"], "notinstalled")
        self.assertEqual(result["version"], "1.0.0")
        self.assertEqual(result["author"], "Some Author")
        self.assertEqual(result["homePage"], "https://example.com/notinstalled")
        self.assertEqual(result["license"], "BSD-3-CLAUSE")

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_uninstalled_pypi_author_email_fallback(self, mock_meta, mock_urlopen):
        """PyPI fallback uses author_email when author is empty."""
        import json
        from importlib.metadata import PackageNotFoundError

        mock_meta.side_effect = PackageNotFoundError("pkg")

        pypi_response = json.dumps(
            {
                "info": {
                    "author": "",
                    "author_email": "dev@example.com",
                    "home_page": "",
                    "project_url": "https://example.com",
                    "license": "MIT",
                    "classifiers": [],
                }
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = pypi_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _get_package_info("pkg", "2.0")
        self.assertEqual(result["author"], "dev@example.com")
        self.assertEqual(result["homePage"], "https://example.com")

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_uninstalled_pypi_classifiers_fallback(self, mock_meta, mock_urlopen):
        """PyPI fallback uses classifiers when licence field is empty."""
        import json
        from importlib.metadata import PackageNotFoundError

        mock_meta.side_effect = PackageNotFoundError("pkg")

        pypi_response = json.dumps(
            {
                "info": {
                    "author": "Author",
                    "author_email": None,
                    "home_page": None,
                    "project_url": None,
                    "license": "",
                    "classifiers": [
                        "Programming Language :: Python :: 3",
                        "License :: OSI Approved :: MIT License",
                        "License :: OSI Approved :: BSD License",
                    ],
                }
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = pypi_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _get_package_info("pkg", "1.0")
        self.assertEqual(result["license"], "MIT LICENSE;; BSD LICENSE")

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_uninstalled_pypi_long_license_ignored(self, mock_meta, mock_urlopen):
        """PyPI fallback ignores long licence text (full licence body)."""
        import json
        from importlib.metadata import PackageNotFoundError

        mock_meta.side_effect = PackageNotFoundError("pkg")

        pypi_response = json.dumps(
            {
                "info": {
                    "author": "Author",
                    "author_email": None,
                    "home_page": None,
                    "project_url": None,
                    "license": "A" * 250,
                    "classifiers": ["License :: OSI Approved :: MIT License"],
                }
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = pypi_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _get_package_info("pkg", "1.0")
        self.assertEqual(result["license"], "MIT LICENSE")


class GetPackageInfoNonExistentTestCase(unittest.TestCase):
    """Tests for _get_package_info when package doesn't exist anywhere."""

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_nonexistent_pypi_error(self, mock_meta, mock_urlopen):
        """Package not installed and PyPI request fails."""
        from importlib.metadata import PackageNotFoundError
        from urllib.error import HTTPError

        mock_meta.side_effect = PackageNotFoundError("ghost")
        mock_urlopen.side_effect = HTTPError("https://pypi.org/pypi/ghost/1.0/json", 404, "Not Found", {}, None)

        result = _get_package_info("ghost", "1.0")
        self.assertEqual(result["name"], "ghost")
        self.assertEqual(result["version"], "1.0")
        self.assertEqual(result["license"], "UNKNOWN")
        self.assertEqual(result["author"], "")
        self.assertEqual(result["homePage"], "")

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_nonexistent_pypi_timeout(self, mock_meta, mock_urlopen):
        """Package not installed and PyPI request times out."""
        from importlib.metadata import PackageNotFoundError

        mock_meta.side_effect = PackageNotFoundError("ghost")
        mock_urlopen.side_effect = TimeoutError("Connection timed out")

        result = _get_package_info("ghost", "1.0")
        self.assertEqual(result["name"], "ghost")
        self.assertEqual(result["version"], "1.0")
        self.assertEqual(result["license"], "UNKNOWN")

    @patch("mkdocs_licenseinfo.get_licenses.urlopen")
    @patch("mkdocs_licenseinfo.get_licenses.get_metadata")
    def test_nonexistent_pypi_connection_error(self, mock_meta, mock_urlopen):
        """Package not installed and no network."""
        from importlib.metadata import PackageNotFoundError

        mock_meta.side_effect = PackageNotFoundError("ghost")
        mock_urlopen.side_effect = OSError("Network unreachable")

        result = _get_package_info("ghost", "1.0")
        self.assertEqual(result["name"], "ghost")
        self.assertEqual(result["license"], "UNKNOWN")


class GetLicensesTestCase(unittest.TestCase):
    """Tests for the get_licenses function."""

    @patch("mkdocs_licenseinfo.get_licenses._get_package_info")
    @patch("mkdocs_licenseinfo.get_licenses._resolve_deps")
    @patch("mkdocs_licenseinfo.get_licenses._read_deps_from_pyproject")
    @patch("mkdocs_licenseinfo.get_licenses.Path")
    def test_get_licenses(self, mock_path_cls, mock_read, mock_resolve, mock_info):
        """Basic get_licenses returns sorted packages with split licences."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.name = "pyproject.toml"
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.cwd.return_value = "/original"

        mock_read.return_value = ["orjson==3.9.10", "aenum==3.1.15"]
        mock_resolve.return_value = [("aenum", "3.1.15", []), ("orjson", "3.9.10", [])]
        mock_info.side_effect = lambda name, version: {
            "orjson": {
                "name": "orjson",
                "version": "3.9.10",
                "homePage": "https://github.com/ijl/orjson",
                "author": "ijl <ijl@mailbox.org>",
                "license": "APACHE SOFTWARE LICENSE;; MIT LICENSE",
            },
            "aenum": {
                "name": "aenum",
                "version": "3.1.15",
                "homePage": "https://github.com/ethanfurman/aenum",
                "author": "Ethan Furman",
                "license": "BSD LICENSE",
            },
        }[name]

        packages = get_licenses()
        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0]["name"], "aenum")
        self.assertEqual(packages[0]["licenses"], ["BSD LICENSE"])
        self.assertEqual(packages[1]["name"], "orjson")
        self.assertEqual(packages[1]["licenses"], ["APACHE SOFTWARE LICENSE", "MIT LICENSE"])

    @patch("mkdocs_licenseinfo.get_licenses._get_package_info")
    @patch("mkdocs_licenseinfo.get_licenses._resolve_deps")
    @patch("mkdocs_licenseinfo.get_licenses._read_deps_from_pyproject")
    @patch("mkdocs_licenseinfo.get_licenses.Path")
    def test_ignore_and_skip_packages(self, mock_path_cls, mock_read, mock_resolve, mock_info):
        """Ignored and skipped packages are excluded from results."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.name = "pyproject.toml"
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.cwd.return_value = "/original"

        mock_read.return_value = ["a", "b", "c"]
        mock_resolve.return_value = [("a", "1.0", []), ("b", "2.0", []), ("c", "3.0", [])]
        mock_info.side_effect = lambda name, version: {
            "name": name,
            "version": version,
            "homePage": "",
            "author": "",
            "license": "MIT",
        }

        packages = get_licenses(ignore_packages=["a"], skip_packages=["c"])
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["name"], "b")

    @patch("mkdocs_licenseinfo.get_licenses._resolve_deps")
    @patch("mkdocs_licenseinfo.get_licenses._read_deps_from_pyproject")
    @patch("mkdocs_licenseinfo.get_licenses.Path")
    def test_empty_deps(self, mock_path_cls, mock_read, mock_resolve):
        """Returns empty list when no dependencies found."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.name = "pyproject.toml"
        mock_path_cls.return_value = mock_path_instance

        mock_read.return_value = []

        packages = get_licenses()
        self.assertEqual(packages, [])
        mock_resolve.assert_not_called()

    @patch("mkdocs_licenseinfo.get_licenses.Path")
    def test_missing_requirements_file(self, mock_path_cls):
        """Returns empty list when requirements file doesn't exist."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        packages = get_licenses()
        self.assertEqual(packages, [])
