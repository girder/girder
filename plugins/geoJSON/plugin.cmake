add_python_test(features PLUGIN geoJSON)
add_python_test(endpoint PLUGIN geoJSON)

add_python_style_test(pep8_style_geojson
                      "${PROJECT_SOURCE_DIR}/plugins/geoJSON/server")
