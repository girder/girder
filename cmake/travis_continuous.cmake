set(CTEST_SOURCE_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}")
set(CTEST_BINARY_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}/_build")

include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)
set(test_group "$ENV{GIRDER_TEST_GROUP}")
set(CTEST_SITE "Travis")
set(CTEST_BUILD_NAME "Linux-$ENV{TRAVIS_BRANCH}-Mongo-$ENV{MONGO_VERSION}-${test_group}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")
set(include_label ".*")
set(exclude_label "")

if(test_group STREQUAL python)
  set(include_label "girder_python")
elseif(test_group STREQUAL browser)
  set(include_label "girder_browser")
elseif(test_group STREQUAL packaging)
  set(include_label "girder_packaging")
elseif(test_group STREQUAL other)
  set(exclude_label "(girder_python|girder_browser|girder_packaging)")
endif()

ctest_start("Continuous")
ctest_configure()
ctest_build()

if(test_group STREQUAL other)
  ctest_test(
    PARALLEL_LEVEL 4 RETURN_VALUE res
    EXCLUDE_LABEL "${exclude_label}"
  )
else()
  ctest_test(
    PARALLEL_LEVEL 4 RETURN_VALUE res
    INCLUDE_LABEL "${include_label}"
  )
endif()

if(test_group STREQUAL "python")
  ctest_coverage()
elseif(test_group STREQUAL "browser")
  file(RENAME "${CTEST_BINARY_DIRECTORY}/js_coverage.xml" "${CTEST_BINARY_DIRECTORY}/coverage.xml")
  ctest_coverage()
endif()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/coverage.xml")
ctest_submit()

file(REMOVE "${CTEST_BINARY_DIRECTORY}/test_failed")
if(NOT res EQUAL 0)
  file(WRITE "${CTEST_BINARY_DIRECTORY}/test_failed" "error")
  message(FATAL_ERROR "Test failures occurred.")
endif()
