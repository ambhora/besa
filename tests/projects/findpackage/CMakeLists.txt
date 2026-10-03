# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Locate the staged BESA package with a version request.
cmake_minimum_required(VERSION 3.25)
project(findpackage LANGUAGES NONE)
find_package(besa "${REQUESTED_VERSION}" CONFIG REQUIRED)
