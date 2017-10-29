find_program(VIRTUALENV_EXECUTABLE virtualenv)
find_program(CURL_EXECUTABLE curl)
find_program(GREP_EXECUTABLE grep)

set(virtualenv_dir "${PROJECT_BINARY_DIR}/env")
set(virtualenv_python "${virtualenv_dir}/bin/python")
set(virtualenv_pip "${virtualenv_dir}/bin/pip")
set(virtualenv_activate "${virtualenv_dir}/bin/activate")
set(girder_install "${virtualenv_dir}/bin/girder-install")

add_custom_command(
  OUTPUT "${virtualenv_python}"
  # TODO: fix this in Python 3.6 to use "python3 -m venv"
  COMMAND "${VIRTUALENV_EXECUTABLE}" -p "${PYTHON_EXECUTABLE}" env
  WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
  COMMENT "Creating virtualenv for packaging tests"
)

add_custom_target(
  virtualenv
  ALL
  DEPENDS "${virtualenv_python}"
)

add_test(
  NAME packaging_generate
  WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
  COMMAND "${PROJECT_SOURCE_DIR}/node_modules/.bin/grunt" package
)

set_property(TEST packaging_generate
  PROPERTY LABELS girder_package
)

add_test(
  NAME packaging_verify_contents
  WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
  COMMAND "${PYTHON_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/packaging/test_package_contents.py"
)

set_property(TEST packaging_verify_contents
  PROPERTY LABELS girder_package
)
set_property(TEST packaging_verify_contents
  PROPERTY DEPENDS packaging_generate
)

add_test(
  NAME packaging_install
  WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
  COMMAND "${PROJECT_SOURCE_DIR}/tests/packaging/pip_install_girder.sh"
          "${virtualenv_pip}"
          "${PROJECT_SOURCE_DIR}"
          "${virtualenv_activate}"
          "${virtualenv_dir}"
          "${CURL_EXECUTABLE}"
          "${GREP_EXECUTABLE}"
)

set_property(TEST packaging_install
  PROPERTY LABELS girder_package
)
set_property(TEST packaging_install
  PROPERTY DEPENDS "packaging_generate"
)
set_property(TEST packaging_install
  PROPERTY RESOURCE_LOCK "packaging_virtualenv"
)

add_test(
  NAME packaging_plugin_install
  WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
  COMMAND "${PROJECT_SOURCE_DIR}/tests/packaging/test_plugin_install.sh"
          "${virtualenv_activate}"
          "${PROJECT_SOURCE_DIR}"
          "${virtualenv_pip}"
)

set_property(TEST packaging_plugin_install
  PROPERTY LABELS girder_package
)
set_property(TEST packaging_plugin_install
  PROPERTY DEPENDS "packaging_install"
)
set_property(TEST packaging_plugin_install
  PROPERTY RESOURCE_LOCK "packaging_virtualenv"
)
