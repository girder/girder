# This file contains cmake functions and macros common to all test types.

# This function derives a default location for a database fixture from
# a given test file.  On exit, this will set the variable `TEST_DATABASE_FILE`
# in the parent scope.  This variable will be an empty string if no
# file was found in the default location.
#
# For an input path "/path/to/spec.js", the default locations searched
# are "/path/to/spec.yml" and "/path/to/spec.json" in that order.
function(get_test_database_spec test_file)
  get_filename_component(test_dir "${test_file}" DIRECTORY)
  get_filename_component(test_basename "${test_file}" NAME_WE)

  if(EXISTS "${test_dir}/${test_basename}.yml")
    set(TEST_DATABASE_FILE "${test_dir}/${test_basename}.yml" PARENT_SCOPE)
  elseif(EXISTS "${test_dir}/${test_basename}.json")
    set(TEST_DATABASE_FILE "${test_dir}/${test_basename}.json" PARENT_SCOPE)
  else()
    set(TEST_DATABASE_FILE "" PARENT_SCOPE)
  endif()
endfunction()
