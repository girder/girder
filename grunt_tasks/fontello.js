/**
 * Copyright 2015 Kitware Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Define tasks that download and copy fontello font files.
 */
module.exports = function (grunt) {
    grunt.config.merge({
        // Why is this tasks necessary? Can't ext-font work off the one in src/assets?
        copy: {
            fontello_config: {
                files: [{
                    src: 'clients/web/src/assets/fontello.config.json',
                    dest: 'clients/web/static/built/fontello/fontello.config.json'
                }]
            }
        },

        fontello: {
            ext_font: {
                options: {
                    config: 'clients/web/static/built/fontello/fontello.config.json',
                    fonts: 'clients/web/static/built/fontello/font',
                    styles: 'clients/web/static/built/fontello/css',
                    // Create output directories
                    force: true
                }
            }
        },

        init: {
            'copy:fontello_config': {},
            'fontello:ext_font': {}
        }
    });
};
