set(CTEST_SOURCE_DIRECTORY "$ENV{HOME}/girder")
set(CTEST_BINARY_DIRECTORY "$ENV{HOME}/_build")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)
if($ENV{CIRCLE_NODE_INDEX} LESS "0")
  set(test_group "python")
elseif($ENV{CIRCLE_NODE_INDEX} EQUAL "2")
  set(test_group "browser")
endif()

set(CTEST_SITE "CircleCI")
set(CTEST_BUILD_NAME "Linux-$ENV{CIRCLE_BRANCH}-Mongo-$ENV{MONGO_VERSION}-${test_group}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")
set(cfg_options
  -DPYTHON_COVERAGE=ON
  -DPYTHON_VERSION=$ENV{PYTHON_VERSION}
  -DPYTHON_COVERAGE_EXECUTABLE=$ENV{COVERAGE_EXECUTABLE}
  -DVIRTUALENV_EXECUTABLE=$ENV{VIRTUALENV_EXECUTABLE}
  -DFLAKE8_EXECUTABLE=$ENV{FLAKE8_EXECUTABLE}
  -DPYTHON_EXECUTABLE=$ENV{PYTHON_EXECUTABLE}
)

ctest_start("Continuous")
ctest_configure(OPTIONS "${cfg_options}")
ctest_build()

if(test_group STREQUAL python)
  ctest_test(
    PARALLEL_LEVEL 16 RETURN_VALUE res
    INCLUDE_LABEL girder_python
  )
elseif(test_group STREQUAL browser)
  ctest_test(
    PARALLEL_LEVEL 16 RETURN_VALUE res
    EXCLUDE_LABEL girder_python
  )
  file(RENAME "${CTEST_BINARY_DIRECTORY}/coverage/js_coverage.xml" "${CTEST_BINARY_DIRECTORY}/coverage.xml")
endif()

ctest_coverage()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_submit()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/test_failed")
if(NOT res EQUAL 0)
  file(WRITE "${CTEST_BINARY_DIRECTORY}/test_failed" "error")
  message(FATAL_ERROR "Test failures occurred.")
endif()
