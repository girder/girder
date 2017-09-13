add_standard_plugin_tests(NO_SERVER_TESTS)

get_filename_component(_pluginName "${CMAKE_CURRENT_LIST_DIR}" NAME)
add_python_test(hdfs_assetstore PLUGIN ${_pluginName} PY2_ONLY)
add_python_style_test(python_static_analysis_${_pluginName}_tests "${_pluginDir}/plugin_tests")
