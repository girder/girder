###############################################################################
#  Copyright 2015 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

get_filename_component(PLUGIN ${CMAKE_CURRENT_LIST_DIR} NAME)

add_python_test(user_quota PLUGIN ${PLUGIN})
add_python_style_test(python_static_analysis_${PLUGIN}
                      "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/server")
add_python_style_test(python_static_analysis_${PLUGIN}_tests
                      "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests")
add_web_client_test(
    ${PLUGIN}
    "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/plugin_tests/userQuotaSpec.js"
    PLUGIN ${PLUGIN})
add_eslint_test(
    ${PLUGIN} "${PROJECT_SOURCE_DIR}/plugins/${PLUGIN}/web_client/js")
