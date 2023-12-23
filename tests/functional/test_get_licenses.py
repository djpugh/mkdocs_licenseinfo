import unittest

from nskit.common.contextmanagers import ChDir

from mkdocs_licenseinfo.get_licenses import get_licenses


class LicenseCheckTestCase(unittest.TestCase):

    def test_get_licenses(self):
        with ChDir():
            with open('requirements.txt', 'w') as f:
                f.write('aenum\norjson\nnskit')
            licenses = get_licenses(using='requirements:requirements.txt')
            self.assertGreater(len(licenses), 3)
            package_names = [u['name'] for u in licenses]
            self.assertIn('orjson', package_names)
            self.assertIn('aenum', package_names)
            self.assertIn('nskit', package_names)
