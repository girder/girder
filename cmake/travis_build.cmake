include(${CTEST_SOURCE_DIRECTORY}/CTestConfig.cmake)

set(CTEST_SOURCE_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}")
set(CTEST_BINARY_DIRECTORY "$ENV{TRAVIS_BUILD_DIR}/_build")
set(CTEST_SITE "Travis")
set(CTEST_BUILD_NAME "Linux-$ENV{TRAVIS_BRANCH}")
set(CTEST_CMAKE_GENERATOR "Unix Makefiles")
set(PYTHON_COVERAGE ON)

ctest_start("Continuous")
ctest_configure()
ctest_build()
ctest_test()
ctest_coverage()
