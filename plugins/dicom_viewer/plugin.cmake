add_python_test(dicom_viewer PLUGIN dicom_viewer)

add_python_style_test(python_static_analysis_dicom_viewer
    "${PROJECT_SOURCE_DIR}/plugins/dicom_viewer/server")

# add_python_style_test(python_static_analysis_dicom_viewer_tests
#     "${PROJECT_SOURCE_DIR}/plugins/dicom_viewer/plugin_tests")

add_eslint_test(dicom_viewer
    "${PROJECT_SOURCE_DIR}/plugins/dicom_viewer/web_external/js")

# add_web_client_test(dicom_viewer
#     "${PROJECT_SOURCE_DIR}/plugins/dicom_viewer/plugin_tests/dicomViewerSpec.js"
#     PLUGIN dicom_viewer)
