set(CTEST_SOURCE_DIRECTORY "/home/cpatrick/Dashboards/girder")
set(CTEST_BINARY_DIRECTORY "/home/cpatrick/Dashboards/girder-nightly")

ctest_empty_binary_directory( ${CTEST_BINARY_DIRECTORY} )

file(WRITE "${CTEST_BINARY_DIRECTORY}/CMakeCache.txt" "
PYTHON_COVERAGE:BOOL=ON
")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)
set(CTEST_SITE "Aiur.kitware")
set(CTEST_BUILD_NAME "Linux-master-nightly")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")

ctest_start("Nightly")
ctest_configure()
ctest_build()
ctest_test(PARALLEL_LEVEL 3 RETURN_VALUE res)
ctest_coverage()
ctest_submit()
