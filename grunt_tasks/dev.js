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
    if (!grunt.config.get('isSourceBuild')) {
        // If this is a package build rather than a source build, we skip the
        // dev build tasks.
        return;
    }

    var fs = require('fs');

    grunt.config.merge({
        uglify: {
            test: {
                files: {
                    'clients/web/static/built/testing/testing.min.js': [
                        'clients/web/test/lib/jasmine-1.3.1/jasmine.js',
                        'clients/web/test/lib/jasmine-1.3.1/ConsoleReporter.js'
                    ]
                }
            },
            polyfill: {
                files: {
                    'clients/web/static/built/testing/polyfill.min.js': [
                        'node_modules/phantomjs-polyfill/bind-polyfill.js'
                    ]
                }
            }
        },

        init: {
            'uglify:polyfill': {}
        },

        default: {
            'test-env-html': {
                dependencies: ['build']
            },
            'uglify:test': {}
        }
    });

    grunt.registerTask('test-env-html', 'Build the phantom test html page.', function () {
        var pug = require('pug');
        var buffer = fs.readFileSync('clients/web/test/testEnv.pug');
        var dependencies = [
            '/clients/web/static/built/girder.ext.min.js',
            '/clients/web/test/testUtils.js'
        ];
        var inputs = [
            '/clients/web/static/built/girder.app.min.js'
        ];

        var fn = pug.compile(buffer, {
            client: false,
            pretty: true
        });
        fs.writeFileSync('clients/web/static/built/testing/testEnv.html', fn({
            cssFiles: [
                '/clients/web/static/built/fontello/css/fontello.css',
                '/clients/web/static/built/girder.ext.min.css',
                '/clients/web/static/built/girder.app.min.css'
            ],
            jsFilesUncovered: dependencies,
            jsFilesCovered: inputs,
            staticRoot: '/static',
            apiRoot: '/api/v1'
        }));
    });
};
