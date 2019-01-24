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

const path = require('path');

/**
 * Define tasks that copy and configure swagger API/doc files.
 */
module.exports = function (grunt) {
    const builtPath = path.resolve(grunt.config.get('builtPath'), 'swagger');
    // require.resolve('@girder/core') finds the main index.js
    const webSrc = path.dirname(require.resolve('@girder/core'));
    grunt.config.merge({
        copy: {
            swagger: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/swagger-ui/dist',
                    src: ['lib/**', 'css/**', 'images/**', 'swagger-ui.min.js'],
                    dest: builtPath
                }]
            },
            'girder-swagger': {
                files: [{
                    expand: true,
                    cwd: 'static',
                    src: ['girder-swagger.js'],
                    dest: builtPath
                }]
            }
        },

        stylus: {
            swagger: {
                files: {
                    [path.resolve(builtPath, 'docs.css')]: [
                        path.resolve(webSrc, 'stylesheets/apidocs/*.styl')
                    ]
                }
            }
        },

        default: {
            'copy:swagger': {},
            'copy:girder-swagger': {},
            'stylus:swagger': {}
        }
    });
};
