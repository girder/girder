set(CTEST_SOURCE_DIRECTORY "$ENV{HOME}/Dashboards/girder")
set(CTEST_BINARY_DIRECTORY "$ENV{HOME}/Builds/girder-$ENV{PYENV_VERSION}")

set(CTEST_SITE "garant")
set(CTEST_BUILD_NAME "Linux-$ENV{GIRDER_BRANCH}-nightly-python-$ENV{PYENV_VERSION}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")
set(CTEST_UPDATE_COMMAND "git")

# rebuild EVERYTHING from scratch
execute_process(COMMAND git checkout -f $ENV{GIRDER_BRANCH} WORKING_DIRECTORY "${CTEST_SOURCE_DIRECTORY}")
execute_process(COMMAND git clean -fdx WORKING_DIRECTORY "${CTEST_SOURCE_DIRECTORY}")

ctest_start("Nightly")
ctest_update(SOURCE "${CTEST_SOURCE_DIRECTORY}")
ctest_submit(PARTS Start Update)

execute_process(COMMAND "$ENV{NPM_EXECUTABLE}" install WORKING_DIRECTORY "${CTEST_SOURCE_DIRECTORY}")

# install core dependencies
execute_process(COMMAND "$ENV{PIP_EXECUTABLE}" install -e .[plugins] WORKING_DIRECTORY "${CTEST_SOURCE_DIRECTORY}")

# install development deps keeping the core deps installed already
execute_process(COMMAND "$ENV{PIP_EXECUTABLE}" install -r requirements-dev.txt WORKING_DIRECTORY "${CTEST_SOURCE_DIRECTORY}")

# build and test
ctest_configure(
  OPTIONS
  "-DPYTHON_VERSION=$ENV{PYENV_VERSION};-DPYTHON_EXECUTABLE=$ENV{PYTHON_EXECUTABLE};-DVIRTUALENV_EXECUTABLE=$ENV{VIRTUALENV_EXECUTABLE}"
)
ctest_submit(PARTS Configure)
ctest_build()
ctest_submit(PARTS Build)
ctest_test(PARALLEL_LEVEL 1)
ctest_submit(PARTS Test)
ctest_coverage()
ctest_submit(PARTS Coverage)

ctest_submit(PARTS Notes ExtraFiles Upload Submit)
