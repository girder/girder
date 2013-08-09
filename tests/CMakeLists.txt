function(add_python_test testName caseName)
  add_test(
    NAME "Server_${testName}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v tests.cases.${caseName}_test
  )
  set_property(TEST "Server_${testName}" PROPERTY RESOURCE_LOCK mongo cherrypy)
endfunction()

add_python_test(User user)
add_python_test(Folder folder)
