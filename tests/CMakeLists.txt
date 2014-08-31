# Set this variable to the minimum coverage percentage to be considered passing
set(COVERAGE_MINIMUM_PASS 80)
set(JS_COVERAGE_MINIMUM_PASS 50)

python_tests_init()
javascript_tests_init()

add_python_style_test(python_static_analysis_core "${PROJECT_SOURCE_DIR}/girder")
add_python_style_test(python_static_analysis_core_tests "${PROJECT_SOURCE_DIR}/tests")

add_python_test(api_describe)
add_python_test(assetstore)
add_python_test(collection)
add_python_test(events)
add_python_test(routes)
add_python_test(file)
add_python_test(folder)
add_python_test(group)
add_python_test(item)
add_python_test(rest_util)
add_python_test(search)
add_python_test(system)
add_python_test(user)
add_python_test(webroot)


add_web_client_test(data "${PROJECT_SOURCE_DIR}/clients/web/test/spec/dataSpec.js")
add_web_client_test(admin "${PROJECT_SOURCE_DIR}/clients/web/test/spec/adminSpec.js")
add_web_client_test(collection "${PROJECT_SOURCE_DIR}/clients/web/test/spec/collectionSpec.js")
add_web_client_test(group "${PROJECT_SOURCE_DIR}/clients/web/test/spec/groupSpec.js")
add_web_client_test(user "${PROJECT_SOURCE_DIR}/clients/web/test/spec/userSpec.js")
add_web_client_test(item "${PROJECT_SOURCE_DIR}/clients/web/test/spec/itemSpec.js")

add_subdirectory(clients)

# Look for CMakeLists.txt in plugin dirs, include if they exist
file(GLOB pluginDirs "${PROJECT_SOURCE_DIR}/plugins/*")
foreach(pluginDir ${pluginDirs})
  if(EXISTS "${pluginDir}/plugin.cmake")
    get_filename_component(pluginName "${pluginDir}" NAME)
    message(STATUS "Including plugin.cmake from \"${pluginName}\"")
    include("${pluginDir}/plugin.cmake")
  endif()
endforeach()
