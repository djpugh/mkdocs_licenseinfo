"""mkdocs_licenseinfo.

mkdocs extension to visualise package dependencies license information.
"""


def __get_version() -> str:
    """Get version information or return default if unable to do so."""
    # Default
    version = '0+unknown'
    # Development installation only
    try:
        # Look here for setuptools scm to update the version - for development environments only
        from setuptools_scm import get_version  # type: ignore
        try:
            version = get_version(root='../../', version_scheme='no-guess-dev', relative_to=__file__)
        except LookupError:
            pass
    except ImportError:
        pass
    # Development installation without setuptools_scm or installed package
    # try loading from file
    if version == '0+unknown':
        try:
            from mkdocs_licenseinfo._version import __version__  # noqa: F401
        except ImportError:
            pass
    # Development installation without setuptools_scm
    if version == '0+unknown':
        # Use the metadata
        import sys
        if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
            from importlib.metadata import PackageNotFoundError
            from importlib.metadata import version as parse_version
        else:
            from importlib_metadata import PackageNotFoundError  # type: ignore
            from importlib_metadata import version as parse_version  # type: ignore
        try:
            version = parse_version("mkdocs_licenseinfo")
        except PackageNotFoundError:
            # package is not installed
            pass
    return version


__version__ = __get_version()
