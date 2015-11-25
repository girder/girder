set(web_client_port 30001)

function(javascript_tests_init)
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
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
            combine_report
            "${PROJECT_BINARY_DIR}/js_coverage"
  )
endfunction()

include(${PROJECT_SOURCE_DIR}/scripts/JsonConfigExpandRelpaths.cmake)
include(${PROJECT_SOURCE_DIR}/scripts/JsonConfigMerge.cmake)

function(add_javascript_style_test name input)
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  set(_args JSHINT_EXTRA_CONFIGS JSSTYLE_EXTRA_CONFIGS)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  # jshint
  set(jshint_config "${PROJECT_BINARY_DIR}/tests/${name}_jshint.cfg")
  json_config_merge(
    INPUTFILES
      "${PROJECT_SOURCE_DIR}/tests/jshint.cfg"
      ${fn_JSHINT_EXTRA_CONFIGS}
    OUTPUTFILE
      ${jshint_config}
    )

  # jsstyle
  set(inputfiles
    "${PROJECT_SOURCE_DIR}/tests/jsstyle.cfg"
    ${fn_JSSTYLE_EXTRA_CONFIGS}
    )
  set(expanded_jsstyle_inputfiles)
  foreach(inputfile IN LISTS inputfiles)
    set(outputfile ${CMAKE_CURRENT_BINARY_DIR}/${inputfile})
    get_filename_component(outputdir ${outputfile} PATH)
    file(MAKE_DIRECTORY ${outputdir})
    list(APPEND expanded_jsstyle_inputfiles ${outputfile})
    json_config_expand_relpaths(
      INPUTFILE ${inputfile}
      OUTPUTFILE ${outputfile}
      RELATIVE_PATH_KEYS excludeFiles
      )
  endforeach()

  set(jsstyle_config "${PROJECT_BINARY_DIR}/tests/${name}_jsstyle.cfg")
  json_config_merge(
    INPUTFILES ${expanded_jsstyle_inputfiles}
    OUTPUTFILE ${jsstyle_config}
    )

  # add tests
  set(working_dir "${PROJECT_SOURCE_DIR}/clients/web")
  if(NOT IS_ABSOLUTE ${input})
    set(input ${working_dir}/${input})
  endif()
  if(NOT EXISTS ${input})
    message(FATAL_ERROR "Failed to add javascript style tests."
                        "Directory or file '${input}' does not exist.")
  endif()

  # check if the input is a directory or file and set the working directory
  if(IS_DIRECTORY "${input}")
    set(test_directory "${input}")
  else()
    get_filename_component(test_directory "${input}" DIRECTORY)
  endif()

  add_test(
    NAME "jshint_${name}"
    WORKING_DIRECTORY "${test_directory}"
    COMMAND "${JSHINT_EXECUTABLE}" --config "${jshint_config}" "${input}"
  )
  add_test(
    NAME "jsstyle_${name}"
    WORKING_DIRECTORY "${test_directory}"
    COMMAND "${JSSTYLE_EXECUTABLE}"  --config "${jsstyle_config}" "${input}"
  )
endfunction()

function(add_web_client_test case specFile)
  # test a web client using a spec file and the specRunner
  # :param case: the name of this test case
  # :param specFile: the path of the spec file to run
  # Optional parameters:
  # PLUGIN (name of plugin) : this plugin is loaded (unless overridden with
  #     ENABLEDPLUGINS) and the test name includes the plugin name
  # PLUGIN_DIRS (list of plugin dirs) : A list of directories plugins
  # should live in.
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
  # BASEURL (url): The base url to load for the test.
  if (NOT BUILD_JAVASCRIPT_TESTS)
    return()
  endif()

  set(testname "web_client_${case}")

  set(_options NOCOVERAGE)
  set(_args PLUGIN ASSETSTORE WEBSECURITY BASEURL PLUGIN_DIRS)
  set(_multival_args RESOURCE_LOCKS TIMEOUT ENABLEDPLUGINS)
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

  add_test(
      NAME ${testname}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v tests.web_client_test
  )

  # Catch view leaks and report them as test failures.
  set_property(TEST ${testname} PROPERTY FAIL_REGULAR_EXPRESSION
    "View created with no parentView property")

  set_property(TEST ${testname} PROPERTY ENVIRONMENT
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
  #if(fn_RESOURCE_LOCKS)
  #  set_property(TEST ${testname} PROPERTY RESOURCE_LOCK mongo cherrypy ${fn_RESOURCE_LOCKS})
  #else()
  #  set_property(TEST ${testname} PROPERTY RESOURCE_LOCK mongo cherrypy)
  #endif()
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
endfunction()
