include(CMakeParseArguments)

set(py_coverage_rc "${PROJECT_BINARY_DIR}/tests/girder.coveragerc")
set(pep8_config "${PROJECT_SOURCE_DIR}/tests/pep8.cfg")
set(coverage_html_dir "${PROJECT_SOURCE_DIR}/clients/web/dev/built/py_coverage")

if(PYTHON_BRANCH_COVERAGE)
  set(_py_branch_cov True)
else()
  set(_py_branch_cov False)
endif()

configure_file(
  "${PROJECT_SOURCE_DIR}/tests/girder.coveragerc.in"
  "${py_coverage_rc}"
  @ONLY
)

function(add_python_style_test name input)
  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PEP8_EXECUTABLE}" "--config=${pep8_config}" "${input}"
  )
endfunction()

function(add_python_test case)
  set(name "server_${case}")

  set(_options NO_LOCK)
  set(_args PLUGIN)
  set(_multival_args "")
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  if(fn_PLUGIN)
    set(name "server_${fn_PLUGIN}.${case}")
    set(module plugin_tests.${case}_test)
    set(pythonpath "${PROJECT_SOURCE_DIR}/plugins/${fn_PLUGIN}")
    set(other_covg ",${PROJECT_SOURCE_DIR}/plugins/${fn_PLUGIN}/server")
  else()
    set(module tests.cases.${case}_test)
    set(pythonpath "")
    set(other_covg "")
  endif()


  if(PYTHON_COVERAGE)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" run -p --append "--rcfile=${py_coverage_rc}"
              "--source=girder${other_covg}" -m unittest -v ${module}
    )
  else()
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v ${module}
    )
  endif()

  set_property(TEST ${name} PROPERTY ENVIRONMENT "PYTHONPATH=${pythonpath}")

  if(NOT fn_NO_LOCK)
    set_property(TEST ${name} PROPERTY RESOURCE_LOCK mongo cherrypy)
  endif()

  if(PYTHON_COVERAGE)
    set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
    set_property(TEST py_coverage_combine APPEND PROPERTY DEPENDS ${name})
  endif()
endfunction()
