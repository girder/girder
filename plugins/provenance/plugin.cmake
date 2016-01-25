###############################################################################
#  Copyright 2014 Kitware Inc.
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

add_python_test(provenance PLUGIN provenance)
add_python_style_test(pep8_style_provenance
                      "${PROJECT_SOURCE_DIR}/plugins/provenance/server")
add_web_client_test(
    provenance
    "${PROJECT_SOURCE_DIR}/plugins/provenance/plugin_tests/provenanceSpec.js"
    PLUGIN provenance)
add_eslint_test(
    provenance "${PROJECT_SOURCE_DIR}/plugins/provenance/web_client/js")
