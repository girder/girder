set(web_client_port 30001)

function(javascript_tests_init)
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  if(RUN_CORE_TESTS)
    set(_core_cov_flag "--include-core")
  else()
    set(_core_cov_flag "--skip-core")
  endif()

  add_test(
    NAME js_coverage_reset
    COMMAND "${PYTHON_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tests/js_coverage_tool.py"
            reset
            "${PROJECT_BINARY_DIR}/js_coverage"
  )
  add_test(
    NAME js_coverage_combine_report
    WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
    COMMAND "${PYTHON_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tests/js_coverage_tool.py"
            "--threshold=${JS_COVERAGE_MINIMUM_PASS}"
            "--source=${PROJECT_SOURCE_DIR}"
            "${_core_cov_flag}"
            combine_report
            "${PROJECT_BINARY_DIR}/js_coverage"
  )
  set_property(TEST js_coverage_reset PROPERTY LABELS girder_browser)
  set_property(TEST js_coverage_combine_report PROPERTY LABELS girder_browser)
endfunction()

function(add_eslint_test name input)
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  if (NOT ESLINT_EXECUTABLE)
    message(FATAL_ERROR "CMake variable ESLINT_EXECUTABLE is not set. Run 'npm install' or disable BUILD_JAVASCRIPT_TESTS.")
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
    set(config_file "${PROJECT_SOURCE_DIR}/.eslintrc")
  endif()

  add_test(
    NAME "eslint_${name}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${ESLINT_EXECUTABLE}" --ignore-path "${ignore_file}" --config "${config_file}" "${input}"
  )
  set_property(TEST "eslint_${name}" PROPERTY LABELS girder_browser girder_static_analysis)
endfunction()

function(add_web_client_test case specFile)
  # test a web client using a spec file and the specRunner
  # :param case: the name of this test case
  # :param specFile: the path of the spec file to run
  # Optional parameters:
  # PLUGIN (name of plugin) : this plugin and all dependencies are loaded
  # (unless overridden with ENABLEDPLUGINS) and the test name includes the
  # plugin name
  # PLUGIN_DIRS (list of plugin dirs) : A list of directories plugins
  # should live in.
  # ASSETSTORE (assetstore type) : use the specified assetstore type when
  #     running the test.  Defaults to 'filesystem'
  # WEBSECURITY (boolean) : if false, don't use CORS validatation.  Defaults to
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
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  set(testname "web_client_${case}")

  set(_options NOCOVERAGE)
  set(_args PLUGIN ASSETSTORE WEBSECURITY BASEURL PLUGIN_DIRS TIMEOUT TEST_MODULE)
  set(_multival_args RESOURCE_LOCKS ENABLEDPLUGINS)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  if(fn_PLUGIN)
    set(testname "web_client_${fn_PLUGIN}.${case}")
    set(plugins ${fn_PLUGIN})
  else()
    set(plugins "")
  endif()

  if(fn_PLUGIN_DIRS)
    set(pluginDirs ${fn_PLUGIN_DIRS})
  else()
    set(pluginDirs "")
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
    "PLUGIN_DIRS=${pluginDirs}"
    "GIRDER_TEST_DB=mongodb://localhost:27017/girder_test_${testname}"
    "GIRDER_TEST_ASSETSTORE=${testname}"
    "GIRDER_PORT=${web_client_port}"
  )
  math(EXPR next_web_client_port "${web_client_port} + 1")
  set(web_client_port ${next_web_client_port} PARENT_SCOPE)

  if(fn_RESOURCE_LOCKS)
    set_property(TEST ${testname} PROPERTY RESOURCE_LOCK ${fn_RESOURCE_LOCKS})
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
    set_property(TEST ${testname} APPEND PROPERTY ENVIRONMENT
        "COVERAGE_FILE=${PROJECT_BINARY_DIR}/js_coverage/${case}.cvg"
    )
    set_property(TEST ${testname} APPEND PROPERTY DEPENDS js_coverage_reset)
    set_property(TEST js_coverage_combine_report APPEND PROPERTY DEPENDS ${testname})
  endif()

  set_property(TEST ${testname} PROPERTY LABELS girder_browser)
endfunction()
