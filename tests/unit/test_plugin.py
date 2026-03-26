import unittest

from mkdocs.config.base import ValidationError
from mkdocs.config.defaults import MkDocsConfig
from nskit.common.contextmanagers import Env

from mkdocs_licenseinfo.plugin import LicenseInfoExtension, MkdocsLicenseInfoPlugin


class MkdocsLicenseInfoPluginTestCase(unittest.TestCase):
    def test_config_defaults(self):
        plugin = MkdocsLicenseInfoPlugin()
        resp = plugin.load_config({})
        expected = {
            "ignore_packages": None,
            "fail_packages": None,
            "skip_packages": None,
            "ignore_licenses": None,
            "fail_licenses": None,
            "requirements_path": None,
            "package_template": None,
            "enabled": True,
        }
        self.assertEqual(plugin.config, expected)
        self.assertEqual(resp, ([], []))

    def test_config_overriden_ok(self):
        plugin = MkdocsLicenseInfoPlugin()
        resp = plugin.load_config(
            {
                "ignore_packages": ["a", "b"],
                "fail_packages": ["c", "d"],
                "skip_packages": ["e", "f"],
                "ignore_licenses": ["g", "h"],
                "fail_licenses": ["i", "j"],
                "requirements_path": "x",
                "package_template": "a",
                "enabled": False,
            }
        )
        expected = {
            "ignore_packages": ["a", "b"],
            "fail_packages": ["c", "d"],
            "skip_packages": ["e", "f"],
            "ignore_licenses": ["g", "h"],
            "fail_licenses": ["i", "j"],
            "requirements_path": "x",
            "package_template": "a",
            "enabled": False,
        }
        self.assertEqual(plugin.config, expected)
        self.assertEqual(resp, ([], []))

    def test_config_overriden_bad(self):
        plugin = MkdocsLicenseInfoPlugin()
        resp = plugin.load_config(
            {
                "ignore_packages": "a",
                "fail_packages": "c",
                "skip_packages": "e",
                "ignore_licenses": "g",
                "fail_licenses": "i",
                "requirements_path": ["a", "b"],
                "package_template": ["a", "b"],
                "enabled": "x",
            }
        )
        # mkdocs may stop at the first validation error or collect all
        self.assertGreater(len(resp[0]), 0)
        self.assertEqual(resp[0][0][0], "ignore_packages")
        self.assertIsInstance(resp[0][0][1], ValidationError)

    def test_on_config(self):
        plugin = MkdocsLicenseInfoPlugin()
        config = MkDocsConfig()
        plugin.load_config({})
        plugin.on_config(config)
        self.assertIsInstance(config.markdown_extensions[-1], LicenseInfoExtension)
        ext = config.markdown_extensions[-1]

        expected = {
            "ignore_packages": None,
            "fail_packages": None,
            "skip_packages": None,
            "ignore_licenses": None,
            "fail_licenses": None,
            "requirements_path": None,
            "package_template": None,
            "enabled": True,
        }
        self.assertEqual(ext._config, expected)

    def test_on_config_from_env(self):
        with Env(override={"PACKAGE_TEMPLATE": "abc"}):
            import os
            import tempfile

            original_dir = os.getcwd()
            tmp_dir = tempfile.mkdtemp()
            try:
                os.chdir(tmp_dir)
                plugin = MkdocsLicenseInfoPlugin()
                config = MkDocsConfig()
                # Load the env var
                config_file = "mkdocs.yml"
                with open(config_file, "w") as f:
                    f.write(
                        "plugins:\n- mkdocs_github_changelog:\n    requirements_path: x\n    package_template: !ENV PACKAGE_TEMPLATE"
                    )
                with open(config_file) as f:
                    config.load_file(f)
                plugin.load_config(config.plugins[0]["mkdocs_github_changelog"])
                plugin.on_config(config)
                self.assertIsInstance(config.markdown_extensions[-1], LicenseInfoExtension)
                ext = config.markdown_extensions[-1]
                expected = {
                    "ignore_packages": None,
                    "fail_packages": None,
                    "skip_packages": None,
                    "ignore_licenses": None,
                    "fail_licenses": None,
                    "requirements_path": "x",
                    "package_template": "abc",
                    "enabled": True,
                }
                self.assertEqual(ext._config, expected)
            finally:
                os.chdir(original_dir)
