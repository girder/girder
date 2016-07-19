add_python_test(autojoin PLUGIN autojoin)

add_python_style_test(
    python_static_analysis_autojoin
    "${PROJECT_SOURCE_DIR}/plugins/autojoin/server")

add_python_style_test(
    python_static_analysis_autojoin_tests
    "${PROJECT_SOURCE_DIR}/plugins/autojoin/plugin_tests")

add_web_client_test(
    autojoin
    "${PROJECT_SOURCE_DIR}/plugins/autojoin/plugin_tests/autojoinSpec.js"
    PLUGIN autojoin)
