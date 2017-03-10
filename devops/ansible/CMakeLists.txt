# These tests are part of the girder_ansible label
file(GLOB examples "${PROJECT_SOURCE_DIR}/devops/ansible/examples/girder-*")

set(TEST_BOXES "ubuntu/trusty64" "centos/7")

foreach (EXAMPLE_DIR ${examples})
  foreach (VAGRANT_BOX ${TEST_BOXES})
    get_filename_component(EXAMPLE_NAME ${EXAMPLE_DIR} NAME)

    set(VAGRANT_ENV_VARS "GIRDER_EXAMPLE=${EXAMPLE_NAME}"
                         "ANSIBLE_TESTING=1"
                         "VAGRANT_BOX=${VAGRANT_BOX}")

    add_test(NAME "ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_up"
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND ${VAGRANT_EXECUTABLE} up --no-provision)
    set_tests_properties("ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_up"
      PROPERTIES
      ENVIRONMENT "${VAGRANT_ENV_VARS}"
      RUN_SERIAL ON
      LABELS girder_ansible)

    add_test(NAME "ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_provision"
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND ${VAGRANT_EXECUTABLE} provision)
    set_tests_properties("ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_provision"
      PROPERTIES
      ENVIRONMENT "${VAGRANT_ENV_VARS}"
      FAIL_REGULAR_EXPRESSION "VM not created."
      RUN_SERIAL ON
      DEPENDS "ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_up"
      LABELS girder_ansible)

    add_test(NAME "ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_destroy"
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND ${VAGRANT_EXECUTABLE} destroy -f)
    set_tests_properties("ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_destroy"
      PROPERTIES
      FAIL_REGULAR_EXPRESSION "VM not created."
      RUN_SERIAL ON
      DEPENDS "ansible_example_${VAGRANT_BOX}_${EXAMPLE_NAME}_vagrant_up"
      LABELS girder_ansible)
  endforeach()
endforeach()
