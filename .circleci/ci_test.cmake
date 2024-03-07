set(CTEST_SOURCE_DIRECTORY "$ENV{CIRCLE_WORKING_DIRECTORY}/girder")
set(CTEST_BINARY_DIRECTORY "$ENV{CIRCLE_WORKING_DIRECTORY}/girder_build")

set(test_group $ENV{TEST_GROUP})
set(branch $ENV{CIRCLE_BRANCH})
set(CTEST_PROJECT_NAME "girder")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")

if(test_group STREQUAL python)
  set(cfg_options
    -DPYTHON_VERSION=$ENV{PYTHON_VERSION}
    -DPYTHON_EXECUTABLE=$ENV{PYTHON_EXECUTABLE}
  )

  set(_test_labels "girder_python")
endif()

ctest_start("Continuous")
ctest_configure(OPTIONS "${cfg_options}")
ctest_build()
ctest_test(
  PARALLEL_LEVEL 4 RETURN_VALUE res
  INCLUDE_LABEL "${_test_labels}"
)

if(NOT res EQUAL 0)
  file(WRITE "${CTEST_BINARY_DIRECTORY}/test_failed" "error")
  message(FATAL_ERROR "Test failures occurred.")
endif()
