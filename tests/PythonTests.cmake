include(CMakeParseArguments)

set(server_port 20200)
set(py_coverage_rc "${PROJECT_BINARY_DIR}/tests/girder.coveragerc")
set(flake8_config "${PROJECT_SOURCE_DIR}/tests/flake8.cfg")
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

if(WIN32)
  set(_separator "\\;")
else()
  set(_separator ":")
endif()

function(python_tests_init)
  if(PYTHON_COVERAGE)
    add_test(
      NAME py_coverage_reset
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" erase "--rcfile=${py_coverage_rc}"
    )
    add_test(
      NAME py_coverage_combine
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" combine
    )
    add_test(
      NAME py_coverage
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" report --fail-under=${COVERAGE_MINIMUM_PASS}
    )
    add_test(
      NAME py_coverage_html
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" html -d "${coverage_html_dir}"
              "--title=Girder Coverage Report"
    )
    add_test(
      NAME py_coverage_xml
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" xml -o "${PROJECT_BINARY_DIR}/coverage.xml"
    )
    set_property(TEST py_coverage PROPERTY DEPENDS py_coverage_combine)
    set_property(TEST py_coverage_html PROPERTY DEPENDS py_coverage)
    set_property(TEST py_coverage_xml PROPERTY DEPENDS py_coverage)
  endif()
endfunction()

function(add_python_style_test name input)
  if(PYTHON_STATIC_ANALYSIS)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${FLAKE8_EXECUTABLE}" "--config=${flake8_config}" "${input}"
    )
  endif()
endfunction()

function(add_python_test case)
  set(name "server_${case}")

  set(_options BIND_SERVER)
  set(_args PLUGIN)
  set(_multival_args RESOURCE_LOCKS TIMEOUT)
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
              "--source=girder,${PROJECT_SOURCE_DIR}/clients/python/girder_client${other_covg}"
              -m unittest -v ${module}
    )
  else()
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v ${module}
    )
  endif()

  string(REPLACE "." "_" _db_name ${name})
  set_property(TEST ${name} PROPERTY ENVIRONMENT
    "PYTHONPATH=$ENV{PYTHONPATH}${_separator}${pythonpath}${_separator}${PROJECT_SOURCE_DIR}/clients/python"
    "GIRDER_TEST_DB=mongodb://localhost:27017/girder_test_${_db_name}"
    "GIRDER_TEST_ASSETSTORE=${name}"
    "GIRDER_TEST_PORT=${server_port}"
  )
  set_property(TEST ${name} PROPERTY COST 50)
  if(fn_RESOURCE_LOCKS)
    set_property(TEST ${name} PROPERTY RESOURCE_LOCK ${fn_RESOURCE_LOCKS})
  endif()
  if(fn_TIMEOUT)
    set_property(TEST ${name} PROPERTY TIMEOUT ${fn_TIMEOUT})
  endif()
  if(fn_BIND_SERVER)
    math(EXPR next_server_port "${server_port} + 1")
    set(server_port ${next_server_port} PARENT_SCOPE)
  endif()

  if(PYTHON_COVERAGE)
    set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
    set_property(TEST py_coverage_combine APPEND PROPERTY DEPENDS ${name})
  endif()
endfunction()
