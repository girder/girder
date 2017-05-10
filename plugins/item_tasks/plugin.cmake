get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_python_test(tasks PLUGIN ${PLUGIN})

add_python_style_test(python_static_analysis_${PLUGIN}
                      "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/server")
add_python_style_test(python_static_analysis_${PLUGIN}_tests
                      "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests")

add_web_client_test(
    widgets "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests/widget.js" PLUGIN ${PLUGIN})
add_web_client_test(
    tasks "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests/tasks.js" PLUGIN ${PLUGIN}
    SETUP_MODULES "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/mock_worker.py")

add_eslint_test(${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client")
add_puglint_test(${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/templates")


if(ANSIBLE_TESTS)
  find_program(VAGRANT_EXECUTABLE vagrant)

  add_test(NAME "${PLUGIN}.vagrant_up"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/devops"
    COMMAND "${VAGRANT_EXECUTABLE}" "up" "--no-provision")
  set_tests_properties("${PLUGIN}.vagrant_up" PROPERTIES
    RUN_SERIAL ON
    LABELS girder_ansible)

  add_test(NAME "${PLUGIN}.vagrant_provision"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/devops"
    COMMAND ${VAGRANT_EXECUTABLE} "provision")
  set_tests_properties("${PLUGIN}.vagrant_provision"
    PROPERTIES
    FAIL_REGULAR_EXPRESSION "VM not created."
    RUN_SERIAL ON
    DEPENDS "${PLUGIN}.vagrant_up"
    LABELS girder_ansible)

  add_test(NAME "${PLUGIN}.vagrant_destroy"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/devops"
    COMMAND "${VAGRANT_EXECUTABLE}" "destroy" "-f")
  set_tests_properties("${PLUGIN}.vagrant_destroy" PROPERTIES
    DEPENDS "${PLUGIN}.vagrant_up;${PLUGIN}.vagrant_provision"
    RUN_SERIAL ON
    FAIL_REGULAR_EXPRESSION "Host file not found;no hosts matched"
    LABELS girder_ansible)
endif()
