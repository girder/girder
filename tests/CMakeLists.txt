# Set this variable to the minimum coverage percentage to be considered passing
set(COVERAGE_MINIMUM_PASS 80)

if(PYTHON_COVERAGE)
  add_test(
    NAME py_coverage_reset
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" erase "--rcfile=${py_coverage_rc}"
  )
  add_test(
    NAME py_coverage
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" report --fail-under=${COVERAGE_MINIMUM_PASS}
  )
  add_test(
    NAME py_coverage_html
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" html -d "${PROJECT_BINARY_DIR}/python_coverage"
  )
  set_property(TEST py_coverage_html PROPERTY DEPENDS py_coverage)
endif()

if(PYTHON_STYLE_TESTS)
  add_python_style_test(pep8_style_core "${PROJECT_SOURCE_DIR}/girder")
  add_python_style_test(pep8_style_core_tests "${PROJECT_SOURCE_DIR}/tests")
endif()

add_python_test(collection)
add_python_test(file)
add_python_test(folder)
add_python_test(group)
add_python_test(item)
add_python_test(search)
add_python_test(user)

add_subdirectory(clients)
