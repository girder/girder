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
 * Define tasks specific to development. These tasks are excluded from the
 * build system for installed girder packages.
 */
var path = require('path');

module.exports = function (grunt) {
    if (grunt.config.get('environment') !== 'dev') {
        return;
    }

    function resolveBuiltPath() {
        var built = grunt.config.get('builtPath');
        return path.resolve(...[built, ...arguments]);
    }

    function resolveTestPath() {
        return path.resolve(...[
            'test', ...arguments
        ]);
    }

    grunt.config.merge({
        uglify: {
            test: {
                files: {
                    [resolveBuiltPath('testing.min.js')]: [
                        require.resolve('babel-polyfill/dist/polyfill.js'),
                        require.resolve('whatwg-fetch/fetch.js'),
                        resolveTestPath('lib/jasmine-1.3.1/jasmine.js'),
                        resolveTestPath('lib/jasmine-1.3.1/ConsoleReporter.js'),
                        resolveTestPath('testUtils.js')
                    ]
                }
            }
        },
        copy: {
            test: {
                src: resolveTestPath('lib/jasmine-1.3.1/jasmine.css'),
                dest: resolveBuiltPath('testing.min.css')
            }
        },
        pug: {
            test: {
                src: resolveTestPath('testEnv.pug'),
                dest: resolveBuiltPath('testEnv.html'),
                options: {
                    data: {
                        cssFiles: [
                            '/static/built/girder_lib.min.css',
                            '/static/built/testing/testing.min.css'
                        ],
                        jsFiles: [
                            '/static/built/girder_lib.min.js',
                            '/static/built/girder_app.min.js',
                            '/static/built/testing.min.js'
                        ],
                        apiRoot: '/api/v1'
                    },
                    pretty: true
                }
            }
        }
    });

    grunt.registerTask('test-env-html', 'Build the phantom test html page.', [
        'uglify:test',
        'copy:test',
        'pug:test'
    ]);
    grunt.config.merge({
        default: {
            'test-env-html': {}
        }
    });
};
