add_python_test(google_analytics PLUGIN google_analytics)

add_python_style_test(python_static_analysis_google_analytics
                      "${PROJECT_SOURCE_DIR}/plugins/google_analytics/server")
add_python_style_test(python_static_analysis_google_analytics_tests
                      "${PROJECT_SOURCE_DIR}/plugins/google_analytics/plugin_tests")

add_eslint_test(google_analytics
                          "${PROJECT_SOURCE_DIR}/plugins/google_analytics/web_client/js/src")
