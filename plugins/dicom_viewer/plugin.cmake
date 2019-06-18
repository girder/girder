add_standard_plugin_tests(PACKAGE "girder_dicom_viewer" NO_SERVER_TESTS)

add_python_test(dicom_viewer
  PLUGIN dicom_viewer
  EXTERNAL_DATA
  plugins/dicom_viewer/000000.dcm
  plugins/dicom_viewer/000001.dcm
  plugins/dicom_viewer/000002.dcm
  plugins/dicom_viewer/000003.dcm
)

get_filename_component(_pluginName "${CMAKE_CURRENT_LIST_DIR}" NAME)

add_eslint_test(${_pluginName}_webpack "${_pluginDir}/girder_dicom_viewer/webpack.helper.js")
add_python_style_test(python_static_anaysis_${_pluginName}_tests "${_pluginDir}/plugin_tests")
