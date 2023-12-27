"""Get licenses and convert to markdown."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

if sys.version_info.major >= 3 and sys.version_info.minor >= 10:
    from importlib.metadata import entry_points
else:
    from backports.entry_points_selectable import entry_points

from jinja2 import Environment

from mkdocs_licenseinfo import logger
from mkdocs_licenseinfo.get_licenses import get_licenses

PACKAGE_TEMPLATE = "# [{{package.name}}]({{package.homePage}})\n{% for license in package.licenses %}``{{license}}`` {% endfor %} \n*Version Checked: {{package.version}}*  \nAuthor: {{package.author}}"


class _EnvironmentFactory():
    """Jinja2 Environment Factory to allow for extension/customisation.

    Adapted from https://djpugh.github.io/nskit.
    """

    def __init__(self):
        """Initialise the factory."""
        self._environment = None

    @property
    def environment(self) -> Environment:
        """Handle caching the environment object so it is lazily initialised."""
        if self._environment is None:
            self._environment = self.get_environment()
            self.add_extensions(self._environment)
        return self._environment

    def add_extensions(self, environment: Environment):
        """Add Extensions to the environment object."""
        # Assuming no risk of extension clash
        extensions = []
        # Load from JSON
        for ext in json.loads(os.environ.get('MKDOCS_LICENSEINFO_JINJA_EXTENSIONS', '[]')):
            extensions.append(ext)
        for extension in list(set(extensions)):
            environment.add_extension(extension)

    def get_environment(self) -> Environment:
        """Get the environment object based on the env var."""
        selected_method = os.environ.get('MKDOCS_LICENSEINFO_JINJA_ENVIRONMENT_FACTORY', None)
        if selected_method is None or selected_method.lower() == 'default':
            # This is our simple implementation
            selected_method = 'default'
        for ep in entry_points().select(group='mkdocs_licenseinfo.jinja_environment_factory', name=selected_method):
            return ep.load()()

    @staticmethod
    def default_environment():
        """Get the default environment object."""
        return Environment()  # nosec B701


JINJA_ENVIRONMENT_FACTORY = _EnvironmentFactory()


def get_licenses_as_markdown(
        using='PEP631',
        ignore_packages: list[str] | None = None,
        fail_packages: list[str] | None = None,
        skip_packages: list[str] | None = None,
        ignore_licenses: list[str] | None = None,
        fail_licenses: list[str] | None = None,
        diff: str | None = None,
        package_template: str | None = PACKAGE_TEMPLATE,
        path: str | Path | None = None
):
    """Get the licenses and render them as markdown strings."""
    jinja_environment = JINJA_ENVIRONMENT_FACTORY.environment
    logger.debug('Getting licenses')
    packages = get_licenses(using, ignore_packages, fail_packages, skip_packages, ignore_licenses, fail_licenses, path=path)
    logger.info(f'Found {len(packages)} packages')

    diff_packages = []
    if diff:
        logger.debug('Getting diff licenses')
        diff_packages = get_licenses(diff, ignore_packages, fail_packages, skip_packages, ignore_licenses, fail_licenses, path=path)
        logger.info(f'Found {len(diff_packages)} diff packages')
    selected_package_names = list({u['name'] for u in packages} - {u['name'] for u in diff_packages})
    selected_packages = [u for u in packages if u['name'] in selected_package_names]
    logger.info(f'Processing remaining {len(selected_packages)} packages')
    if package_template is None:
        package_template = PACKAGE_TEMPLATE
    logger.debug('Rendering licenses')
    return [jinja_environment.from_string(package_template).render(package=package) for package in selected_packages]
