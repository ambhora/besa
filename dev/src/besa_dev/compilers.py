# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""The compiler configuration in dev/etc/compilers.json.

The file has three parts. ``families`` describes, per compiler family, how a
version is discovered upstream, which container image provides it, and how the
image is prepared. ``compilers`` lists the concrete versions under test.
Strings in a family may contain ``{version}``, replaced by the major version.
"""

import dataclasses as _dataclasses
import json as _json
import pathlib as _pathlib
import re as _re
import typing as _typing

SCHEMA = 1
DISCOVERY_KINDS = ("docker-hub-tags", "github-releases")
VERSION_PLACEHOLDER = "{version}"


class ConfigError(Exception):
    """The compiler configuration is malformed."""


@_dataclasses.dataclass(frozen=True)
class Discovery:
    """Where the released major versions of a family are found."""

    kind: str
    repository: str
    pattern: str


@_dataclasses.dataclass(frozen=True)
class Family:
    """How the compilers of one family are discovered and installed."""

    name: str
    minimum: int
    discovery: Discovery
    image: str
    setup: tuple[str, ...]
    cc: str
    cxx: str
    path: str


@_dataclasses.dataclass(frozen=True)
class Compiler:
    """One compiler version under test."""

    family: str
    version: int
    experimental: bool


@_dataclasses.dataclass(frozen=True)
class Config:
    """The complete compiler configuration."""

    families: tuple[Family, ...]
    compilers: tuple[Compiler, ...]


def _require_table(value: _typing.Any, where: str) -> dict[str, _typing.Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: expected an object")
    return value


def _require_keys(
    table: dict[str, _typing.Any], keys: set[str], where: str
) -> None:
    missing = sorted(keys - set(table))
    unknown = sorted(set(table) - keys)
    if missing:
        raise ConfigError(f"{where}: missing keys: {', '.join(missing)}")
    if unknown:
        raise ConfigError(f"{where}: unknown keys: {', '.join(unknown)}")


def _require_string(value: _typing.Any, where: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{where}: expected a string")
    return value


def _require_version(value: _typing.Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigError(f"{where}: expected a positive integer")
    return value


def _parse_discovery(value: _typing.Any, where: str) -> Discovery:
    table = _require_table(value, where)
    _require_keys(table, {"kind", "repository", "pattern"}, where)
    kind = _require_string(table["kind"], f"{where}.kind")
    if kind not in DISCOVERY_KINDS:
        expected = ", ".join(DISCOVERY_KINDS)
        raise ConfigError(f"{where}.kind: expected one of {expected}")
    pattern = _require_string(table["pattern"], f"{where}.pattern")
    try:
        compiled = _re.compile(pattern)
    except _re.error as error:
        raise ConfigError(f"{where}.pattern: {error}") from error
    if compiled.groups != 1:
        raise ConfigError(
            f"{where}.pattern: expected one group capturing the major version"
        )
    return Discovery(
        kind=kind,
        repository=_require_string(table["repository"], f"{where}.repository"),
        pattern=pattern,
    )


def _parse_family(name: str, value: _typing.Any) -> Family:
    where = f"families.{name}"
    table = _require_table(value, where)
    keys = {"minimum", "discovery", "image", "setup", "cc", "cxx", "path"}
    _require_keys(table, keys, where)
    setup = table["setup"]
    if not isinstance(setup, list):
        raise ConfigError(f"{where}.setup: expected an array of strings")
    return Family(
        name=name,
        minimum=_require_version(table["minimum"], f"{where}.minimum"),
        discovery=_parse_discovery(table["discovery"], f"{where}.discovery"),
        image=_require_string(table["image"], f"{where}.image"),
        setup=tuple(
            _require_string(item, f"{where}.setup[{index}]")
            for index, item in enumerate(setup)
        ),
        cc=_require_string(table["cc"], f"{where}.cc"),
        cxx=_require_string(table["cxx"], f"{where}.cxx"),
        path=_require_string(table["path"], f"{where}.path"),
    )


def _parse_compiler(
    value: _typing.Any, families: set[str], where: str
) -> Compiler:
    table = _require_table(value, where)
    _require_keys(table, {"family", "version", "experimental"}, where)
    family = _require_string(table["family"], f"{where}.family")
    if family not in families:
        raise ConfigError(f"{where}.family: unknown family '{family}'")
    experimental = table["experimental"]
    if not isinstance(experimental, bool):
        raise ConfigError(f"{where}.experimental: expected true or false")
    return Compiler(
        family=family,
        version=_require_version(table["version"], f"{where}.version"),
        experimental=experimental,
    )


def canonical(config: Config) -> Config:
    """Order compilers by family declaration order, newest version first."""
    order = {family.name: index for index, family in enumerate(config.families)}
    compilers = sorted(
        config.compilers,
        key=lambda compiler: (order[compiler.family], -compiler.version),
    )
    return Config(families=config.families, compilers=tuple(compilers))


def parse(data: _typing.Any) -> Config:
    """Validate decoded JSON and return the canonical configuration."""
    table = _require_table(data, "compilers.json")
    _require_keys(table, {"schema", "families", "compilers"}, "compilers.json")
    if table["schema"] != SCHEMA:
        raise ConfigError(f"compilers.json: schema must be {SCHEMA}")
    raw_families = _require_table(table["families"], "families")
    families = tuple(
        _parse_family(name, value) for name, value in raw_families.items()
    )
    raw_compilers = table["compilers"]
    if not isinstance(raw_compilers, list):
        raise ConfigError("compilers: expected an array")
    names = {family.name for family in families}
    compilers = tuple(
        _parse_compiler(item, names, f"compilers[{index}]")
        for index, item in enumerate(raw_compilers)
    )
    seen: set[tuple[str, int]] = set()
    for compiler in compilers:
        key = (compiler.family, compiler.version)
        if key in seen:
            raise ConfigError(
                f"compilers: {compiler.family} {compiler.version} is listed"
                " more than once"
            )
        seen.add(key)
    return canonical(Config(families=families, compilers=compilers))


def load(path: _pathlib.Path) -> Config:
    """Read and validate a compiler configuration file."""
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as error:
        raise ConfigError(f"cannot read {path}: {error}") from error
    return parse(data)


def dump(config: Config) -> str:
    """Serialize a configuration as canonical JSON text."""
    families = {
        family.name: {
            "minimum": family.minimum,
            "discovery": {
                "kind": family.discovery.kind,
                "repository": family.discovery.repository,
                "pattern": family.discovery.pattern,
            },
            "image": family.image,
            "setup": list(family.setup),
            "cc": family.cc,
            "cxx": family.cxx,
            "path": family.path,
        }
        for family in config.families
    }
    compilers = [
        {
            "family": compiler.family,
            "version": compiler.version,
            "experimental": compiler.experimental,
        }
        for compiler in canonical(config).compilers
    ]
    data = {"schema": SCHEMA, "families": families, "compilers": compilers}
    return _json.dumps(data, indent=2) + "\n"


def save(config: Config, path: _pathlib.Path) -> None:
    """Write a configuration file in canonical form."""
    path.write_text(dump(config), encoding="utf-8")


def family(config: Config, name: str) -> Family:
    """Return the family called name."""
    for candidate in config.families:
        if candidate.name == name:
            return candidate
    raise ConfigError(f"unknown family '{name}'")


def expand(template: str, version: int) -> str:
    """Substitute the major version into a family template string."""
    return template.replace(VERSION_PLACEHOLDER, str(version))
