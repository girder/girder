# Set this variable to the minimum coverage percentage to be considered passing
set(COVERAGE_MINIMUM_PASS 80)

set(py_coverage_rc "${PROJECT_SOURCE_DIR}/tests/girder.coveragerc")

function(add_python_test case)
  set(name "Server_${case}")

  if(PYTHON_COVERAGE)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" run --append "--rcfile=${py_coverage_rc}"
              --source=girder -m unittest -v tests.cases.${case}_test
    )
  else()
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v tests.cases.${case}_test
    )
  endif()
  set_property(TEST ${name} PROPERTY RESOURCE_LOCK mongo cherrypy)

  if(PYTHON_COVERAGE)
    set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
    set_property(TEST py_coverage APPEND PROPERTY DEPENDS ${name})
  endif()
endfunction()

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

add_python_test(user)
add_python_test(folder)
