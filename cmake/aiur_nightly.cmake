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
set(CTEST_UPDATE_COMMAND "git")

ctest_start("Nightly")
ctest_update(SOURCE ${CTEST_SOURCE_DIRECTORY})

# We must run grunt so the correct git hash gets built into the version file
execute_process(COMMAND npm run build WORKING_DIRECTORY ${CTEST_SOURCE_DIRECTORY})

ctest_configure()
ctest_build()
ctest_test(PARALLEL_LEVEL 3 RETURN_VALUE res)
ctest_coverage()
ctest_submit()
