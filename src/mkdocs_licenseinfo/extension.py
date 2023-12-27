"""Defines the extension for processing a markdown block to get the license information.

Uses a Markdown [block processor](https://python-markdown.github.io/extensions/api/#blockprocessors)
that looks for on '::licenseinfo'.

The specifics can be configured with YAML configuration in the block, and include !ENV flags:

```yaml
::license_check

    # The information on what to use for requirments (see the [licensecheck docs](https://pypi.org/project/licensecheck/#configuration-example)) - default is PEP631 (pyproject.toml)
    using: <PEP631:dev;dev-test>
    # Packages to remove (see the [licensecheck docs](https://pypi.org/project/licensecheck/#configuration-example)) - default is None, the packages in this are not shown in the section
    diff: <PEP631>
    # A list of packages to ignore
    ignore_packages: <list of packages>
    # A list of packages to fail on
    fail_packages: <list of packages>
    # A list of packages to skip
    skip_packages: <list of packages>
    # A list of licenses to ignore
    ignore_licenses: <list of licenses>
    # A list of licenses to skip
    fail_licenses: <list of licenses>
    # Set the base indent to work from - optional, can use the heading of the block instead.
    base_indent: 2
    # Set the package template to process the package into as an Jinja2 template (optional) (the github api response is passed in as package)
    package_template: "{{package.name}}"
    # Path to requirements containing folder relative to docs_dir - if not set the working dir is used
    requirements_path: <path string>
```
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, MutableSequence, TYPE_CHECKING
from xml.etree.ElementTree import Element  # nosec: B405

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from mkdocs.utils.yaml import get_yaml_loader, yaml_load

from mkdocs_licenseinfo import logger
from mkdocs_licenseinfo.render_markdown import get_licenses_as_markdown

if TYPE_CHECKING:
    from markdown import Markdown
    from markdown.blockparser import BlockParser


class LicenseInfoProcessor(BlockProcessor):
    """License info Markdown block processor."""

    regex = re.compile(r"^(?P<heading>#{1,6} *|)::licenseinfo*$", flags=re.MULTILINE)

    def __init__(
        self,
        parser: BlockParser,
        config: dict,
    ) -> None:
        """Initialize the processor."""
        super().__init__(parser=parser)
        self._config = config

    def test(self, parent: Element, block: str) -> bool:  # noqa: U100
        """Match the extension instructions."""
        logger.debug(f'Checking block: {block}')
        return bool(self.regex.search(block))

    def run(self, parent: Element, blocks: MutableSequence[str]) -> None:
        """Run code on the matched blocks to get the markdown."""
        block = blocks.pop(0)
        match = self.regex.search(block)

        if match:
            if match.start() > 0:
                self.parser.parseBlocks(parent, [block[: match.start()]])
            # removes the first line
            block = block[match.end() :]

        block, the_rest = self.detab(block)
        if the_rest:
            # This block contained unindented line(s) after the first indented
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, the_rest)

        if match:
            heading_level = match["heading"].count("#")
            # We are going to process the markdown from the releases and then
            # insert it back into the blocks to be processed as markdown
            block = self._process_block(block, heading_level)
            blocks.insert(0, block)

    def _process_block(
        self,
        yaml_block: str,
        heading_level: int = 0,
    ) -> str:
        """Process a block."""
        config = yaml_load(yaml_block, loader=get_yaml_loader()) or {}
        if heading_level is None:
            heading_level = 0
        base_indent = config.get('base_indent', heading_level)
        using = config.get('using', None)
        diff = config.get('diff', None)
        ignore_packages = config.get('ignore_packages', self._config.get('ignore_packages', None))
        fail_packages = config.get('fail_packages', self._config.get('fail_packages', None))
        skip_packages = config.get('skip_packages', self._config.get('skip_packages', None))
        ignore_licenses = config.get('ignore_licenses', self._config.get('ignore_licenses', None))
        fail_licenses = config.get('fail_licenses', self._config.get('fail_licenses', None))
        package_template = config.get('package_template', self._config.get('package_template', None))
        requirements_path = config.get('requirements_path', self._config.get('requirements_path', None))
        if requirements_path:
            requirements_path = (Path(self._config.get('docs_dir', '.')) / Path(requirements_path)).resolve()
        block = '\n\n'.join(get_licenses_as_markdown(
            using=using,
            ignore_packages=ignore_packages,
            fail_packages=fail_packages,
            skip_packages=skip_packages,
            ignore_licenses=ignore_licenses,
            fail_licenses=fail_licenses,
            diff=diff,
            package_template=package_template,
            path=requirements_path
            ))
        # We need to decrease/increase the base indent level
        if base_indent > 0:
            block = block.replace('# ', ('#'*base_indent)+'# ')
        return block


class LicenseInfoExtension(Extension):
    """The Markdown extension."""

    def __init__(self, config: dict, **kwargs: Any) -> None:
        """Initialize the object."""
        super().__init__(**kwargs)
        self._config = config

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the extension.

        Add an instance of [`LicenseInfoProcessor`][mkdocs_licenseinfo.extension.LicenseInfoProcessor]
        to the Markdown parser.
        """
        md.parser.blockprocessors.register(
            LicenseInfoProcessor(md.parser, self._config),
            "license_check",
            priority=75,  # Right before markdown.blockprocessors.HashHeaderProcessor
        )
