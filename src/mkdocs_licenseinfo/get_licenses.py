"""Get licence information for packages."""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404
import sys
from email.header import decode_header
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as get_metadata
from urllib.request import urlopen

from mkdocs_licenseinfo import logger

PYPROJECT_TOML = "pyproject.toml"


def _parse_using(using: str) -> tuple[list[str], list[str], list[str]]:
    """Parse the legacy 'using' parameter into requirements_paths, groups, and extras.

    Supports formats:
        - ``PEP631`` — read from pyproject.toml
        - ``PEP631:dev;dev-test`` — read from pyproject.toml with groups
        - ``requirements:path/to/requirements.txt`` — read from requirements file

    Args:
        using: The using specification string.

    Returns:
        Tuple of (requirements_paths, groups, extras).
    """
    if using.startswith("requirements:"):
        paths = using.split(":", 1)[1]
        return [p.strip() for p in paths.split(";") if p.strip()], [], []
    if ":" in using:
        _, groups_str = using.split(":", 1)
        groups = [g.strip() for g in groups_str.split(";") if g.strip()]
        return [PYPROJECT_TOML], groups, []
    return [PYPROJECT_TOML], [], []


def _read_deps_from_pyproject(
    pyproject_path: Path,
    groups: list[str],
) -> list[str]:
    """Read dependency names from a pyproject.toml file.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        groups: Optional dependency groups to include.

    Returns:
        List of dependency specifier strings.
    """
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    deps = list(data.get("project", {}).get("dependencies", []))
    optional_deps = data.get("project", {}).get("optional-dependencies", {})
    dep_groups = data.get("dependency-groups", {})
    for group in groups:
        group_deps = optional_deps.get(group, dep_groups.get(group, []))
        # Filter out dependency-group include directives (dicts like {include-group = "..."})
        deps.extend(d for d in group_deps if isinstance(d, str))
    return deps


def _read_deps_from_requirements(req_path: Path) -> list[str]:
    """Read dependency specifiers from a requirements.txt file.

    Args:
        req_path: Path to the requirements file.

    Returns:
        List of dependency specifier strings.
    """
    deps = []
    for line in req_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            deps.append(line)
    return deps


def _parse_compile_line(line: str) -> tuple[str, str | tuple[str, str] | None]:
    """Classify a single line from uv pip compile output.

    Returns:
        A tuple of (type, value) where type is 'package', 'via', or 'skip'.
    """
    stripped = line.strip()
    if not stripped:
        return ("skip", None)
    match = re.match(r"^([a-zA-Z0-9_.-]+)==([^\s;]+)", stripped)
    if match:
        return ("package", (match.group(1), match.group(2)))
    if stripped.startswith("# via"):
        dep = stripped[5:].strip()
        return ("via", dep) if dep else ("skip", None)
    if stripped.startswith("#"):
        dep = stripped.lstrip("#").strip()
        return ("via", dep) if dep else ("skip", None)
    return ("skip", None)


def _parse_compile_output(output: str) -> list[tuple[str, str, list[str]]]:
    """Parse uv pip compile output into (name, version, needed_by) tuples."""
    packages = []
    current_pkg = None
    via: list[str] = []
    for line in output.splitlines():
        kind, value = _parse_compile_line(line)
        if kind == "package":
            if current_pkg:
                packages.append((*current_pkg, via))
            current_pkg = value
            via = []
        elif kind == "via" and current_pkg:
            via.append(value)
    if current_pkg:
        packages.append((*current_pkg, via))
    return packages


def _resolve_deps(dep_specifiers: list[str]) -> list[tuple[str, str, list[str]]]:
    """Resolve dependency specifiers to concrete name-version pairs using uv.

    Falls back to parsing specifiers directly if uv is not available.

    Args:
        dep_specifiers: List of PEP 508 dependency strings.

    Returns:
        List of (name, version, needed_by) tuples.
    """
    try:
        result = subprocess.run(  # nosec B603
            [sys.executable, "-m", "uv", "pip", "compile", "--no-header", "-"],
            input="\n".join(dep_specifiers),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return _parse_compile_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: just extract package names, look up installed versions
    packages = []
    for spec in dep_specifiers:
        name = re.split(r"[><=!;\[\s]", spec)[0].strip()
        if name:
            try:
                meta = get_metadata(name)
                packages.append((meta["Name"], meta["Version"], []))
            except PackageNotFoundError:
                packages.append((name, "unknown", []))
    return packages


def _decode_header(value: str) -> str:
    """Decode RFC 2047 encoded header values."""
    parts = decode_header(value)
    return "".join(part.decode(charset or "utf-8") if isinstance(part, bytes) else part for part, charset in parts)


def _get_licence_from_metadata(meta) -> str:
    """Extract the licence string from package metadata.

    Checks License-Expression (PEP 639), License field, and classifiers.

    Args:
        meta: Package metadata object.

    Returns:
        Licence string.
    """
    # PEP 639
    license_expr = meta.get("License-Expression")
    if license_expr and license_expr.strip():
        return license_expr.strip().upper()
    # Legacy License field
    license_field = meta.get("License")
    if license_field and license_field.strip() and len(license_field.strip()) < 200:
        return license_field.strip().upper()
    # Classifiers
    classifiers = meta.get_all("Classifier") or []
    license_classifiers = [c.split(" :: ")[-1] for c in classifiers if c.startswith("License ::")]
    if license_classifiers:
        return ";; ".join(c.upper() for c in license_classifiers)
    return "UNKNOWN"


def _get_home_page(meta) -> str:
    """Extract the home page URL from package metadata."""
    home_page = meta.get("Home-page") or ""
    if home_page:
        return home_page
    urls = meta.get_all("Project-URL") or []
    for url_entry in urls:
        if "," in url_entry:
            label, url = url_entry.split(",", 1)
            if label.strip().lower() in ("homepage", "home", "repository", "source"):
                return url.strip()
    if urls and "," in urls[0]:
        return urls[0].split(",", 1)[-1].strip()
    return ""


def _get_author(meta) -> str:
    """Extract and clean the author name from package metadata."""
    author = meta.get("Author") or meta.get("Author-email") or ""
    if author:
        author = _decode_header(author)
        author = re.sub(r"\s*<[^>]+>", "", author).strip()  # nosec - no ReDoS: [^>]+ is unambiguous
    return author


def _get_package_info(name: str, version: str) -> dict:
    """Get package information from installed metadata or PyPI.

    Args:
        name: Package name.
        version: Package version.

    Returns:
        Dictionary with package information.
    """
    try:
        meta = get_metadata(name)
        return {
            "name": meta["Name"],
            "version": meta["Version"],
            "homePage": _get_home_page(meta),
            "author": _get_author(meta),
            "license": _get_licence_from_metadata(meta),
        }
    except PackageNotFoundError:
        return _get_package_info_from_pypi(name, version)


def _get_package_info_from_pypi(name: str, version: str) -> dict:
    """Fetch package information from PyPI as a fallback.

    Args:
        name: Package name.
        version: Package version.

    Returns:
        Dictionary with package information.
    """
    info = {
        "name": name,
        "version": version,
        "homePage": "",
        "author": "",
        "license": "UNKNOWN",
    }
    try:
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urlopen(url, timeout=10) as resp:  # nosec B310
            data = json.loads(resp.read())
        pypi_info = data.get("info", {})
        info["author"] = pypi_info.get("author") or pypi_info.get("author_email") or ""
        info["author"] = re.sub(r"\s*<[^>]+>", "", info["author"]).strip()  # nosec - no ReDoS: [^>]+ is unambiguous
        info["homePage"] = pypi_info.get("home_page") or pypi_info.get("project_url") or ""
        license_str = pypi_info.get("license") or ""
        if license_str and len(license_str.strip()) < 200:
            info["license"] = license_str.strip().upper()
        elif pypi_info.get("classifiers"):
            lc = [c.split(" :: ")[-1] for c in pypi_info["classifiers"] if c.startswith("License ::")]
            if lc:
                info["license"] = ";; ".join(c.upper() for c in lc)
    except Exception:
        logger.debug(f"Failed to fetch PyPI info for {name}=={version}")
    return info


def _split_licenses(package: dict) -> None:
    """Split the licence string into a list of individual licences."""
    package["licenses"] = [u.strip() for u in package["license"].split(";;")]


def _collect_dep_specifiers(
    requirements_paths: list[str],
    groups: list[str],
) -> list[str]:
    """Collect dependency specifiers from requirement sources."""
    dep_specifiers = []
    for req_path_str in requirements_paths:
        req_path = Path(req_path_str)
        if not req_path.exists():
            logger.warning(f"Requirements path not found: {req_path}")
            continue
        if req_path.name == PYPROJECT_TOML:
            dep_specifiers.extend(_read_deps_from_pyproject(req_path, groups))
        else:
            dep_specifiers.extend(_read_deps_from_requirements(req_path))
    return dep_specifiers


def get_licenses(
    using: str = "PEP631",
    ignore_packages: list[str] | None = None,
    fail_packages: list[str] | None = None,
    skip_packages: list[str] | None = None,
    ignore_licenses: list[str] | None = None,
    fail_licenses: list[str] | None = None,
    path: str | None = None,
) -> list[dict]:
    """Get the licences for dependencies.

    Args:
        using: Requirements source specification.
        ignore_packages: Packages to ignore (excluded from results).
        fail_packages: Unused, kept for API compatibility.
        skip_packages: Packages to skip (excluded from results).
        ignore_licenses: Unused, kept for API compatibility.
        fail_licenses: Unused, kept for API compatibility.
        path: Path to the directory containing the requirements file.

    Returns:
        List of package dictionaries with licence information.
    """
    if using is None:
        using = "PEP631"

    original_path = None
    if path:
        original_path = Path.cwd()
        os.chdir(str(path))

    try:
        logger.info(f"Getting licenses for: {using} in path: {path}")
        requirements_paths, groups, _extras = _parse_using(using)
        dep_specifiers = _collect_dep_specifiers(requirements_paths, groups)

        if not dep_specifiers:
            logger.warning("No dependencies found")
            return []

        resolved = _resolve_deps(dep_specifiers)
        skip_set = {n.lower() for n in (ignore_packages or [])} | {n.lower() for n in (skip_packages or [])}

        packages = []
        for name, version, needed_by in sorted(resolved):
            if name.lower() in skip_set:
                continue
            pkg = _get_package_info(name, version)
            pkg["neededBy"] = needed_by
            pkg["direct"] = len(needed_by) == 0
            _split_licenses(pkg)
            packages.append(pkg)

        return packages
    finally:
        if original_path:
            os.chdir(str(original_path))
