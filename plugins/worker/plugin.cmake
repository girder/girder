add_python_style_test(
    python_static_analysis_worker "${PROJECT_SOURCE_DIR}/plugins/worker/server")

add_eslint_test(
    worker "${PROJECT_SOURCE_DIR}/plugins/worker/web_client/js")
