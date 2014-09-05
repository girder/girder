cmake_minimum_required(VERSION 2.8.6)

project(Girder)

include(CTest)
enable_testing()

find_program(PYTHON_EXECUTABLE python)

option(PYTHON_STATIC_ANALYSIS "Run Python static analysis tests with flake8" ON)
option(PYTHON_COVERAGE "Run tests with coverage.py" ON)
option(PYTHON_BRANCH_COVERAGE "Use branch-level coverage instead of line-level" OFF)
option(JAVASCRIPT_STYLE_TESTS "Run Javascript style tests with jslint" ON)

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE coverage)
endif()

if(PYTHON_STATIC_ANALYSIS)
  find_program(FLAKE8_EXECUTABLE flake8)
endif()

if(JAVASCRIPT_STYLE_TESTS)
  find_program(JSHINT_EXECUTABLE jshint ${PROJECT_SOURCE_DIR}/node_modules/jshint/bin)
  find_program(JSLINT_EXECUTABLE nodelint ${PROJECT_SOURCE_DIR}/node_modules/nodelint)
endif()

if(BUILD_TESTING)
  include(tests/PythonTests.cmake)
  include(tests/JavascriptTests.cmake)
  add_subdirectory(tests)
endif()
