# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Locate the staged BESA package with a version request.
cmake_minimum_required(VERSION 4.3)
project(findpackage LANGUAGES NONE)
find_package(besa "${REQUESTED_VERSION}" CONFIG REQUIRED)
