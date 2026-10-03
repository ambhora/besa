# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
import copy as _copy
import json as _json
import pathlib as _pathlib

import pytest as _pytest

import besa_dev.compilers as _compilers

CONFIG = _pathlib.Path(__file__).parents[1] / "etc" / "compilers.json"


def raw() -> dict:
    return _json.loads(CONFIG.read_text(encoding="utf-8"))


def test_repository_configuration_is_canonical() -> None:
    config = _compilers.load(CONFIG)
    assert _compilers.dump(config) == CONFIG.read_text(encoding="utf-8")


def test_repository_configuration_respects_minimums() -> None:
    config = _compilers.load(CONFIG)
    for compiler in config.compilers:
        family = _compilers.family(config, compiler.family)
        assert compiler.version >= family.minimum


def test_parse_orders_compilers_newest_first() -> None:
    data = raw()
    data["compilers"].reverse()
    config = _compilers.parse(data)
    versions = [c.version for c in config.compilers if c.family == "gcc"]
    assert versions == sorted(versions, reverse=True)
    assert config.compilers[0].family == "gcc"


def test_dump_round_trips() -> None:
    config = _compilers.parse(raw())
    assert _compilers.parse(_json.loads(_compilers.dump(config))) == config


@_pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(schema=2), "schema must be 1"),
        (lambda d: d.update(extra=1), "unknown keys: extra"),
        (lambda d: d["families"]["gcc"].pop("image"), "missing keys: image"),
        (
            lambda d: d["families"]["gcc"]["discovery"].update(kind="ftp"),
            "expected one of",
        ),
        (
            lambda d: d["families"]["gcc"]["discovery"].update(pattern="\\d+"),
            "one group",
        ),
        (
            lambda d: d["families"]["gcc"]["discovery"].update(pattern="("),
            "pattern",
        ),
        (
            lambda d: d["compilers"].append(
                {"family": "msvc", "version": 19, "experimental": False}
            ),
            "unknown family 'msvc'",
        ),
        (
            lambda d: d["compilers"].append(dict(d["compilers"][0])),
            "more than once",
        ),
        (
            lambda d: d["compilers"][0].update(version=True),
            "positive integer",
        ),
        (
            lambda d: d["compilers"][0].update(experimental="no"),
            "true or false",
        ),
    ],
)
def test_parse_rejects_malformed_configuration(mutate, message) -> None:
    data = _copy.deepcopy(raw())
    mutate(data)
    with _pytest.raises(_compilers.ConfigError, match=message):
        _compilers.parse(data)


def test_expand_substitutes_every_placeholder() -> None:
    assert _compilers.expand("a{version}b{version}", 21) == "a21b21"
