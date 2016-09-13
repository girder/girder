# These tests are part of the girder_ansible_client label

add_test(
  NAME ansible_client_test_vagrant_up
  WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
  COMMAND ${VAGRANT_EXECUTABLE} up)

set(VAGRANT_ENV_VARS "ANSIBLE_CLIENT_TESTING=1"
                     "ANSIBLE_TESTING=1")

set_tests_properties(ansible_client_test_vagrant_up PROPERTIES
  LABELS girder_ansible_client
  ENVIRONMENT "${VAGRANT_ENV_VARS}")

add_ansible_test(user)
add_ansible_test(assetstore)
add_ansible_test(resources)
add_ansible_test(files)
add_ansible_test(plugin)
add_ansible_test(access)
add_ansible_test(hierarchy)
add_ansible_test(apikey)
add_ansible_test(setting)

add_test(
  NAME ansible_client_test_vagrant_destroy
  WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
  COMMAND ${VAGRANT_EXECUTABLE} destroy -f
  )
get_property(vagrant_tests GLOBAL PROPERTY vagrant_tests)
set_tests_properties(ansible_client_test_vagrant_destroy PROPERTIES DEPENDS "${vagrant_tests}" LABELS girder_ansible_client)
