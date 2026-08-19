# Smoke tests validate the environment before more expensive tests are trusted.  Sanitizer smoke
# tests intentionally trigger their sanitizer so a misconfigured instrumentation runtime is caught.

besa_add_executable(
  NAME smoke.thread.t
  INSTALL FALSE
  SOURCES thread.t.cpp
  LINK_LIBRARIES vorlage.test.runtime Threads::Threads
)
add_test(NAME smoke.thread.t COMMAND $<TARGET_FILE:smoke.thread.t>)
set_property(TEST smoke.thread.t PROPERTY LABELS "smoke;production")

if(PROJECT_DEVTOOLS_ASAN)
  besa_add_executable(NAME smoke.asan.t INSTALL FALSE SOURCES asan.t.cpp)
  add_test(
    NAME smoke.asan.t
    COMMAND "${CMAKE_COMMAND}" -E env
      ASAN_OPTIONS=abort_on_error=0:halt_on_error=0:exitcode=0
      $<TARGET_FILE:smoke.asan.t>
  )
  set_tests_properties(smoke.asan.t PROPERTIES PASS_REGULAR_EXPRESSION "AddressSanitizer")
  set_property(TEST smoke.asan.t PROPERTY LABELS "smoke;production;sanitizer;asan")
endif()

if(PROJECT_DEVTOOLS_LSAN)
  besa_add_executable(NAME smoke.lsan.t INSTALL FALSE SOURCES lsan.t.cpp)
  add_test(NAME smoke.lsan.t COMMAND $<TARGET_FILE:smoke.lsan.t>)
  set_tests_properties(smoke.lsan.t PROPERTIES WILL_FAIL TRUE)
  set_property(TEST smoke.lsan.t PROPERTY LABELS "smoke;production;sanitizer;lsan")
endif()

if(PROJECT_DEVTOOLS_UBSAN)
  besa_add_executable(NAME smoke.ubsan.t INSTALL FALSE SOURCES ubsan.t.cpp)
  add_test(NAME smoke.ubsan.t COMMAND $<TARGET_FILE:smoke.ubsan.t>)
  set_tests_properties(smoke.ubsan.t PROPERTIES WILL_FAIL TRUE)
  set_property(TEST smoke.ubsan.t PROPERTY LABELS "smoke;production;sanitizer;ubsan")
endif()
