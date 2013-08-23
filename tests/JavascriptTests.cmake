function(add_javascript_style_test name input)
  set(name "js_style_${name}")
  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/clients/web"
    COMMAND "${JSHINT_EXECUTABLE}" --config "${PROJECT_SOURCE_DIR}/tests/jshint.cfg" "${input}"
  )
endfunction()
