set(web_client_port 50001)

function(javascript_tests_init)
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
            combine_report
            "${PROJECT_BINARY_DIR}/js_coverage"
  )
endfunction()

function(add_javascript_style_test name input)
  add_test(
    NAME "jshint_${name}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/clients/web"
    COMMAND "${JSHINT_EXECUTABLE}" --config "${PROJECT_SOURCE_DIR}/tests/jshint.cfg" "${input}"
  )
  add_test(
    NAME "jsstyle_${name}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/clients/web"
    COMMAND "${JSSTYLE_EXECUTABLE}" --config "${PROJECT_SOURCE_DIR}/tests/jsstyle.cfg" "${input}"
  )
endfunction()

function(add_web_client_test case specFile)
  # test a web client using a spec file and the specRunner
  # :param case: the nane of this test case
  # :param specFile: the path of the spec file to run
  # Optional parameters:
  # PLUGIN (name of plugin) : this plugin is loaded (unless overridden with
  #     ENABLEDPLUGINS) and the test name includes the plugin name
  # ASSETSTORE (assetstore type) : use the specified assetstore type when
  #     running the test.  Defaults to 'filesystem'
  # WEBSECURITY (boolean) : if false, don't use CORS validatation.  Defaults to
  #     'true'
  # ENABLEDPLUGINS (list of plugins): A list of plugins to load.  If PLUGIN is
  #     specified, this overrides loading that plugin, so it probably should be
  #     included in this list, too.
  # RESOURCE_LOCKS (list of resources): A list of resources that this test
  #     needs exclusive access to.  Defaults to mongo and cherrypy.
  # TIMEOUT (seconds): An overall test timeout.
  set(testname "web_client_${case}")

  set(_args PLUGIN ASSETSTORE WEBSECURITY)
  set(_multival_args RESOURCE_LOCKS TIMEOUT ENABLEDPLUGINS)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  if(fn_PLUGIN)
    set(testname "web_client_${fn_PLUGIN}.${case}")
    set(plugins ${fn_PLUGIN})
  else()
    set(plugins '')
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
    set(plugins ${fn_ENABLEDPLIGINS})
  endif()

  add_test(
      NAME ${testname}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v tests.web_client_test
  )

  set_property(TEST ${testname} PROPERTY ENVIRONMENT
    "SPEC_FILE=${specFile}"
    "ASSETSTORE_TYPE=${assetstoreType}"
    "WEB_SECURITY=${webSecurity}"
    "ENABLED_PLUGINS=${plugins}"
    "COVERAGE_FILE=${PROJECT_BINARY_DIR}/js_coverage/${case}.cvg"
    "GIRDER_TEST_DB=mongodb://localhost:27017/girder_test_${testname}"
    "GIRDER_TEST_ASSETSTORE=webclient_${testname}"
    "GIRDER_PORT=${web_client_port}"
  )
  math(EXPR next_web_client_port "${web_client_port} + 1")
  set(web_client_port ${next_web_client_port} PARENT_SCOPE)

  if(fn_RESOURCE_LOCKS)
    set_property(TEST ${testname} PROPERTY RESOURCE_LOCK ${fn_RESOURCE_LOCKS})
  endif()
  #if(fn_RESOURCE_LOCKS)
  #  set_property(TEST ${testname} PROPERTY RESOURCE_LOCK mongo cherrypy ${fn_RESOURCE_LOCKS})
  #else()
  #  set_property(TEST ${testname} PROPERTY RESOURCE_LOCK mongo cherrypy)
  #endif()
  if(fn_TIMEOUT)
    set_property(TEST ${testname} PROPERTY TIMEOUT ${fn_TIMEOUT})
  endif()

  set_property(TEST ${testname} APPEND PROPERTY DEPENDS js_coverage_reset)
  set_property(TEST js_coverage_combine_report APPEND PROPERTY DEPENDS ${testname})
endfunction()
