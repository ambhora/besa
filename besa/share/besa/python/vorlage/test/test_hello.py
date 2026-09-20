# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from vorlage import hello


def test_hello() -> None:
    assert hello() == "Hello, world!"
