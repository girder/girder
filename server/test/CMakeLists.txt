function(add_python_test testName caseName)
  add_test(
    NAME "Server_${testName}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/server"
    COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v test.cases.${caseName}_test
  )
endfunction()

add_python_test(User user)
add_python_test(Folder folder)
