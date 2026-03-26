import json
import sys
import unittest
from functools import wraps
from unittest.mock import DEFAULT, MagicMock, call, patch

from jinja2 import Environment
from nskit.common.contextmanagers import Env, TestExtension

from mkdocs_licenseinfo.render_markdown import (
    _EnvironmentFactory,
    get_licenses_as_markdown,
)


class EnvironmentFactoryTestCase(unittest.TestCase):
    def test_init(self):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)

    def test_add_extensions(self):
        # Use a magic mock to check add_extension called as expected

        with Env(override={"MKDOCS_LICENSEINFO_JINJA_EXTENSIONS": json.dumps(["a", "b", "c"])}):
            # We create a factory and check it here
            factory = _EnvironmentFactory()
            environment = MagicMock()
            factory.add_extensions(environment)
            environment.add_extension.assert_has_calls([call("a"), call("b"), call("c")], any_order=True)
            self.assertEqual(environment.add_extension.call_count, 3)

    def test_add_extensions_default(self):
        # Use a magic mock to check add_extension not called
        factory = _EnvironmentFactory()
        environment = MagicMock()
        factory.add_extensions(environment)
        environment.add_extension.assert_not_called()

    def test_get_environment(self):
        # Create Extensions for this
        environment1 = MagicMock()

        def test_extension1():
            return environment1

        environment2 = MagicMock()

        def test_extension_2():
            return environment2

        with TestExtension("test1", "mkdocs_licenseinfo.jinja_environment_factory", test_extension1):
            with TestExtension("test2", "mkdocs_licenseinfo.jinja_environment_factory", test_extension_2):
                factory = _EnvironmentFactory()
                with Env(override={"MKDOCS_LICENSEINFO_JINJA_ENVIRONMENT_FACTORY": "test1"}):
                    self.assertEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)

    def test_get_environment_default(self):
        # Create Extensions for this
        environment1 = MagicMock()

        def test_extension1():
            return environment1

        environment2 = MagicMock()

        def test_extension_2():
            return environment2

        with TestExtension("test1", "mkdocs_licenseinfo.jinja_environment_factory", test_extension1):
            with TestExtension("test2", "mkdocs_licenseinfo.jinja_environment_factory", test_extension_2):
                factory = _EnvironmentFactory()
                with Env(override={"MKDOCS_GITHUB_CHANGELOG_JINJA_ENVIRONMENT_FACTORY": "default"}):
                    self.assertNotEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)
                    self.assertIsInstance(factory.get_environment(), Environment)

    def test_get_environment_none(self):
        # Create Extensions for this
        environment1 = MagicMock()

        def test_extension1():
            return environment1

        environment2 = MagicMock()

        def test_extension_2():
            return environment2

        with TestExtension("test1", "mkdocs_github_changelog.jinja_environment_factory", test_extension1):
            with TestExtension("test2", "mkdocs_github_changelog.jinja_environment_factory", test_extension_2):
                factory = _EnvironmentFactory()
                with Env(remove=["MKDOCS_LICENSEINFO_JINJA_ENVIRONMENT_FACTORY"]):
                    self.assertNotEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)
                    self.assertIsInstance(factory.get_environment(), Environment)

    def test_environment_exists(self):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)
        factory._environment = "a"
        self.assertEqual(factory.environment, "a")

    @patch.multiple(_EnvironmentFactory, get_environment=DEFAULT, add_extensions=DEFAULT)
    def test_environment_not_exists(self, get_environment, add_extensions):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)
        get_environment.return_value = "a"
        self.assertEqual(factory.environment, "a")
        self.assertEqual(factory._environment, "a")
        get_environment.assert_called_once_with()
        add_extensions.assert_called_once_with("a")

    def test_default_environment(self):
        # Check loader is correct
        environment = _EnvironmentFactory.default_environment()
        self.assertIsInstance(environment, Environment)


def patch_get_licenses(func):
    @wraps(func)
    @patch("mkdocs_licenseinfo.render_markdown.get_licenses")
    def wrapped(self, mock_get_licenses, *args):
        def side_effect(
            using="PEP631",
            ignore_packages=None,
            fail_packages=None,
            skip_packages=None,
            ignore_licenses=None,
            fail_licenses=None,
            path=None,
        ):
            if using == "diff":
                return [
                    {
                        "name": "orjson",
                        "version": "3.9.10",
                        "homePage": "https://github.com/ijl/orjson",
                        "author": "ijl",
                        "license": "APACHE SOFTWARE LICENSE;; MIT LICENSE",
                        "licenses": ["APACHE SOFTWARE LICENSE", "MIT LICENSE"],
                        "neededBy": [],
                        "direct": True,
                    }
                ]
            return [
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

        mock_get_licenses.side_effect = side_effect
        return func(self, mock_get_licenses, *args)

    return wrapped


class GetLicensesAsMarkdownTestCase(unittest.TestCase):
    @patch_get_licenses
    def test_simple(self, lc):
        result = get_licenses_as_markdown()
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0],
            "# [orjson](https://github.com/ijl/orjson)\n``APACHE SOFTWARE LICENSE`` ``MIT LICENSE``  \n*Version Checked: 3.9.10*  \nAuthor: ijl",
        )
        self.assertEqual(
            result[1],
            "# [aenum](https://github.com/ethanfurman/aenum)\n``BSD LICENSE``  \n*Version Checked: 3.1.15*  \nAuthor: Ethan Furman",
        )

    @patch_get_licenses
    def test_custom_template(self, lc):
        result = get_licenses_as_markdown(package_template="!! {{package.name}}")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "!! orjson")
        self.assertEqual(result[1], "!! aenum")

    @patch_get_licenses
    def test_with_diff(self, lc):
        result = get_licenses_as_markdown(diff="diff")
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0],
            "# [aenum](https://github.com/ethanfurman/aenum)\n``BSD LICENSE``  \n*Version Checked: 3.1.15*  \nAuthor: Ethan Furman",
        )
