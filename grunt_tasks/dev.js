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
module.exports = function (grunt) {
    if (grunt.config.get('environment') !== 'dev') {
        return;
    }

    var fs = require('fs');

    grunt.config.merge({
        uglify: {
            test: {
                files: {
                    'clients/web/static/built/testing/testing.min.js': [
                        'node_modules/core-js/client/shim.js',
                        'clients/web/test/lib/jasmine-1.3.1/jasmine.js',
                        'clients/web/test/lib/jasmine-1.3.1/ConsoleReporter.js',
                        'clients/web/test/testUtils.js'
                    ]
                }
            }
        },
        copy: {
            test: {
                src: 'clients/web/test/lib/jasmine-1.3.1/jasmine.css',
                dest: 'clients/web/static/built/testing/testing.min.css'
            }
        },

        default: {
            'test-env-html': {
                dependencies: ['build', 'uglify:test', 'copy:test']
            },
            'uglify:test': {},
            'copy:test': {}
        }
    });

    grunt.registerTask('test-env-html', 'Build the phantom test html page.', function () {
        var pug = require('pug');
        var buffer = fs.readFileSync('clients/web/test/testEnv.pug');

        var fn = pug.compile(buffer, {
            client: false,
            pretty: true
        });
        fs.writeFileSync('clients/web/static/built/testing/testEnv.html', fn({
            cssFiles: [
                '/static/built/fontello/css/fontello.css',
                '/static/built/girder_lib.min.css',
                '/static/built/girder_app.min.css',
                '/static/built/testing.min.css'
            ],
            jsFiles: [
                '/static/built/girder_lib.min.js',
                '/static/built/girder_app.min.js',
                '/static/built/testing/testing.min.js'
            ],
            staticRoot: '/static',
            apiRoot: '/api/v1'
        }));
    });
};
