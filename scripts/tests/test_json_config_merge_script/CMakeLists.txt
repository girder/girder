
#
# Prerequisites
#

function(add_json_config_merge_test name)
  set(testname json_config_merge_${name}_test)
  add_test(
    NAME ${testname}
    COMMAND ${NODEJS_EXECUTABLE} ${JSON_CONFIG_MERGE_SCRIPT} ${ARGN}
    )
  set(testname ${testname} PARENT_SCOPE)
endfunction()

#
# Setup data
#

foreach(filename IN ITEMS
  input1.js
  input2.js
  input3.js
  baseline_input_1_and_2.js
  baseline_input_1_and_2_and_3.js
  )
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/data/${filename}
    ${CMAKE_CURRENT_BINARY_DIR}/data/${filename}
    COPYONLY
    )
endforeach()

set(input1 ${CMAKE_CURRENT_BINARY_DIR}/data/input1.js)
set(input2 ${CMAKE_CURRENT_BINARY_DIR}/data/input2.js)
set(input3 ${CMAKE_CURRENT_BINARY_DIR}/data/input3.js)

set(baseline_case1 ${CMAKE_CURRENT_BINARY_DIR}/data/baseline_input_1_and_2.js)
set(baseline_case2 ${CMAKE_CURRENT_BINARY_DIR}/data/baseline_input_1_and_2_and_3.js)

set(output_case1 ${CMAKE_CURRENT_BINARY_DIR}/data/output_input_1_and_2.js)
set(output_case2 ${CMAKE_CURRENT_BINARY_DIR}/data/output_input_1_and_2_and_3.js)

foreach(output IN ITEMS ${output_case1} ${output_case2})
  file(REMOVE ${output})
endforeach()

#
# Add tests
#

set(expected_usage "\nThis script allows to merge multiple JSON config files.\n\nUsage:")

add_json_config_merge_test(usage)
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^${expected_usage}"
  )

add_json_config_merge_test(usage_verbose --verbose)
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^${expected_usage}"
  )

add_json_config_merge_test(unknown_param --unknown_param)
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^\nOption '--unknown_param' not supported."
  )

add_json_config_merge_test(missing_outputfile_param -i ${input1})
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^\nMissing '--outputfile' argument."
  )

add_json_config_merge_test(missing_inputfile_param -o ${output_case1} -i ${input1})
set_tests_properties(${testname}
  PROPERTIES
    PASS_REGULAR_EXPRESSION "^\nAt least two config files should be specified."
  )

#
# Case1: Two input files
#
add_json_config_merge_test(input1_and_input2 -o ${output_case1} -i ${input1} -i ${input2})
set_tests_properties(${testname}
  PROPERTIES
    REQUIRED_FILES "${input1};${input2}"
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
# Case2: Three input files
#
add_json_config_merge_test(input1_and_input2_and_input3 -o ${output_case2} -i ${input1} -i ${input2} -i ${input3})
set_tests_properties(${testname}
  PROPERTIES
    REQUIRED_FILES "${input1};${input2};${input3}"
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
