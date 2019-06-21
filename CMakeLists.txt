cmake_minimum_required(VERSION 2.8.6)

project(Girder NONE)

# Address warning with Ninja generator and ExternalData
if(POLICY CMP0058)
  cmake_policy(SET CMP0058 NEW)
endif()

include(CTest)
include(CMakeParseArguments)

set(PYTHON_VERSION "2.7" CACHE STRING "Python version used for testing")

find_package(PythonInterp ${PYTHON_VERSION} REQUIRED)

option(BUILD_JAVASCRIPT_TESTS "Build Javascript tests" ON)
option(RUN_CORE_TESTS "Whether to run the core tests" ON)
set(TEST_PLUGINS "" CACHE STRING "List of plugins to test. Leave empty to test all plugins")

find_program(PYTHON_COVERAGE_EXECUTABLE NAMES coverage python-coverage)

if(BUILD_TESTING)
  include(tests/TestData.cmake)
  include(tests/TestCommon.cmake)
  include(tests/PythonTests.cmake)
  include(tests/JavascriptTests.cmake)
  add_subdirectory(tests)
endif()
