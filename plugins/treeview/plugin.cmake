get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_web_client_test(
    types "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests/types.js" PLUGIN ${PLUGIN})

add_eslint_test(${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client")
add_eslint_test(${PLUGIN}-tests "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests")
add_puglint_test(${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/templates")
