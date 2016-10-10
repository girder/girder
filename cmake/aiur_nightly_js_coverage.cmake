# THIS IS A HACK to work around ctest/cdash's treatment of nightly builds
# so that we can submit two separate coverage results from the same actual
# build & test run. It will appear as two distinct builds in the dashboard,
# but for now that looks like the easiest way to get both coverage results
# to show up.

set(CTEST_SOURCE_DIRECTORY "/home/cpatrick/Dashboards/girder")
set(CTEST_BINARY_DIRECTORY "/home/cpatrick/Dashboards/girder-nightly")

file(RENAME "${CTEST_BINARY_DIRECTORY}/coverage/js_coverage.xml" "${CTEST_BINARY_DIRECTORY}/../coverage.xml")
ctest_empty_binary_directory( ${CTEST_BINARY_DIRECTORY} )

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)
set(CTEST_SITE "Aiur.kitware")
set(CTEST_BUILD_NAME "Linux-master-nightly-js-cov")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")

ctest_start("Nightly")
ctest_configure()
file(RENAME "${CTEST_BINARY_DIRECTORY}/../coverage.xml" "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_coverage()
file(REMOVE "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_submit()
