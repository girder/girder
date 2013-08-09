find_program(PYTHON_EXECUTABLE python)

if(BUILD_TESTING)
  add_subdirectory(test)
endif()
