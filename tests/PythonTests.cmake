set(py_coverage_rc "${PROJECT_SOURCE_DIR}/tests/girder.coveragerc")
set(pep8_config "${PROJECT_SOURCE_DIR}/tests/pep8.cfg")

function(add_python_style_test name input)
  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PEP8_EXECUTABLE}" "--config=${pep8_config}" "${input}"
  )
endfunction()

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
