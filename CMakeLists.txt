cmake_minimum_required(VERSION 2.8.6)

project(Girder)

include(CTest)
enable_testing()

find_program(PYTHON_EXECUTABLE python)

option(PYTHON_COVERAGE "Run tests with coverage.py" OFF)

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE coverage)
endif()

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
