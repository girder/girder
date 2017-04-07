set(CTEST_SOURCE_DIRECTORY "$ENV{HOME}/girder")
set(CTEST_BINARY_DIRECTORY "$ENV{HOME}/build")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)

set(test_group $ENV{TEST_GROUP})
set(branch $ENV{CIRCLE_BRANCH})
set(CTEST_SITE "CircleCI")
set(CTEST_BUILD_NAME "Linux-${branch}-$ENV{PYTHON_VERSION}-${test_group}")
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

# Only run the packaging tests on master branch, or a release branch
if(branch STREQUAL "master" OR branch MATCHES "^v[0-9]+\\.[0-9]+\\.[0-9]+")
  set(_label "girder_python|girder_package")
else()
  set(_label "girder_python")
endif()

if(test_group STREQUAL python)
  ctest_test(
    PARALLEL_LEVEL 4 RETURN_VALUE res
    INCLUDE_LABEL "${_label}"
  )
elseif(test_group STREQUAL browser)
  ctest_test(
    PARALLEL_LEVEL 4 RETURN_VALUE res
    EXCLUDE_LABEL "girder_python|girder_package"
  )
  file(RENAME "${CTEST_BINARY_DIRECTORY}/coverage/js_coverage.xml" "${CTEST_BINARY_DIRECTORY}/coverage.xml")
endif()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_submit()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/test_failed")
if(NOT res EQUAL 0)
  file(WRITE "${CTEST_BINARY_DIRECTORY}/test_failed" "error")
  message(FATAL_ERROR "Test failures occurred.")
endif()
