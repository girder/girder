if(RUN_CORE_TESTS)
  add_eslint_test(core_scripts scripts)

  add_subdirectory(test_json_config_expand_relpaths_script)
  add_subdirectory(test_json_config_merge_script)
endif()
