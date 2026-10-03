#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
# Run the BESA test suite inside a compiler image. Started by `besa-dev run`,
# which passes the compiler description from dev/etc/compilers.json as:
#
#   BESA_CI_ID      compiler identifier, e.g. gcc-16; names the build tree
#   BESA_CI_SETUP   shell commands that install the compiler and python3-venv
#   BESA_CI_PATH    directories prepended to PATH (may be empty)
#   CC, CXX         compilers used by the test projects
set -euo pipefail

: "${BESA_CI_ID:?BESA_CI_ID is required}"
: "${CC:?CC is required}"
: "${CXX:?CXX is required}"

if [[ -n "${BESA_CI_SETUP:-}" ]]; then
  bash -euo pipefail -c "${BESA_CI_SETUP}"
fi

# CMake, Ninja, and gcovr come from PyPI so every image gets the same versions.
python3 -m venv /opt/besa-ci
/opt/besa-ci/bin/python -m pip install --quiet --upgrade pip
/opt/besa-ci/bin/python -m pip install --quiet cmake ninja gcovr
export PATH="/opt/besa-ci/bin${BESA_CI_PATH:+:${BESA_CI_PATH}}:${PATH}"

"${CC}" --version
"${CXX}" --version
cmake --version

build="build/ci-${BESA_CI_ID}"
rm -rf "${build}"
cmake -S . -B "${build}" -G Ninja
ctest --test-dir "${build}" --output-on-failure --parallel "$(nproc)"
