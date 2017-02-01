###############################################################################
#  Copyright Kitware Inc.
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

set(dicom_plugin_affix "plugins/dicom")
set(dicom_plugin_dir ${PROJECT_SOURCE_DIR}/plugins/dicom)

add_python_test(conversion
                PLUGIN dicom
                )
add_python_test(dicom
                PLUGIN dicom
                EXTERNAL_DATA "${dicom_plugin_affix}/Image0075.dcm"
                )
add_python_test(search_for_studies
                PLUGIN dicom
                EXTERNAL_DATA
                    "${dicom_plugin_affix}/Image0075.dcm"
                    "${dicom_plugin_affix}/Image0076.dcm"
                    "${dicom_plugin_affix}/Image0077.dcm"
                    "${dicom_plugin_affix}/012345.002.050"
                    "${dicom_plugin_affix}/9575"
                    "${dicom_plugin_affix}/9605"
                    "${dicom_plugin_affix}/9635"
                    "${dicom_plugin_affix}/9665"
                )
add_python_style_test(python_static_analysis_dicom "${dicom_plugin_dir}/server")
add_python_style_test(python_static_analysis_dicom_tests
                      "${dicom_plugin_dir}/plugin_tests")

