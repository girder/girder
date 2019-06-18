# All of our core javascript will be checked with a single test
add_eslint_test(core "${PROJECT_SOURCE_DIR}/girder/web_client/src")
add_puglint_test(core "${PROJECT_SOURCE_DIR}/girder/web_client/src/templates")
add_stylint_test(core "${PROJECT_SOURCE_DIR}/girder/web_client/src/stylesheets")
