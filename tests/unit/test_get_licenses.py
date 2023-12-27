from datetime import datetime
from functools import wraps
import sys
import unittest
from unittest.mock import call, DEFAULT, patch

import licensecheck

from mkdocs_licenseinfo import get_licenses as gl_module
from mkdocs_licenseinfo.get_licenses import (
    _split_licenses,
    get_licenses,
    LicenseCheckArgs,
    UnclosableIO,
)


class UnclosableIOTestCase(unittest.TestCase):

    def test_close(self):
        output = UnclosableIO()
        self.assertFalse(output.closed)
        output.close()
        self.assertFalse(output.closed)

    def test_force_close(self):
        output = UnclosableIO()
        self.assertFalse(output.closed)
        output.force_close()
        self.assertTrue(output.closed)


class LicenseCheckArgsTestCase(unittest.TestCase):

    def test_init_no_args(self):
        args = LicenseCheckArgs()
        self.assertEqual(args._using, 'PEP631')
        self.assertEqual(args._format, 'json')
        self.assertEqual(args._ignore_packages, [])
        self.assertEqual(args._fail_packages, [])
        self.assertEqual(args._skip_packages, [])
        self.assertEqual(args._ignore_licenses, [])
        self.assertEqual(args._fail_licenses, [])
        self.assertIsInstance(args._output, UnclosableIO)
        self.assertIsNone(args._stdout)

    def test_init_args(self):
        args = LicenseCheckArgs('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h')
        self.assertEqual(args._using, 'a')
        self.assertEqual(args._format, 'b')
        self.assertEqual(args._ignore_packages, 'c')
        self.assertEqual(args._fail_packages, 'd')
        self.assertEqual(args._skip_packages, 'e')
        self.assertEqual(args._ignore_licenses, 'f')
        self.assertEqual(args._fail_licenses, 'g')
        self.assertNotIsInstance(args._output, UnclosableIO)
        self.assertEqual(args._output, 'h')
        self.assertIsNone(args._stdout)

    def test_contextmanager(self):
        args = LicenseCheckArgs('a', 'b', ['c', 'd'], ['e', 'f'], ['g', 'h'], ['i', 'j'], ['k', 'l'])
        expected_args = [
            'licensecheck',
            '-u',
            'a',
            '--format',
            'b',
            '--ignore-packages',
            'c',
            '--ignore-packages',
            'd',
            '--fail-packages',
            'e',
            '--fail-packages',
            'f',
            '--skip-dependencies',
            'g',
            '--skip-dependencies',
            'h',
            '--ignore-licenses',
            'i',
            '--ignore-licenses',
            'j',
            '--fail-licenses',
            'k',
            '--fail-licenses',
            'l'
        ]
        self.assertNotEqual(sys.argv, expected_args)
        original_stdout = licensecheck.stdout
        self.assertNotIsInstance(licensecheck.stdout, UnclosableIO)
        with args:
            self.assertEqual(sys.argv, expected_args)
            self.assertIsInstance(licensecheck.stdout, UnclosableIO)
            self.assertEqual(args._stdout, original_stdout)
        self.assertNotEqual(sys.argv, expected_args)
        self.assertEqual(licensecheck.stdout, original_stdout)
        self.assertNotIsInstance(licensecheck.stdout, UnclosableIO)
        self.assertFalse(args._output.closed)


class GetLicensesTestCase(unittest.TestCase):

    def test_split_licenses_no_split(self):
        package = {'license': 'a'}
        _split_licenses(package)
        self.assertEqual(package, {'license': 'a', 'licenses': ['a']})

    @patch.object(gl_module, 'licensecheck', autospec=True)
    def test_get_licenses(self, lc):
        # Patch licensecheck
        def cli(*args, **kwargs):
            lc.stdout.write('{"packages": [{"a": 1, "license": "abc;; 123"}, {"b": 2, "license": "mit"}]}')
        lc.cli.side_effect = cli
        packages = get_licenses()
        self.assertEqual(packages, [{'a': 1, 'license': 'abc;; 123', 'licenses': ['abc', '123']},
                                    {'b': 2, 'license': 'mit', 'licenses': ['mit']}])
