cmake_minimum_required(VERSION 2.8.6)

project(Girder)

include(CTest)
enable_testing()

find_program(PYTHON_EXECUTABLE python)

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
