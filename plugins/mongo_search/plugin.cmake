add_python_test(search PLUGIN mongo_search)
if(PYTHON_STYLE_TESTS)
  add_python_style_test(pep8_style_mongo_search
                        "${PROJECT_SOURCE_DIR}/plugins/mongo_search/server")
endif()
