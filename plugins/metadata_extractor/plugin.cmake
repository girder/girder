add_standard_plugin_tests(NO_SERVER_TESTS)

get_filename_component(_pluginName "${CMAKE_CURRENT_LIST_DIR}" NAME)
add_python_test(client_metadata_extractor PLUGIN ${_pluginName} RESOURCE_LOCKS cherrypy PY2_ONLY)
add_python_test(server_metadata_extractor PLUGIN ${_pluginName} RESOURCE_LOCKS cherrypy PY2_ONLY)
