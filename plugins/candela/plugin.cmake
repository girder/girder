get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_web_client_test(${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests/candelaSpec.js"
    PLUGIN ${PLUGIN})
add_eslint_test(
    ${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client")
add_puglint_test(${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/templates")
