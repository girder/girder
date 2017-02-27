get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_python_test(${PLUGIN} PLUGIN ${PLUGIN})

add_python_style_test(python_static_analysis_dicom_viewer
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/server")

add_python_style_test(python_static_analysis_dicom_viewer_tests
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests")

add_eslint_test(${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_external/js")

add_puglint_test(${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/templates")
