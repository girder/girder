set(web_client_port 30001)

function(javascript_tests_init)
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  add_test(
    NAME js_coverage_reset
    COMMAND ${CMAKE_COMMAND} -E remove_directory "${PROJECT_SOURCE_DIR}/build/test/coverage/server_html"
  )
  add_test(
    NAME js_coverage_combine_report
    WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
    COMMAND "${ISTANBUL_EXECUTABLE}"
            "report"
            "--config" "${PROJECT_SOURCE_DIR}/.istanbul.yml"
            "--root" "${PROJECT_SOURCE_DIR}/build/test/coverage/web_temp"
            "--include" "coverage*.json"
            "--dir" "${PROJECT_SOURCE_DIR}/build/test/coverage/web"
            "text-summary" "lcovonly" "cobertura" "html"
  )
  set_property(TEST js_coverage_reset PROPERTY LABELS girder_browser girder_integration)
  set_property(TEST js_coverage_combine_report PROPERTY LABELS girder_coverage)
endfunction()

function(add_eslint_test name input)
  if (NOT JAVASCRIPT_STYLE_TESTS)
    return()
  endif()

  if (NOT ESLINT_EXECUTABLE)
    message(FATAL_ERROR "CMake variable ESLINT_EXECUTABLE is not set. Run 'girder-install web --dev' or disable JAVASCRIPT_STYLE_TESTS.")
  endif()

  set(_args ESLINT_IGNORE_FILE ESLINT_CONFIG_FILE)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  if(fn_ESLINT_IGNORE_FILE)
    set(ignore_file "${fn_ESLINT_IGNORE_FILE}")
  else()
    set(ignore_file "${PROJECT_SOURCE_DIR}/.eslintignore")
  endif()

  if(fn_ESLINT_CONFIG_FILE)
    set(config_file "${fn_ESLINT_CONFIG_FILE}")
  else()
    set(config_file "${PROJECT_SOURCE_DIR}/.eslintrc.json")
  endif()

  add_test(
    NAME "eslint_${name}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${ESLINT_EXECUTABLE}" --ignore-path "${ignore_file}" --config "${config_file}" "${input}"
  )
  set_property(TEST "eslint_${name}" PROPERTY LABELS girder_browser)
endfunction()

function(add_puglint_test name path)
  if (NOT JAVASCRIPT_STYLE_TESTS)
    return()
  endif()

  if (NOT PUGLINT_EXECUTABLE)
    message(FATAL_ERROR "CMake variable PUGLINT_EXECUTABLE is not set. Run 'girder-install web --dev' or disable JAVASCRIPT_STYLE_TESTS.")
  endif()

  add_test(
    NAME "puglint_${name}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PUGLINT_EXECUTABLE}" -c "${PROJECT_SOURCE_DIR}/.pug-lintrc" "${path}"
  )
  set_property(TEST "puglint_${name}" PROPERTY LABELS girder_browser)
endfunction()

function(add_stylint_test name path)
  if (NOT JAVASCRIPT_STYLE_TESTS)
    return()
  endif()

  if (NOT STYLINT_EXECUTABLE)
    message(FATAL_ERROR "CMake variable STYLINT_EXECUTABLE is not set. Run 'girder-install web --dev' or disable JAVASCRIPT_STYLE_TESTS.")
  endif()

  add_test(
    NAME "stylint_${name}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${STYLINT_EXECUTABLE}" --config "${PROJECT_SOURCE_DIR}/.stylintrc" "${path}"
  )
  set_property(TEST "stylint_${name}" PROPERTY LABELS girder_browser)
endfunction()

function(add_web_client_test case specFile)
  # test a web client using a spec file and the specRunner
  # :param case: the name of this test case
  # :param specFile: the path of the spec file to run
  # Optional parameters:
  # PLUGIN (name of plugin) : this plugin and all dependencies are loaded
  # (unless overridden with ENABLEDPLUGINS) and the test name includes the
  # plugin name
  # PLUGIN_DIR Alternate directory in which to look for plugins.
  # ASSETSTORE (assetstore type) : use the specified assetstore type when
  #     running the test.  Defaults to 'filesystem'
  # WEBSECURITY (boolean) : if false, don't use CORS validation.  Defaults to
  #     'true'
  # ENABLEDPLUGINS (list of plugins): A list of plugins to load. This overrides the
  # PLUGIN parameter, so if you intend to load PLUGIN it must be included in this
  # list. All dependencies of ENABLEDPLUGINS are also loaded.
  # RESOURCE_LOCKS (list of resources): A list of resources that this test
  #     needs exclusive access to.  Defaults to mongo and cherrypy.
  # TIMEOUT (seconds): An overall test timeout.
  # BASEURL (url): The base url to load for the test.
  # TEST_MODULE (python module path): Run this module rather than the default
  #     "tests.web_client_test"
  # SETUP_MODULES: colon-separated list of python scripts to import at test setup time
  #     for side effects such as mocking, adding API routes, etc.
  # SETUP_DATABASE: An absolute path to a database initialization spec
  # REQUIRED_FILES: A list of files required to run the test.
  # ENVIRONMENT: A list of key=value pairs to add to the test's runtime environment
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  set(testname "web_client_${case}")

  set(_options NOCOVERAGE)
  set(_args PLUGIN ASSETSTORE WEBSECURITY BASEURL PLUGIN_DIR TIMEOUT TEST_MODULE REQUIRED_FILES
            SETUP_MODULES ENVIRONMENT EXTERNAL_DATA SETUP_DATABASE)
  set(_multival_args RESOURCE_LOCKS ENABLEDPLUGINS)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  if(fn_PLUGIN)
    set(testname "web_client_${fn_PLUGIN}.${case}")
    set(plugins ${fn_PLUGIN})
  else()
    set(plugins "")
  endif()

  if(fn_PLUGIN_DIR)
    set(pluginDir ${fn_PLUGIN_DIR})
  else()
    set(pluginDir "")
  endif()

  if(fn_ASSETSTORE)
    set(assetstoreType ${fn_ASSETSTORE})
  else()
    set(assetstoreType "filesystem")
  endif()

  if(DEFINED fn_WEBSECURITY)
    set(webSecurity ${fn_WEBSECURITY})
  else()
    set(webSecurity true)
  endif()

  if(fn_ENABLEDPLUGINS)
    list(APPEND plugins ${fn_ENABLEDPLUGINS})
  endif()

  if(fn_TEST_MODULE)
    set(test_module ${fn_TEST_MODULE})
  else()
    set(test_module "tests.web_client_test")
  endif()

  if(fn_EXTERNAL_DATA)
    set(_data_files "")
    foreach(_data_file ${fn_EXTERNAL_DATA})
      list(APPEND _data_files "DATA{${GIRDER_EXTERNAL_DATA_BUILD_PATH}/${_data_file}}")
    endforeach()
    girder_ExternalData_expand_arguments("${testname}_data" _tmp ${_data_files})
    girder_ExternalData_add_target("${testname}_data")
  endif()

  if(fn_SETUP_DATABASE)
    set(TEST_DATABASE_FILE "${fn_SETUP_DATABASE}")
  else()
    get_test_database_spec("${specFile}")
  endif()

  add_test(
    NAME ${testname}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v "${test_module}"
  )

  # Catch view leaks and report them as test failures.
  set_property(TEST ${testname} PROPERTY FAIL_REGULAR_EXPRESSION
    "View created with no parentView property")

  # Treat plugins as a space separated string for the environment variable
  # to be set properly
  string(REPLACE ";" " " plugins "${plugins}")

  set_property(TEST ${testname} PROPERTY ENVIRONMENT
    "PYTHONPATH=$ENV{PYTHONPATH}"
    "SPEC_FILE=${specFile}"
    "ASSETSTORE_TYPE=${assetstoreType}"
    "WEB_SECURITY=${webSecurity}"
    "ENABLED_PLUGINS=${plugins}"
    "PLUGIN_DIR=${pluginDir}"
    "GIRDER_TEST_DB=mongodb://localhost:27017/girder_test_${testname}"
    "GIRDER_TEST_ASSETSTORE=${testname}"
    "GIRDER_PORT=${web_client_port}"
    "MONGOD_EXECUTABLE=${MONGOD_EXECUTABLE}"
    "GIRDER_TEST_DATA_PREFIX=${GIRDER_EXTERNAL_DATA_ROOT}"
    "GIRDER_TEST_DATABASE_CONFIG=${TEST_DATABASE_FILE}"
    "${fn_ENVIRONMENT}"
  )
  math(EXPR next_web_client_port "${web_client_port} + 1")
  set(web_client_port ${next_web_client_port} PARENT_SCOPE)
  set_property(TEST ${testname} PROPERTY REQUIRED_FILES "${fn_REQUIRED_FILES}")

  if(fn_RESOURCE_LOCKS)
    set_property(TEST ${testname} PROPERTY RESOURCE_LOCK ${fn_RESOURCE_LOCKS})
  endif()

  if(fn_SETUP_MODULES)
    set_property(TEST ${testname} APPEND PROPERTY ENVIRONMENT
      "SETUP_MODULES=${fn_SETUP_MODULES}"
    )
  endif()

  if(fn_TIMEOUT)
    set_property(TEST ${testname} PROPERTY TIMEOUT ${fn_TIMEOUT})
  endif()

  if(fn_BASEURL)
    set_property(TEST ${testname} APPEND PROPERTY ENVIRONMENT
      "BASEURL=${fn_BASEURL}"
    )
  endif()

  if (NOT fn_NOCOVERAGE)
    set_property(TEST ${testname} APPEND PROPERTY DEPENDS js_coverage_reset)
    set_property(TEST js_coverage_combine_report APPEND PROPERTY DEPENDS ${testname})
  endif()

  set_property(TEST ${testname} PROPERTY LABELS girder_browser)
endfunction()
