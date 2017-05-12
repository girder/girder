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

if (BUILD_JAVASCRIPT_TESTS)
    set_property(TEST web_client_item_tasks.tasks PROPERTY RUN_SERIAL ON)
endif()

add_eslint_test(${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client")
add_eslint_test(${PLUGIN}-tests "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests")
add_puglint_test(${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/templates")
