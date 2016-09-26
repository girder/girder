# All of our core javascript will be checked with a single test
add_eslint_test(core "${PROJECT_SOURCE_DIR}/clients/web/src")
add_puglint_test(core "${PROJECT_SOURCE_DIR}/clients/web/src/templates")
