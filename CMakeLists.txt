cmake_minimum_required(VERSION 2.8.6)

project(Girder)

include(CTest)
enable_testing()

find_program(PYTHON_EXECUTABLE python)

option(PYTHON_STYLE_TESTS "Run Python style tests with pep8" ON)
option(PYTHON_COVERAGE "Run tests with coverage.py" OFF)

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE coverage)
endif()

if(PYTHON_STYLE_TESTS)
  find_program(PEP8_EXECUTABLE pep8)
endif()

if(BUILD_TESTING)
  include(tests/PythonTests.cmake)
  add_subdirectory(tests)
endif()
