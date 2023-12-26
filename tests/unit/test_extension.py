import unittest

from markdown import Markdown

from mkdocs_licenseinfo.extension import LicenseInfoExtension, LicenseInfoProcessor


class LicenseInfoExtensionTestCase(unittest.TestCase):

    def test_init(self):
        ext = LicenseInfoExtension({'a': 1})
        self.assertEqual(ext._config, {'a': 1})

    def test_extendMarkdown(self):
        md = Markdown()
        ext = LicenseInfoExtension({'a': 1})
        ext.extendMarkdown(md)
        self.assertTrue(any([isinstance(proc, LicenseInfoProcessor) for proc in md.parser.blockprocessors]))
