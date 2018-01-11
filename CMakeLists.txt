cmake_minimum_required(VERSION 2.8.6)

project(Girder NONE)

# Address warning with Ninja generator and ExternalData
if(POLICY CMP0058)
  cmake_policy(SET CMP0058 NEW)
endif()

include(CTest)
include(CMakeParseArguments)

set(PYTHON_VERSION "2.7" CACHE STRING "Python version used for testing")

find_package(PythonInterp ${PYTHON_VERSION} REQUIRED)

option(PYTHON_STATIC_ANALYSIS "Run Python static analysis tests with flake8" ON)
option(JAVASCRIPT_STYLE_TESTS "Run Javascript style tests with eslint" ON)
option(BUILD_JAVASCRIPT_TESTS "Build Javascript tests" ON)
option(RUN_CORE_TESTS "Whether to run the core tests" ON)
option(ANSIBLE_TESTS "Whether to run Ansible tests" OFF)
option(ANSIBLE_CLIENT_TESTS "Whether to run Ansible client tests" OFF)
set(TEST_PLUGINS "" CACHE STRING "List of plugins to test. Leave empty to test all plugins")

find_program(PYTHON_COVERAGE_EXECUTABLE NAMES coverage python-coverage)

if(PYTHON_STATIC_ANALYSIS)
  find_program(FLAKE8_EXECUTABLE flake8)
endif()

if(BUILD_TESTING)
  include(tests/TestData.cmake)
  include(tests/TestCommon.cmake)
  include(tests/PythonTests.cmake)
  include(tests/JavascriptTests.cmake)
  add_subdirectory(tests)
endif()

if(ANSIBLE_TESTS OR ANSIBLE_CLIENT_TESTS)
  find_program(VAGRANT_EXECUTABLE vagrant)
  if (NOT VAGRANT_EXECUTABLE)
    message(FATAL_ERROR "'vagrant' executable couldn't be found.\n"
      "Consider reconfiguring passing -DVAGRANT_EXECUTABLE:FILEPATH=/path/to/vagrant")
  endif()

  find_program(ANSIBLE_PLAYBOOK_EXECUTABLE ansible-playbook)
  if (NOT ANSIBLE_PLAYBOOK_EXECUTABLE)
    message(FATAL_ERROR "'ansible-playbook' executable couldn't be found.\n"
      "Consider reconfiguring passing -DANSIBLE_PLAYBOOK_EXECUTABLE:FILEPATH=/path/to/ansible-playbook")
  endif()

  include(devops/ansible_vagrant.cmake)

  if (ANSIBLE_TESTS)
    add_subdirectory(devops/ansible)
  endif()

  if (ANSIBLE_CLIENT_TESTS)
    add_subdirectory(devops/ansible/roles/girder/library/test)
  endif()
endif()
