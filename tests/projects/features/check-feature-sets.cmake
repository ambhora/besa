# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
set(_file "${BINARY_DIR}/feature-sets.json")
if(NOT EXISTS "${_file}")
  message(FATAL_ERROR "missing ${_file}")
endif()
file(READ "${_file}" _json)

string(JSON _generator GET "${_json}" generator)
if(NOT _generator STREQUAL "besa")
  message(FATAL_ERROR "expected generator 'besa', got '${_generator}':\n${_json}")
endif()

string(JSON _project_name GET "${_json}" project name)
if(NOT _project_name STREQUAL "features")
  message(FATAL_ERROR "expected project name 'features', got '${_project_name}':\n${_json}")
endif()

string(JSON _project_version GET "${_json}" project version)
if(NOT _project_version STREQUAL "1.0.0")
  message(FATAL_ERROR "expected project version '1.0.0', got '${_project_version}':\n${_json}")
endif()
string(JSON _count LENGTH "${_json}" feature-sets)
if(NOT _count EQUAL 8)
  message(FATAL_ERROR "expected 8 feature sets, got ${_count}:\n${_json}")
endif()

# Concrete feature sets are deliberately unnamed. Each row is just the features in that build.
math(EXPR _last "${_count} - 1")
foreach(_index RANGE 0 ${_last})
  string(JSON _entry GET "${_json}" feature-sets ${_index})
  string(FIND "${_entry}" "\"name\"" _name_position)
  if(NOT _name_position EQUAL -1)
    message(FATAL_ERROR "feature sets must not have synthetic names:\n${_entry}")
  endif()

  string(JSON _n LENGTH "${_json}" feature-sets ${_index} features)
  set(_implementation 0)
  if(_n GREATER 0)
    math(EXPR _feature_last "${_n} - 1")
    foreach(_findex RANGE 0 ${_feature_last})
      string(JSON _feature GET "${_json}" feature-sets ${_index} features ${_findex})
      if(_feature MATCHES "^(alpha|beta)$")
        math(EXPR _implementation "${_implementation} + 1")
      endif()
    endforeach()
  endif()
  if(NOT _implementation EQUAL 1)
    message(FATAL_ERROR "feature set must contain exactly one implementation:\n${_json}")
  endif()
endforeach()
