add_test(
  NAME documentation_generate
  WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
  COMMAND npx grunt docs:clean
)

set_property(TEST documentation_generate
  PROPERTY FAIL_REGULAR_EXPRESSION "ERROR"
)
set_property(TEST documentation_generate
  PROPERTY LABELS girder_browser
)
