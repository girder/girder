add_standard_plugin_tests(NO_CLIENT_TESTS)

set(_pluginDir "${CMAKE_CURRENT_LIST_DIR}")
get_filename_component(_pluginName "${CMAKE_CURRENT_LIST_DIR}" NAME)

add_web_client_test(widgets "${_pluginDir}/plugin_tests/widgetsSpec.js" PLUGIN ${_pluginName})
add_web_client_test(tasks "${_pluginDir}/plugin_tests/tasksSpec.js" PLUGIN ${_pluginName}
  SETUP_MODULES "${_pluginDir}/plugin_tests/mock_worker.py")

# run this test serially to avoid event stream timeouts on CI
if (BUILD_JAVASCRIPT_TESTS)
  set_property(TEST web_client_item_tasks.tasks PROPERTY RUN_SERIAL ON)
endif()

add_eslint_test(${_pluginName}_tests "${_pluginDir}/plugin_tests/plugin_tests"
  ESLINT_CONFIG_FILE "${PROJECT_SOURCE_DIR}/clients/web/test/.eslintrc.json")

if(ANSIBLE_TESTS)
  find_program(VAGRANT_EXECUTABLE vagrant)

  add_test(NAME "${_pluginName}.vagrant_up"
    WORKING_DIRECTORY "${_pluginDir}/devops"
    COMMAND "${VAGRANT_EXECUTABLE}" "up" "--no-provision")
  set_tests_properties("${_pluginName}.vagrant_up" PROPERTIES
    RUN_SERIAL ON
    LABELS girder_ansible)

  add_test(NAME "${_pluginName}.vagrant_provision"
    WORKING_DIRECTORY "${_pluginDir}/devops"
    COMMAND ${VAGRANT_EXECUTABLE} "provision")
  set_tests_properties("${_pluginName}.vagrant_provision"
    PROPERTIES
    FAIL_REGULAR_EXPRESSION "VM not created."
    RUN_SERIAL ON
    DEPENDS "${_pluginName}.vagrant_up"
    LABELS girder_ansible)

  add_test(NAME "${_pluginName}.vagrant_destroy"
    WORKING_DIRECTORY "${_pluginDir}/devops"
    COMMAND "${VAGRANT_EXECUTABLE}" "destroy" "-f")
  set_tests_properties("${_pluginName}.vagrant_destroy" PROPERTIES
    DEPENDS "${_pluginName}.vagrant_up;${_pluginName}.vagrant_provision"
    RUN_SERIAL ON
    FAIL_REGULAR_EXPRESSION "Host file not found;no hosts matched"
    LABELS girder_ansible)
endif()
