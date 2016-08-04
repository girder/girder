add_python_test(thumbnail PLUGIN thumbnails)
add_python_test(thumbnail_py2 PLUGIN thumbnails PY2_ONLY)
add_python_style_test(python_static_analysis_thumbnails
                      "${PROJECT_SOURCE_DIR}/plugins/thumbnails/server")
add_python_style_test(python_static_analysis_thumbnails_tests
                      "${PROJECT_SOURCE_DIR}/plugins/thumbnails/plugin_tests")

add_web_client_test(thumbnails
    "${PROJECT_SOURCE_DIR}/plugins/thumbnails/plugin_tests/thumbnailsSpec.js"
    PLUGIN thumbnails)
add_eslint_test(
    thumbnails "${PROJECT_SOURCE_DIR}/plugins/thumbnails/web_client/js"
    ESLINT_CONFIG_FILE "${PROJECT_SOURCE_DIR}/plugins/thumbnails/web_client/.eslintrc")
