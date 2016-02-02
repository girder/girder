cmake_minimum_required(VERSION 2.8.6)

project(Girder NONE)

include(CTest)
enable_testing()

set(PYTHON_VERSION "2.7" CACHE STRING "Python version used for testing")

find_package(PythonInterp ${PYTHON_VERSION} REQUIRED)

option(PYTHON_STATIC_ANALYSIS "Run Python static analysis tests with flake8" ON)
option(PYTHON_COVERAGE "Run tests with coverage.py" ON)
option(PYTHON_BRANCH_COVERAGE "Use branch-level coverage instead of line-level" OFF)
option(JAVASCRIPT_STYLE_TESTS "Run Javascript style tests with jslint" ON)
option(BUILD_JAVASCRIPT_TESTS "Build Javascript tests" ON)
option(RUN_CORE_TESTS "Whether to run the core unit tests" ON)
set(TEST_PLUGINS "" CACHE STRING "List of plugins to test. Leave empty to test all plugins")

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE coverage)
endif()

if(PYTHON_STATIC_ANALYSIS)
  find_program(FLAKE8_EXECUTABLE flake8)
endif()

set(JSON_CONFIG_MERGE_SCRIPT ${PROJECT_SOURCE_DIR}/scripts/json_config_merge.js)
set(JSON_CONFIG_EXPAND_RELPATHS_SCRIPT ${PROJECT_SOURCE_DIR}/scripts/json_config_expand_relpaths.js)

if(JAVASCRIPT_STYLE_TESTS)
  find_program(NODEJS_EXECUTABLE NAMES nodejs node)
  if(NOT NODEJS_EXECUTABLE)
    message(FATAL_ERROR "'nodejs' executable couldn't be found.\n"
                        "Consider reconfiguring passing -DNODEJS_EXECUTABLE:FILEPATH=/path/to/nodejs")
  endif()
  find_program(JSHINT_EXECUTABLE jshint ${PROJECT_SOURCE_DIR}/node_modules/jshint/bin NO_DEFAULT_PATH)
  find_program(JSSTYLE_EXECUTABLE jscs ${PROJECT_SOURCE_DIR}/node_modules/jscs/bin NO_DEFAULT_PATH)
  find_program(ESLINT_EXECUTABLE eslint ${PROJECT_SOURCE_DIR}/node_modules/.bin NO_DEFAULT_PATH)
endif()

if(BUILD_TESTING)
  include(tests/PythonTests.cmake)
  include(tests/JavascriptTests.cmake)
  add_subdirectory(scripts/tests)
  add_subdirectory(tests)
endif()
