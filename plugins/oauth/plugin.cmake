add_python_test(oauth PLUGIN oauth)

add_python_style_test(python_static_analysis_oauth
                      "${PROJECT_SOURCE_DIR}/plugins/oauth/server")
add_python_style_test(python_static_analysis_oauth_tests
                      "${PROJECT_SOURCE_DIR}/plugins/oauth/plugin_tests")
