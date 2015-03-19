
function(json_config_expand_relpaths)
  set(_options )
  set(_args INPUTFILE OUTPUTFILE BASEDIR)
  set(_multival_args RELATIVE_PATH_KEYS)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})

  set(expected_defined_vars INPUTFILE OUTPUTFILE RELATIVE_PATH_KEYS)
  foreach(var ${expected_defined_vars})
    if(NOT DEFINED fn_${var})
      message(FATAL_ERROR "Parameter ${var} is mandatory")
    endif()
  endforeach()

  set(expected_existing_vars INPUTFILE)
  if(DEFINED fn_BASEDIR)
    list(APPEND expected_existing_vars BASEDIR)
  endif()
  foreach(var ${expected_existing_vars})
    if(NOT EXISTS "${fn_${var}}")
      message(FATAL_ERROR "Parameter ${var} set to ${fn_${var}} corresponds to an nonexistent file.")
    endif()
  endforeach()

  set(basedir_arg)
  if(DEFINED fn_BASEDIR)
    set(basedir_arg -b ${fn_BASEDIR})
  endif()

  set(relpathkey_args)
  foreach(key IN LISTS fn_RELATIVE_PATH_KEYS)
    list(APPEND relpathkey_args -k ${key})
  endforeach()

  execute_process(
    COMMAND ${NODEJS_EXECUTABLE} ${JSON_CONFIG_EXPAND_RELPATHS_SCRIPT}
      ${basedir_arg} ${relpathkey_args} -o ${fn_OUTPUTFILE} -i ${fn_INPUTFILE}
    )
endfunction()
