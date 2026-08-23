# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from .library import hello


def main() -> int:
    print(hello())
    return 0
