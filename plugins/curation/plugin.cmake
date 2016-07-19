add_python_test(curation PLUGIN curation)

add_python_style_test(python_static_analysis_curation
    "${PROJECT_SOURCE_DIR}/plugins/curation/server")

add_python_style_test(python_static_analysis_curation_tests
    "${PROJECT_SOURCE_DIR}/plugins/curation/plugin_tests")

add_eslint_test(curation
    "${PROJECT_SOURCE_DIR}/plugins/curation/web_client/js")

add_web_client_test(curation
    "${PROJECT_SOURCE_DIR}/plugins/curation/plugin_tests/curationSpec.js"
    PLUGIN curation)
