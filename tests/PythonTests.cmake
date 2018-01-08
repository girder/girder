set(server_port 20200)

if(RUN_CORE_TESTS)
  set(_python_coverage_omit_extra "")
else()
  set(_python_coverage_omit_extra "--omit=girder/*,clients/python/*")
endif()

if(WIN32)
  set(_separator "\\;")
else()
  set(_separator ":")
endif()

find_program(PYTEST_EXECUTABLE NAMES pytest)

function(python_tests_init)
  add_test(
    NAME py_coverage_reset
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" erase
  )
  add_test(
    NAME py_coverage_combine
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" combine
  )
  add_test(
    NAME py_coverage
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" report
  )
  add_test(
    NAME py_coverage_html
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" html
  )
  add_test(
    NAME py_coverage_xml
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" xml
  )
  set_property(TEST py_coverage PROPERTY DEPENDS py_coverage_combine)
  set_property(TEST py_coverage_html PROPERTY DEPENDS py_coverage)
  set_property(TEST py_coverage_xml PROPERTY DEPENDS py_coverage)

  set_property(TEST py_coverage PROPERTY LABELS girder_coverage)
  set_property(TEST py_coverage_reset PROPERTY LABELS girder_python girder_integration)
  set_property(TEST py_coverage_combine PROPERTY LABELS girder_coverage)
  set_property(TEST py_coverage_html PROPERTY LABELS girder_coverage)
  set_property(TEST py_coverage_xml PROPERTY LABELS girder_coverage)
endfunction()

function(add_python_style_test name input)
  if(PYTHON_STATIC_ANALYSIS)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${FLAKE8_EXECUTABLE}" "${input}"
    )
    set_property(TEST "${name}" PROPERTY LABELS girder_python)
  endif()
endfunction()

function(add_python_test case)
  set(name "server_${case}")

  set(_options BIND_SERVER PY2_ONLY RUN_SERIAL)
  set(_args DBNAME PLUGIN SUBMODULE)
  set(_multival_args RESOURCE_LOCKS TIMEOUT EXTERNAL_DATA REQUIRED_FILES COVERAGE_PATHS
                     ENVIRONMENT SETUP_DATABASE)
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
    set(test_file "${PROJECT_SOURCE_DIR}/plugins/${fn_PLUGIN}/plugin_tests/${case}_test.py")
  else()
    set(module tests.cases.${case}_test)
    set(pythonpath "")
    set(other_covg "")
    set(test_file "${PROJECT_SOURCE_DIR}/tests/cases/${case}_test.py")
  endif()

  if(fn_COVERAGE_PATHS)
    set(other_covg "${other_covg},${fn_COVERAGE_PATHS}")
  endif()

  if(fn_SUBMODULE)
    set(module ${module}.${fn_SUBMODULE})
    set(name ${name}.${fn_SUBMODULE})
  endif()

  file(MAKE_DIRECTORY "${PROJECT_SOURCE_DIR}/build/test/coverage/python_temp")

  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" run
      ${_python_coverage_omit_extra}
      "--source=girder,${PROJECT_SOURCE_DIR}/clients/python/girder_client${other_covg}"
      -m unittest -v ${module}
  )

  if(fn_DBNAME)
    set(_db_name ${fn_DBNAME})
  else()
    set(_db_name ${name})
  endif()

  if(fn_SETUP_DATABASE)
    set(TEST_DATABASE_FILE "${fn_SETUP_DATABASE}")
  else()
    get_test_database_spec("${test_file}")
  endif()

  string(REPLACE "." "_" _db_name ${_db_name})
  set_property(TEST ${name} PROPERTY ENVIRONMENT
    "PYTHONPATH=$ENV{PYTHONPATH}${_separator}${pythonpath}${_separator}${PROJECT_SOURCE_DIR}/clients/python"
    "GIRDER_TEST_DB=mongodb://localhost:27017/girder_test_${_db_name}"
    "GIRDER_TEST_ASSETSTORE=${name}"
    "GIRDER_TEST_PORT=${server_port}"
    "GIRDER_TEST_DATA_PREFIX=${GIRDER_EXTERNAL_DATA_ROOT}"
    "MONGOD_EXECUTABLE=${MONGOD_EXECUTABLE}"
    "GIRDER_TEST_DATABASE_CONFIG=${TEST_DATABASE_FILE}"
    "${fn_ENVIRONMENT}"
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
  if(fn_RUN_SERIAL)
    set_property(TEST ${name} PROPERTY RUN_SERIAL ON)
  endif()

  set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
  set_property(TEST py_coverage_combine APPEND PROPERTY DEPENDS ${name})

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

function(add_pytest_test case)
  set(name "server_pytest_${case}")

  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTEST_EXECUTABLE}" --tb=long --cov-append
  )
  set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
  set_property(TEST py_coverage_combine APPEND PROPERTY DEPENDS ${name})
  set_property(TEST ${name} PROPERTY LABELS girder_python)
endfunction()
