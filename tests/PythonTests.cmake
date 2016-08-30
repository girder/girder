include(CMakeParseArguments)

set(server_port 20200)
set(flake8_config "${PROJECT_SOURCE_DIR}/tests/flake8.cfg")
set(coverage_html_dir "${PROJECT_SOURCE_DIR}/clients/web/dev/built/py_coverage")

if(PYTHON_BRANCH_COVERAGE)
  set(_py_branch_cov True)
else()
  set(_py_branch_cov False)
endif()

if(RUN_CORE_TESTS)
  set(_omit_python_covg "girder/external/*")
else()
  set(_omit_python_covg "girder/*,clients/python/*")
endif()

configure_file(
  "${PROJECT_SOURCE_DIR}/tests/girder.coveragerc.in"
  "${girder_py_coverage_rc}"
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
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" erase "--rcfile=${PYTHON_COVERAGE_CONFIG}"
    )
    add_test(
      NAME py_coverage_combine
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" combine
    )
    add_test(
      NAME py_coverage
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" report "--rcfile=${PYTHON_COVERAGE_CONFIG}" --fail-under=${COVERAGE_MINIMUM_PASS}
    )
    add_test(
      NAME py_coverage_html
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" html "--rcfile=${PYTHON_COVERAGE_CONFIG}" -d "${coverage_html_dir}"
              "--title=Girder Coverage Report"
    )
    add_test(
      NAME py_coverage_xml
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" xml "--rcfile=${PYTHON_COVERAGE_CONFIG}" -o "${PROJECT_BINARY_DIR}/coverage.xml"
    )
    set_property(TEST py_coverage PROPERTY DEPENDS py_coverage_combine)
    set_property(TEST py_coverage_html PROPERTY DEPENDS py_coverage)
    set_property(TEST py_coverage_xml PROPERTY DEPENDS py_coverage)

    set_property(TEST py_coverage PROPERTY LABELS girder_python)
    set_property(TEST py_coverage_reset PROPERTY LABELS girder_python)
    set_property(TEST py_coverage_combine PROPERTY LABELS girder_python)
    set_property(TEST py_coverage_html PROPERTY LABELS girder_python)
    set_property(TEST py_coverage_xml PROPERTY LABELS girder_python)
  endif()
endfunction()

function(add_python_style_test name input)
  if(PYTHON_STATIC_ANALYSIS)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${FLAKE8_EXECUTABLE}" "--config=${flake8_config}" "${input}"
    )
    set_property(TEST "${name}" PROPERTY LABELS girder_static_analysis girder_python)
  endif()
endfunction()

function(add_python_test case)
  set(name "server_${case}")

  set(_options BIND_SERVER PY2_ONLY)
  set(_args DBNAME PLUGIN SUBMODULE)
  set(_multival_args RESOURCE_LOCKS TIMEOUT EXTERNAL_DATA REQUIRED_FILES)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  if(fn_PY2_ONLY AND PYTHON_VERSION MATCHES "^3")
    message(STATUS " !!! Not adding test ${name}, cannot run in python version ${PYTHON_VERSION}.")
    return()
  endif()

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

  if(fn_SUBMODULE)
    set(module ${module}.${fn_SUBMODULE})
    set(name ${name}.${fn_SUBMODULE})
  endif()

  if(PYTHON_COVERAGE)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" run --parallel-mode "--rcfile=${PYTHON_COVERAGE_CONFIG}"
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

  if(fn_DBNAME)
    set(_db_name ${fn_DBNAME})
  else()
    set(_db_name ${name})
  endif()

  string(REPLACE "." "_" _db_name ${_db_name})
  set_property(TEST ${name} PROPERTY ENVIRONMENT
    "PYTHONPATH=$ENV{PYTHONPATH}${_separator}${pythonpath}${_separator}${PROJECT_SOURCE_DIR}/clients/python"
    "GIRDER_TEST_DB=mongodb://localhost:27017/girder_test_${_db_name}"
    "GIRDER_TEST_ASSETSTORE=${name}"
    "GIRDER_TEST_PORT=${server_port}"
    "GIRDER_TEST_DATA_PREFIX=${GIRDER_EXTERNAL_DATA_ROOT}"
    "MONGOD_EXECUTABLE=${MONGOD_EXECUTABLE}"
  )
  set_property(TEST ${name} PROPERTY COST 50)
  set_property(TEST ${name} PROPERTY REQUIRED_FILES ${fn_REQUIRED_FILES})

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

  if(fn_EXTERNAL_DATA)
    set(_data_files "")
    foreach(_data_file ${fn_EXTERNAL_DATA})
      list(APPEND _data_files "DATA{${GIRDER_EXTERNAL_DATA_BUILD_PATH}/${_data_file}}")
    endforeach()
    girder_ExternalData_expand_arguments("${name}_data" _tmp ${_data_files})
    girder_ExternalData_add_target("${name}_data")
  endif()

  set_property(TEST ${name} PROPERTY LABELS girder_python)
endfunction()
