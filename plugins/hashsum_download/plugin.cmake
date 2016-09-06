get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_web_client_test(hashsum_download
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests/hashsumSpec.js"
    PLUGIN ${PLUGIN})

add_eslint_test(
    ${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/js")

add_python_test(
  hashsum_download
  PLUGIN ${PLUGIN}
)

add_python_style_test(
  python_static_analysis_${PLUGIN}
  "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/server"
)
add_python_style_test(
  python_static_analysis_${PLUGIN}_tests
  "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests"
)
