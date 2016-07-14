set(CTEST_SOURCE_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}")
set(CTEST_BINARY_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}/_build")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)
set(test_group "$ENV{GIRDER_TEST_GROUP}")
set(CTEST_SITE "Travis")
set(CTEST_BUILD_NAME "Linux-$ENV{TRAVIS_BRANCH}-Mongo-$ENV{MONGO_VERSION}-${test_group}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")

ctest_start("Continuous")
ctest_configure()
ctest_build()

if(test_group STREQUAL python)
  ctest_test(
    PARALLEL_LEVEL 4 RETURN_VALUE res
    INCLUDE_LABEL girder_python
  )
elseif(test_group STREQUAL browser)
  ctest_test(
    PARALLEL_LEVEL 4 RETURN_VALUE res
    EXCLUDE_LABEL girder_python
  )
  file(RENAME "${CTEST_BINARY_DIRECTORY}/js_coverage.xml" "${CTEST_BINARY_DIRECTORY}/coverage.xml")
endif()

ctest_coverage()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_submit()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/test_failed")
if(NOT res EQUAL 0)
  file(WRITE "${CTEST_BINARY_DIRECTORY}/test_failed" "error")
  message(FATAL_ERROR "Test failures occurred.")
endif()
