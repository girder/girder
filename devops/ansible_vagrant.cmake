# This CMake file is responsible for functionality tied to running vagrant and ansible
# from CTest.
set(ANSIBLE_INVENTORY "${PROJECT_SOURCE_DIR}/.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory" CACHE FILEPATH "")
set(ANSIBLE_PRIVATE_KEY "${PROJECT_SOURCE_DIR}/.vagrant/machines/girder/virtualbox/private_key" CACHE FILEPATH "")
set(ANSIBLE_USER "vagrant" CACHE STRING "User to ssh into the vagrantbox as")

function(add_ansible_test case)
  set(name "ansible_client_test_${case}")
  set(VAGRANT_ENV_VARS "ANSIBLE_CLIENT_TESTING=1"
                       "ANSIBLE_TESTING=1")

  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${ANSIBLE_PLAYBOOK_EXECUTABLE}" -i ${ANSIBLE_INVENTORY} --private-key=${ANSIBLE_PRIVATE_KEY} -u ${ANSIBLE_USER} "${PROJECT_SOURCE_DIR}/devops/ansible/roles/girder/library/test/test_${case}.yml" -v
    )

  set_tests_properties("${name}" PROPERTIES
    DEPENDS vagrant_up
    RUN_SERIAL ON
    ENVIRONMENT "${VAGRANT_ENV_VARS}"
    # This happens in the case where vagrant up fails, failing to generate a valid host file.
    # Without this, ansible would return a valid exit status since it provisioned 0 hosts correctly.
    FAIL_REGULAR_EXPRESSION "Host file not found;no hosts matched"
    LABELS girder_ansible_client)
  set_property(GLOBAL APPEND PROPERTY vagrant_tests "${name}")
endfunction()
