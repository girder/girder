set(CTEST_SOURCE_DIRECTORY "$ENV{CIRCLE_WORKING_DIRECTORY}/girder")
set(CTEST_BINARY_DIRECTORY "$ENV{CIRCLE_WORKING_DIRECTORY}/girder_build")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)

set(test_group $ENV{TEST_GROUP})
set(branch $ENV{CIRCLE_BRANCH})
set(CTEST_SITE "CircleCI")
set(CTEST_BUILD_NAME "Linux-${branch}-$ENV{PYTHON_VERSION}-${test_group}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")

if(test_group STREQUAL python)
  set(cfg_options
    -DPYTHON_VERSION=$ENV{PYTHON_VERSION}
    -DPYTHON_EXECUTABLE=$ENV{PYTHON_EXECUTABLE}
    -DVIRTUALENV_EXECUTABLE=$ENV{VIRTUALENV_EXECUTABLE}
    -DPYTHON_COVERAGE=ON
    -DPYTHON_STATIC_ANALYSIS=ON
    -DBUILD_JAVASCRIPT_TESTS=OFF
    -DJAVASCRIPT_STYLE_TESTS=OFF
  )

  set(_test_labels "girder_python")
elseif(test_group STREQUAL browser)
  set(cfg_options
    -DPYTHON_VERSION=$ENV{PYTHON_VERSION}
    -DPYTHON_EXECUTABLE=$ENV{PYTHON_EXECUTABLE}
    -DPYTHON_COVERAGE=OFF
    -DPYTHON_STATIC_ANALYSIS=OFF
    -DBUILD_JAVASCRIPT_TESTS=ON
    -DJAVASCRIPT_STYLE_TESTS=ON
  )

  set(_test_labels "girder_browser")
  # # Only run the packaging tests on master branch, or a release branch
  # if(branch STREQUAL "master" OR branch MATCHES "^v[0-9]+\\.[0-9]+\\.[0-9]+")
  #   set(_test_labels "${_test_labels}|girder_package")
  # endif()
  # Always run the packaging tests
  set(_test_labels "${_test_labels}|girder_package")
elseif(test_group STREQUAL coverage)
  set(cfg_options
    -DPYTHON_VERSION=$ENV{PYTHON_VERSION}
    -DPYTHON_EXECUTABLE=$ENV{PYTHON_EXECUTABLE}
    -DVIRTUALENV_EXECUTABLE=$ENV{VIRTUALENV_EXECUTABLE}
    -DPYTHON_COVERAGE=ON
    -DBUILD_JAVASCRIPT_TESTS=$ENV{BUILD_JAVASCRIPT_TESTS}
  )
  set(_test_labels "coverage")
endif()

ctest_start("Continuous")
ctest_configure(OPTIONS "${cfg_options}")
ctest_build()
ctest_test(
  PARALLEL_LEVEL 4 RETURN_VALUE res
  INCLUDE_LABEL "${_test_labels}"
)
if(test_group STREQUAL coverage)
  ctest_submit()
endif()

if(NOT res EQUAL 0)
  file(WRITE "${CTEST_BINARY_DIRECTORY}/test_failed" "error")
  message(FATAL_ERROR "Test failures occurred.")
endif()
