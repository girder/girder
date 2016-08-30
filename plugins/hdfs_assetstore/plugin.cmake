get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_python_test(assetstore PLUGIN ${PLUGIN} PY2_ONLY)

add_python_style_test(
  python_static_analysis_${PLUGIN}
  "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/server"
)
add_python_style_test(
  python_static_analysis_${PLUGIN}_tests
  "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests"
)

add_eslint_test(
  ${PLUGIN}
  "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/js"
)
