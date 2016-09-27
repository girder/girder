get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_eslint_test(${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client")
add_puglint_test(${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/templates")
