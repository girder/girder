add_python_test(auto_join PLUGIN auto_join)

add_python_style_test(
    python_static_analysis_auto_join
    "${PROJECT_SOURCE_DIR}/plugins/auto_join/server")

add_python_style_test(
    python_static_analysis_auto_join_tests
    "${PROJECT_SOURCE_DIR}/plugins/auto_join/plugin_tests")

# add_web_client_test(
#     auto_join
#     "${PROJECT_SOURCE_DIR}/plugins/auto_join/plugin_tests/autoJoinSpec.js"
#     PLUGIN auto_join)
