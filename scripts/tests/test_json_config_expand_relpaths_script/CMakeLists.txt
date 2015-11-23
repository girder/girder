
#
# Prerequisites
#

function(add_json_config_expand_relpaths_test name)
  set(testname json_config_expand_relpaths_${name}_test)
  add_test(
    NAME ${testname}
    COMMAND ${NODEJS_EXECUTABLE} ${JSON_CONFIG_EXPAND_RELPATHS_SCRIPT} ${ARGN}
    )
  set(testname ${testname} PARENT_SCOPE)
endfunction()

#
# Setup data
#

# Input
set(input ${CMAKE_CURRENT_BINARY_DIR}/data/input.js)
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/data/input.js
  ${input}
  COPYONLY
  )

# Baseline
set(baseline_case1 ${CMAKE_CURRENT_BINARY_DIR}/data/baseline_case1.js)
set(base_dir_config ${CMAKE_CURRENT_BINARY_DIR}/data)
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/data/baseline.js.in
  ${baseline_case1}
  @ONLY
  )

set(baseline_case2 ${CMAKE_CURRENT_BINARY_DIR}/data/baseline_case2.js)
set(explicit_base_dir "/an/explicit/basedir")
set(base_dir_config ${explicit_base_dir})
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/data/baseline.js.in
  ${baseline_case2}
  @ONLY
  )

# Output
set(output_case1 ${CMAKE_CURRENT_BINARY_DIR}/data/output_case1.js)
set(output_case2 ${CMAKE_CURRENT_BINARY_DIR}/data/output_case2.js)

foreach(output IN ITEMS ${output_case1} ${output_case2})
  file(REMOVE ${output})
endforeach()

#
# Add tests
#

set(expected_usage "\nThis script allows to expand relative path in a JSON config file.\n\nUsage:")

add_json_config_expand_relpaths_test(usage)
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^${expected_usage}"
  )

add_json_config_expand_relpaths_test(usage_verbose --verbose)
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^${expected_usage}"
  )

add_json_config_expand_relpaths_test(unknown_param --unknown_param)
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^\nOption '--unknown_param' not supported."
  )

add_json_config_expand_relpaths_test(missing_relative_path_key_param -i ${input})
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^\nMissing '--relative_path_key' argument."
  )

set(relative_path_key_args -k relpath -k relpaths)

#
# Case1: Expand relpaths using config file directory as <base_dir>
#
add_json_config_expand_relpaths_test(expand
  ${relative_path_key_args} -i ${input} -o ${output_case1})
set_tests_properties(${testname}
  PROPERTIES
    REQUIRED_FILES "${input}"
  )

add_test(
  NAME ${testname}_check_result
  COMMAND ${CMAKE_COMMAND} -E compare_files ${baseline_case1} ${output_case1}
  )
set_tests_properties(${testname}_check_result
  PROPERTIES
    DEPENDS ${testname}
    REQUIRED_FILES "${baseline_case1};${output_case1}"
  )

#
# Case2: Expand relpaths explicitly specifying <base_dir>
#
add_json_config_expand_relpaths_test(expand_with_explicit_basedir
  ${relative_path_key_args} -b ${explicit_base_dir} -i ${input} -o ${output_case2})
set_tests_properties(${testname}
  PROPERTIES
    REQUIRED_FILES "${input}"
  )

add_test(
  NAME ${testname}_check_result
  COMMAND ${CMAKE_COMMAND} -E compare_files ${baseline_case2} ${output_case2}
  )
set_tests_properties(${testname}_check_result
  PROPERTIES
    DEPENDS ${testname}
    REQUIRED_FILES "${baseline_case2};${output_case2}"
  )
