# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Drive one BESA test project through configure, build, test, install, and consumption.
#
# Required:
#   SOURCE       project source directory
#   WORK         scratch directory; its build/ child is the build tree, so WORK is the workspace
#   PREFIX       prefix holding the staged BESA installation
#   EXPECT       PASS, CONFIGURE_FAIL, BUILD_FAIL, or TEST_FAIL
# Optional:
#   GENERATOR    CMake generator used for the project
#   ARGS         extra configure arguments, separated by '|'
#   MATCH        regular expression the output of the failing step must match
#   CHECK        cmake -P script run after configure with -DBINARY_DIR=<build tree>
#   INSTALL      ON to install the project into WORK/install
#   CONSUMER     source directory of a downstream project built against the installed project

foreach(_required SOURCE WORK PREFIX EXPECT)
  if(NOT DEFINED ${_required})
    message(FATAL_ERROR "driver.cmake: ${_required} is required")
  endif()
endforeach()
if(NOT EXPECT MATCHES "^(PASS|CONFIGURE_FAIL|BUILD_FAIL|TEST_FAIL)$")
  message(FATAL_ERROR "driver.cmake: unknown EXPECT '${EXPECT}'")
endif()

# ARGS is split on '|'. Each -D<name>[:<type>]=<value> is written to a cache preload script passed
# with -C, so list values containing ';' reach the project intact; other arguments pass through.
file(REMOVE_RECURSE "${WORK}")
file(MAKE_DIRECTORY "${WORK}")
set(_preload "${WORK}/preload.cmake")
file(WRITE "${_preload}" "")
set(_args)
string(REPLACE ";" "\\;" _escaped "${ARGS}")
string(REPLACE "|" ";" _escaped "${_escaped}")
foreach(_arg IN LISTS _escaped)
  if(_arg MATCHES "^-D([^:=]+)(:[^=]*)?=(.*)$")
    file(APPEND "${_preload}" "set(${CMAKE_MATCH_1} [==[${CMAKE_MATCH_3}]==] CACHE STRING \"\")\n")
  elseif(NOT _arg STREQUAL "")
    list(APPEND _args "${_arg}")
  endif()
endforeach()

set(_generator)
if(GENERATOR)
  set(_generator -G "${GENERATOR}")
endif()

# Run one step. Steps before the expected failure must succeed; the expected failure itself must
# fail, match MATCH, and end the test successfully.
function(_step NAME FAILURE_KIND)
  execute_process(
    COMMAND ${ARGN}
    RESULT_VARIABLE _result
    OUTPUT_VARIABLE _output
    ERROR_VARIABLE _output
  )
  if(EXPECT STREQUAL FAILURE_KIND)
    if(_result EQUAL 0)
      message(FATAL_ERROR "${NAME} succeeded but was expected to fail:\n${_output}")
    endif()
    # Diagnostics are wrapped at arbitrary points, so match against whitespace-normalized output.
    string(REGEX REPLACE "[ \t\r\n]+" " " _flat "${_output}")
    if(DEFINED MATCH AND NOT _flat MATCHES "${MATCH}")
      message(FATAL_ERROR "${NAME} failed without matching '${MATCH}':\n${_output}")
    endif()
    message(STATUS "${NAME} failed as expected")
    set(_besa_driver_done TRUE PARENT_SCOPE)
    return()
  endif()
  if(NOT _result EQUAL 0)
    message(FATAL_ERROR "${NAME} failed:\n${_output}")
  endif()
  set(_besa_driver_done FALSE PARENT_SCOPE)
endfunction()

set(_build "${WORK}/build")
set(_project_test_include)
if(EXISTS "${SOURCE}/test.cmake")
  list(APPEND _project_test_include "-DCMAKE_PROJECT_INCLUDE=${SOURCE}/test.cmake")
endif()

_step(configure CONFIGURE_FAIL
  "${CMAKE_COMMAND}" -S "${SOURCE}" -B "${_build}" ${_generator}
  -C "${_preload}" "-DCMAKE_PREFIX_PATH=${PREFIX}" -DCMAKE_BUILD_TYPE=Debug
  ${_project_test_include} ${_args}
)
if(_besa_driver_done)
  return()
endif()

if(CHECK)
  _step(check NONE "${CMAKE_COMMAND}" "-DBINARY_DIR=${_build}" -P "${CHECK}")
endif()

_step(build BUILD_FAIL "${CMAKE_COMMAND}" --build "${_build}")
if(_besa_driver_done)
  return()
endif()

_step(test TEST_FAIL
  "${CMAKE_CTEST_COMMAND}" --test-dir "${_build}" --output-on-failure --no-tests=ignore
)
if(_besa_driver_done)
  return()
endif()

if(INSTALL)
  _step(install NONE "${CMAKE_COMMAND}" --install "${_build}" --prefix "${WORK}/install")
endif()

if(CONSUMER)
  set(_consumer "${WORK}/consumer")
  set(_consumer_preload "${WORK}/consumer-preload.cmake")
  file(WRITE "${_consumer_preload}"
    "set(CMAKE_PREFIX_PATH [==[${PREFIX};${WORK}/install]==] CACHE STRING \"\")\n"
  )
  set(_consumer_test_include)
  if(EXISTS "${CONSUMER}/test.cmake")
    list(APPEND _consumer_test_include "-DCMAKE_PROJECT_INCLUDE=${CONSUMER}/test.cmake")
  endif()
  _step(consumer-configure NONE
    "${CMAKE_COMMAND}" -S "${CONSUMER}" -B "${_consumer}/build" ${_generator}
    -C "${_consumer_preload}" -DCMAKE_BUILD_TYPE=Debug ${_consumer_test_include}
  )
  _step(consumer-build NONE "${CMAKE_COMMAND}" --build "${_consumer}/build")
  _step(consumer-test NONE
    "${CMAKE_CTEST_COMMAND}" --test-dir "${_consumer}/build" --output-on-failure
  )
endif()

if(NOT EXPECT STREQUAL "PASS")
  message(FATAL_ERROR "every step succeeded but EXPECT was ${EXPECT}")
endif()
