add_python_test(gravatar PLUGIN gravatar)
add_python_style_test(
  python_static_analysis_gravatar
  "${PROJECT_SOURCE_DIR}/plugins/gravatar/server"
)

add_eslint_test(
    gravatar
    "${PROJECT_SOURCE_DIR}/plugins/gravatar/web_client/js"
)
