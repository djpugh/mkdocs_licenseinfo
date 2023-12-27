mkdocs extension to visualise package dependencies license information

## Why?
For software supply chain security and legal compliance, it's important to make it easy to understand a library's dependencies (and their licenses).

``mkdocs_licenseinfo`` can be used to generate sbom license info in ``mkdocs`` documentation automatically and without needing another commit.

## Using mkdocs_licenseinfo

### Configuration

In the ``mkdocs.yml`` file, add the plugin and any configuration options to override the defaults:

```yaml

plugins:
    ...
    - mkdocs_licenseinfo:
        # Packages to ignore.
        ignore_packages: <List of packages>
        # Packages to fail on.
        fail_packages: <List of packages>
        # Packages to skip.
        skip_packages: <List of packages>
        # Licenses to ignore.
        ignore_licenses: <List of licenses>
        # Licenses to fail on.
        fail_licenses: <List of licenses>
        # Path to the requirements/pyproject.toml dir relative to docs dir (otherwise uses the working directory).
        requirements_path: str
        # Jinja2 template string to override the default.
        package_template: str
        # Enable or disable the plugin.
        enabled: True
```

Then in the file you want to implement the license info (e.g. ``sbom.md``):

```
markdown

::licenseinfo
    base_indent: 2
    using: PEP631:dev
    diff: PEP631
    ignore_packages: <list of packages to ignore>
    fail_packages: <list of packages to fail>
    skip_packages: <list of packages to skip>
    ignore_licenses: <list of licenses to ignore>
    fail_licenses: <list of licenses to fail>
    package_template: <jinja2 str>
```

All of the options are optional when configuring, and the indent level can be set by using ``#`` in front of the ``::licenseinfo`` line like normal markdown headings, but the ``base_indent`` option will override this.

The remaining optins can override/set the value specifically for that command (if you have multiple license info settings).


### Setting the template

The ``package_template`` option sets a ``jinja2`` template string to format the ``package`` object (from the array of packages).

The default template should be good, but if you have specific needs, you can create a custom template and define it in either the global or local config. The package object is passed in as ``package``:

```
"# [{{package.name}}]({{package.homePage}})\n{% for license in package.licenses %}``{{license}}`` {% endfor %} \n*Version Checked: {{package.version}}*  \nAuthor: {{package.author}}"
```

#### Jinja Environment Customisation

If you need specific extensions in the jinja environment, you can add them in using a json encoded list on the ``MKDOCS_LICENSE_INFO_JINJA_EXTENSIONS`` environment variables.


You can also customise the jinja2 environment initialisation through the ``[project.entry-points."mkdocs_licenseinfo.jinja_environment_factory"]`` entrypoint, and then setting the ``MKDOCS_LICENSE_INFO_JINJA_ENVIRONMENT_FACTORY`` environment variable to the name of the entrypoint.