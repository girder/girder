
add_javascript_style_test(
  core_scripts ${PROJECT_SOURCE_DIR}/scripts
  JSHINT_EXTRA_CONFIGS ${PROJECT_SOURCE_DIR}/scripts/.jshintrc
  JSSTYLE_EXTRA_CONFIGS ${PROJECT_SOURCE_DIR}/scripts/.jscsrc
  )

add_subdirectory(test_json_config_expand_relpaths_script)
add_subdirectory(test_json_config_merge_script)
