cmake_minimum_required(VERSION 2.8.6)

project(Girder NONE)

# Address warning with Ninja generator and ExternalData
if(POLICY CMP0058)
  cmake_policy(SET CMP0058 NEW)
endif()

include(CTest)

set(PYTHON_VERSION "2.7" CACHE STRING "Python version used for testing")

find_package(PythonInterp ${PYTHON_VERSION} REQUIRED)

option(PYTHON_STATIC_ANALYSIS "Run Python static analysis tests with flake8" ON)
option(PYTHON_COVERAGE "Run tests with coverage.py" ON)
option(PYTHON_BRANCH_COVERAGE "Use branch-level coverage instead of line-level" OFF)
option(JAVASCRIPT_STYLE_TESTS "Run Javascript style tests with eslint" ON)
option(BUILD_JAVASCRIPT_TESTS "Build Javascript tests" ON)
option(RUN_CORE_TESTS "Whether to run the core unit tests" ON)
option(ANSIBLE_TESTS "Whether to run Ansible tests" OFF)
option(ANSIBLE_CLIENT_TESTS "Whether to run Ansible client tests" OFF)
set(TEST_PLUGINS "" CACHE STRING "List of plugins to test. Leave empty to test all plugins")

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE NAMES coverage python-coverage)
  set(girder_py_coverage_rc "${PROJECT_BINARY_DIR}/tests/girder.coveragerc")
  set(PYTHON_COVERAGE_CONFIG "${girder_py_coverage_rc}" CACHE FILEPATH "Custom python coverage configuration file")
  mark_as_advanced(PYTHON_COVERAGE_CONFIG)
endif()

if(PYTHON_STATIC_ANALYSIS)
  find_program(FLAKE8_EXECUTABLE flake8)
endif()

if(JAVASCRIPT_STYLE_TESTS)
  find_program(NODEJS_EXECUTABLE NAMES nodejs node)
  if(NOT NODEJS_EXECUTABLE)
    message(FATAL_ERROR "'nodejs' executable couldn't be found.\n"
                        "Consider reconfiguring passing -DNODEJS_EXECUTABLE:FILEPATH=/path/to/nodejs")
  endif()
  find_program(ESLINT_EXECUTABLE eslint ${PROJECT_SOURCE_DIR}/node_modules/.bin NO_DEFAULT_PATH)
  find_program(PUGLINT_EXECUTABLE pug-lint ${PROJECT_SOURCE_DIR}/node_modules/.bin NO_DEFAULT_PATH)
endif()

if(BUILD_JAVASCRIPT_TESTS)
  find_program(ISTANBUL_EXECUTABLE istanbul
    PATHS "${PROJECT_SOURCE_DIR}/node_modules/.bin"
    NO_DEFAULT_PATH)
endif()

if(BUILD_TESTING)
  include(tests/TestData.cmake)
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
