from functools import wraps
import json
import sys
import unittest
from unittest.mock import call, DEFAULT, MagicMock, patch

from jinja2 import Environment
from nskit.common.contextmanagers import Env, TestExtension

from mkdocs_licenseinfo import get_licenses
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

        with Env(override={'MKDOCS_LICENSEINFO_JINJA_EXTENSIONS': json.dumps(["a", "b", "c"]) }):
            # We create a factory and check it here
            factory = _EnvironmentFactory()
            environment = MagicMock()
            factory.add_extensions(environment)
            environment.add_extension.assert_has_calls([call('a'), call('b'), call('c')], any_order=True)
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

        with TestExtension('test1', 'mkdocs_licenseinfo.jinja_environment_factory', test_extension1):
            with TestExtension('test2', 'mkdocs_licenseinfo.jinja_environment_factory', test_extension_2):
                factory = _EnvironmentFactory()
                with Env(override={'MKDOCS_LICENSEINFO_JINJA_ENVIRONMENT_FACTORY': 'test1'}):
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

        with TestExtension('test1', 'mkdocs_licenseinfo.jinja_environment_factory', test_extension1):
            with TestExtension('test2', 'mkdocs_licenseinfo.jinja_environment_factory', test_extension_2):
                factory = _EnvironmentFactory()
                with Env(override={'MKDOCS_GITHUB_CHANGELOG_JINJA_ENVIRONMENT_FACTORY': 'default'}):
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

        with TestExtension('test1', 'mkdocs_github_changelog.jinja_environment_factory', test_extension1):
            with TestExtension('test2', 'mkdocs_github_changelog.jinja_environment_factory', test_extension_2):
                factory = _EnvironmentFactory()
                with Env(remove=['MKDOCS_LICENSEINFO_JINJA_ENVIRONMENT_FACTORY']):
                    self.assertNotEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)
                    self.assertIsInstance(factory.get_environment(), Environment)

    def test_environment_exists(self):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)
        factory._environment = 'a'
        self.assertEqual(factory.environment, 'a')

    @patch.multiple(_EnvironmentFactory, get_environment=DEFAULT, add_extensions=DEFAULT)
    def test_environment_not_exists(self, get_environment, add_extensions):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)
        get_environment.return_value =  'a'
        self.assertEqual(factory.environment, 'a')
        self.assertEqual(factory._environment, 'a')
        get_environment.assert_called_once_with()
        add_extensions.assert_called_once_with('a')

    def test_default_environment(self):
        # Check loader is correct
        environment = _EnvironmentFactory.default_environment()
        self.assertIsInstance(environment, Environment)


def patch_licensecheck(func):

    @wraps(func)
    @patch.object(get_licenses, 'licensecheck', autospec=True)
    def wrapped(self, lc, *args):
        # Patch licensecheck
        def cli(*args, **kwargs):
            if 'diff' in sys.argv:
                lc.stdout.write(json.dumps({
                    "packages": [
                        {"name": "orjson",
                        "version": "3.9.10",
                        "size": 594514,
                        "homePage": "https://github.com/ijl/orjson",
                        "author": "ijl <ijl@mailbox.org>",
                        "license": "APACHE SOFTWARE LICENSE;; MIT LICENSE",
                        "licenseCompat": True,
                        "errorCode": 0,
                        "namever": "orjson-3.9.10"}]}))
            else:
                lc.stdout.write(json.dumps({
                    "packages": [
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
                        'namever': 'aenum-3.1.15'}]}))
        lc.cli.side_effect = cli
        return func(self, lc, *args)

    return wrapped


class GetLicensesAsMarkdownTestCase(unittest.TestCase):

    @patch_licensecheck
    def test_simple(self, lc):
        result = get_licenses_as_markdown()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], '# [orjson](https://github.com/ijl/orjson)\n``APACHE SOFTWARE LICENSE`` ``MIT LICENSE``  \n*Version Checked: 3.9.10*  \nAuthor: ijl <ijl@mailbox.org>')
        self.assertEqual(result[1], '# [aenum](https://github.com/ethanfurman/aenum)\n``BSD LICENSE``  \n*Version Checked: 3.1.15*  \nAuthor: Ethan Furman')

    @patch_licensecheck
    def test_custom_template(self, lc):
        result = get_licenses_as_markdown(package_template='!! {{package.name}}')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], '!! orjson')
        self.assertEqual(result[1], '!! aenum')

    @patch_licensecheck
    def test_with_diff(self, lc):
        result = get_licenses_as_markdown(diff='diff')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '# [aenum](https://github.com/ethanfurman/aenum)\n``BSD LICENSE``  \n*Version Checked: 3.1.15*  \nAuthor: Ethan Furman')
