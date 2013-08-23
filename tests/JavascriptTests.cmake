function(add_javascript_style_test input)
  set(name "js_style_${input}")
  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/clients/web/src"
    COMMAND "${JSLINT_EXECUTABLE}" "${input}"
  )
endfunction()
