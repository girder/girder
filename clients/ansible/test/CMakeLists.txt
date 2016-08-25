cmake_minimum_required(VERSION 2.8.12)
project("Girder Ansible Module")

include(CTest)
enable_testing()

find_program(ANSIBLE_PLAYBOOK_BIN ansible-playbook)
set(ANSIBLE_INVENTORY "${PROJECT_SOURCE_DIR}/.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory" CACHE FILEPATH "")
set(ANSIBLE_PRIVATE_KEY "${PROJECT_SOURCE_DIR}/.vagrant/machines/girder/virtualbox/private_key" CACHE FILEPATH "")
set(ANSIBLE_USER "vagrant" CACHE STRING "User to ssh into the vagrantbox as")

add_test(
  NAME vagrant_up
  WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
  COMMAND vagrant up)

function(add_ansible_test case)
  set(name "test_${case}")

  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${ANSIBLE_PLAYBOOK_BIN}" -i ${ANSIBLE_INVENTORY} --private-key=${ANSIBLE_PRIVATE_KEY} -u ${ANSIBLE_USER} test_${case}.yml -v
    )

  set_tests_properties("${name}" PROPERTIES
    DEPENDS vagrant_up
    RUN_SERIAL ON)
  set_property(GLOBAL APPEND PROPERTY vagrant_tests "${name}")

endfunction()

add_ansible_test(user)
add_ansible_test(assetstore)
add_ansible_test(resources)
add_ansible_test(files)
add_ansible_test(plugin)
add_ansible_test(access)
add_ansible_test(hierarchy)
add_ansible_test(apikey)

add_test(
  NAME vagrant_destroy
  WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
  COMMAND vagrant destroy -f
  )
get_property(vagrant_tests GLOBAL PROPERTY vagrant_tests)
set_tests_properties(vagrant_destroy PROPERTIES DEPENDS "${vagrant_tests}")
