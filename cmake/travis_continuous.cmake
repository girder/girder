set(CTEST_SOURCE_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}")
set(CTEST_BINARY_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}/_build")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)
set(CTEST_SITE "Travis")
set(CTEST_BUILD_NAME "Linux-$ENV{TRAVIS_BRANCH}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")

file(WRITE "${CTEST_BINARY_DIRECTORY}/CMakeCache.txt" "
PYTHON_COVERAGE:BOOL=ON
")

ctest_start("Continuous")
ctest_configure()
ctest_build()
ctest_test(PARALLEL_LEVEL 3 RETURN_VALUE res)
ctest_coverage()
file(REMOVE "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_submit()

if(NOT res EQUAL 0)
  message(FATAL_ERROR "Test failures occurred.")
endif()
