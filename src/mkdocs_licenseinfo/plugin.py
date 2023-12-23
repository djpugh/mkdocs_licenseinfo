"""This module contains the MkDocs plugin.

It creates a Markdown extension ([`LicenseInfoExtension`][mkdocs_licenseinfo.extension.LicenseInfoExtension]),
and adds it to `mkdocs` during the [`on_config` event hook](https://www.mkdocs.org/user-guide/plugins/#on_config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.plugins import BasePlugin

from mkdocs_licenseinfo.extension import LicenseInfoExtension

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig


class PluginConfig(Config):
    """Configuration options for `mkdocs_github_changelog` in `mkdocs.yml`."""
    ignore_packages = opt.Optional(opt.ListOfItems(opt.Type(str)))
    """Packages to ignore."""
    fail_packages = opt.Optional(opt.ListOfItems(opt.Type(str)))
    """Packages to fail on."""
    skip_packages = opt.Optional(opt.ListOfItems(opt.Type(str)))
    """Packages to skip."""
    ignore_licenses = opt.Optional(opt.ListOfItems(opt.Type(str)))
    """Licenses to ignore."""
    fail_licenses = opt.Optional(opt.ListOfItems(opt.Type(str)))
    """Licenses to fail on."""
    requirements_path = opt.Optional(opt.Type(str))
    """Path to the requirements/pyproject.toml dir relative to docs dir (otherwise uses the invocation directory)."""
    package_template = opt.Optional(opt.Type(str))
    """Jinja2 template string to override the default."""
    enabled = opt.Type(bool, default=True)
    """Enable or disable the plugin."""


class MkdocsLicenseInfoPlugin(BasePlugin[PluginConfig]):
    """`mkdocs` plugin to provide the licenseinfo."""

    def on_config(self, config: MkDocsConfig) -> MkDocsConfig | None:
        """Initialises the extension if the plugin is enabled."""
        self.config.docs_dir = config.docs_dir
        if self.config.enabled:
            licenseinfo_extension = LicenseInfoExtension(self.config)
            config.markdown_extensions.append(licenseinfo_extension)  # type: ignore[arg-type]
        return config
