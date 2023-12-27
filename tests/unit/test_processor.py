from pathlib import Path
import unittest
from unittest.mock import patch

from markdown import Markdown
from markdown.blockparser import BlockParser
from nskit.common.contextmanagers import Env

from mkdocs_licenseinfo import extension
from mkdocs_licenseinfo.extension import LicenseInfoProcessor


class ProccesorTestCase(unittest.TestCase):

    def test_regexp_matching(self):

        test_map = {
            '::licenseinfo':  {'heading': ''},
            '## ::licenseinfo': {'heading': '## '},
            '### ::licenseinfo': {'heading': '### '}
        }
        for test_string, expected in test_map.items():
            with self.subTest(test=test_string):
                result = LicenseInfoProcessor.regex.match(test_string).groupdict()
                self.assertEqual(result, expected)

    def test_regexp_non_matching(self):

        test_strings = [
            '::abc',
            '::licenseinfo abc*21/@12'
            '::: licenseinfo'
        ]
        for test_string in test_strings:
            with self.subTest(test=test_string):
                result = LicenseInfoProcessor.regex.match(test_string)
                self.assertIsNone(result)

    # Patch get_licenses_as_markdown to return the release info
    @patch.object(extension, 'get_licenses_as_markdown')
    def test_process_block_simple(self, get_licenses_as_markdown):
        packages = 'Abacus'
        get_licenses_as_markdown.return_value = [packages]
        processor = LicenseInfoProcessor(BlockParser(Markdown()), {})
        result = processor._process_block('')
        self.assertEqual(result, packages)
        get_licenses_as_markdown.assert_called_once_with(
            using=None,
            ignore_packages=None,
            fail_packages=None,
            skip_packages=None,
            ignore_licenses=None,
            fail_licenses=None,
            diff=None,
            package_template=None,
            path=None
        )

    @patch.object(extension, 'get_licenses_as_markdown')
    def test_process_block_with_global_config(self, get_licenses_as_markdown):
        packages = 'Ipsum'
        get_licenses_as_markdown.return_value = [packages]
        global_config = {
            'ignore_packages': ['a', 'b'],
            'fail_packages': ['c', 'd'],
            'skip_packages': ['e', 'f'],
            'ignore_licenses': ['g', 'h'],
            'fail_licenses': ['i', 'j'],
            'package_template': 'abc',
            'requirements_path': '..',
            # Set by plugin
            'docs_dir': 'docs'
        }
        processor = LicenseInfoProcessor(BlockParser(Markdown()), global_config)
        result = processor._process_block('')
        self.assertEqual(result, packages)
        get_licenses_as_markdown.assert_called_once_with(
            using=None,
            ignore_packages=['a', 'b'],
            fail_packages=['c', 'd'],
            skip_packages=['e', 'f'],
            ignore_licenses=['g', 'h'],
            fail_licenses=['i', 'j'],
            diff=None,
            package_template='abc',
            path=Path('.').resolve()
        )

    @patch.object(extension, 'get_licenses_as_markdown')
    def test_process_block_with_local_config(self, get_licenses_as_markdown):
        packages = '# Ipsum'
        get_licenses_as_markdown.return_value = [packages]
        global_config = {
            'ignore_packages': ['a', 'b'],
            'fail_packages': ['c', 'd'],
            'skip_packages': ['e', 'f'],
            'ignore_licenses': ['g', 'h'],
            'fail_licenses': ['i', 'j'],
            'package_template': 'abc',
            'requirements_path': '..',
            # Set by plugin
            'docs_dir': 'docs'
        }
        processor = LicenseInfoProcessor(BlockParser(Markdown()), global_config)
        result = processor._process_block('requirements_path: ../random\nbase_indent: 3\nusing: xyz\ndiff: ghi\nignore_packages:\n  - k\n  - l\nfail_packages:\n  - m\n  - n\nskip_packages:\n  - o\n  - p\nignore_licenses:\n  - q\n  - r\nfail_licenses:\n  - s\n  - t\npackage_template: mno')
        self.assertEqual(result, '###'+packages)
        get_licenses_as_markdown.assert_called_once_with(
            using='xyz',
            ignore_packages=['k', 'l'],
            fail_packages=['m', 'n'],
            skip_packages=['o', 'p'],
            ignore_licenses=['q', 'r'],
            fail_licenses=['s', 't'],
            diff='ghi',
            package_template='mno',
            path=Path('random').absolute()
        )


    @patch.object(extension, 'get_licenses_as_markdown')
    def test_process_block_with_env(self, get_licenses_as_markdown):
        packages = 'Sit'
        get_licenses_as_markdown.return_value = [packages]
        global_config = {
            'ignore_packages': ['a', 'b'],
            'fail_packages': ['c', 'd'],
            'skip_packages': ['e', 'f'],
            'ignore_licenses': ['g', 'h'],
            'fail_licenses': ['i', 'j'],
            'package_template': 'abc',
            'requirements_path': '..',
            # Set by plugin
            'docs_dir': 'docs'
        }
        processor = LicenseInfoProcessor(BlockParser(Markdown()), global_config)
        with Env(override={'PACKAGE_TEMPLATE': 'abcdef'}):
            result = processor._process_block('using: xyz\ndiff: ghi\nignore_packages:\n  - k\n  - l\nfail_packages:\n  - m\n  - n\nskip_packages:\n  - o\n  - p\nignore_licenses:\n  - q\n  - r\nfail_licenses:\n  - s\n  - t\npackage_template: !ENV PACKAGE_TEMPLATE')
        self.assertEqual(result, packages)
        get_licenses_as_markdown.assert_called_once_with(
            using='xyz',
            ignore_packages=['k', 'l'],
            fail_packages=['m', 'n'],
            skip_packages=['o', 'p'],
            ignore_licenses=['q', 'r'],
            fail_licenses=['s', 't'],
            diff='ghi',
            package_template='abcdef',
            path=Path('.').resolve()
        )

    @patch.object(extension, 'get_licenses_as_markdown')
    def test_process_block_with_heading_level(self, get_licenses_as_markdown):
        packages = '# Amet'
        get_licenses_as_markdown.return_value = [packages]
        processor = LicenseInfoProcessor(BlockParser(Markdown()), {})
        result = processor._process_block('', 2)
        self.assertEqual(result, '##'+packages)

    def test_test_matching(self):
        test_strings = [
            '::licenseinfo\n    using: 123',
            '## ::licenseinfo',
            '### ::licenseinfo',
        ]
        processor = LicenseInfoProcessor(BlockParser(Markdown()), {})
        for test_string in test_strings:
            with self.subTest(test_string=test_string):
                self.assertTrue(processor.test(None, test_string))

    def test_test_not_matching(self):
        test_strings = [
            '::licenseinfo abc',
            '::licenseinfo abc*21/@12'
            '::: licenseinfo',
            '::licenseinfo abcder'
            ':: licenseinfo abc/def\n    using: 123',
        ]
        processor = LicenseInfoProcessor(BlockParser(Markdown()), {})
        for test_string in test_strings:
            with self.subTest(test_string=test_string):
                self.assertFalse(processor.test(None, test_string))

    @patch.object(extension, 'get_licenses_as_markdown')
    def test_run_matching_block(self, get_licenses_as_markdown):
        packages = '# Consectetur'
        get_licenses_as_markdown.return_value = [packages]
        blocks = ['::licenseinfo', 'b']
        processor = LicenseInfoProcessor(BlockParser(Markdown()), {})
        processor.run(None, blocks)
        self.assertEqual(blocks, [packages, 'b'])

    def test_run_no_matching_block(self):
        blocks = ['a', 'b']
        processor = LicenseInfoProcessor(BlockParser(Markdown()), {})
        processor.run(None, blocks)
        self.assertEqual(blocks, ['a', 'b'])
