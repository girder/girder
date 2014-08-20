add_python_test(search PLUGIN mongo_search)
add_python_style_test(python_static_analysis_mongo_search
                      "${PROJECT_SOURCE_DIR}/plugins/mongo_search/server")
