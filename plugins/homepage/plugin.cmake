add_python_test(homepage PLUGIN homepage)

add_python_style_test(python_static_analysis_homepage
    "${PROJECT_SOURCE_DIR}/plugins/homepage/server")

add_python_style_test(python_static_analysis_homepage_tests
    "${PROJECT_SOURCE_DIR}/plugins/homepage/plugin_tests")

add_eslint_test(homepage
    "${PROJECT_SOURCE_DIR}/plugins/homepage/web_client/js/src")
