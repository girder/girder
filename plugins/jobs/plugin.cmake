add_python_test(jobs PLUGIN jobs)

add_python_style_test(python_static_analysis_jobs
                      "${PROJECT_SOURCE_DIR}/plugins/jobs/server")

add_web_client_test(
    jobs
    "${PROJECT_SOURCE_DIR}/plugins/jobs/plugin_tests/jobsSpec.js"
    PLUGIN jobs)
add_eslint_test(
    jobs "${PROJECT_SOURCE_DIR}/plugins/jobs/web_client/js")
