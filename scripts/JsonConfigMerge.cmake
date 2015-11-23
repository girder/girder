
function(json_config_merge)
  set(_options )
  set(_args OUTPUTFILE)
  set(_multival_args INPUTFILES)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  set(expected_defined_vars OUTPUTFILE INPUTFILES)
  foreach(var ${expected_defined_vars})
    if(NOT DEFINED fn_${var})
      message(FATAL_ERROR "Parameter ${var} is mandatory")
    endif()
  endforeach()

  list(LENGTH fn_INPUTFILES inputfile_count)
  if(inputfile_count GREATER 1)
    set(inputfiles )
    foreach(configfile IN LISTS fn_INPUTFILES)
      if(NOT EXISTS ${configfile})
        message(FATAL_ERROR "Failed to merge JSON config file."
                            "File '${configfile}' does not exist.")
      endif()
      list(APPEND inputfiles -i ${configfile})
    endforeach()

    execute_process(
      COMMAND ${NODEJS_EXECUTABLE} ${JSON_CONFIG_MERGE_SCRIPT}
        -o ${fn_OUTPUTFILE} ${inputfiles}
      RESULT_VARIABLE result
      )
    if(NOT result EQUAL 0)
      message(FATAL_ERROR "Failed to merge config files: ${fn_INPUTFILES}")
    endif()
  else()
    configure_file(
      ${fn_INPUTFILES}
      ${fn_OUTPUTFILE}
      COPYONLY
      )
  endif()
endfunction()
