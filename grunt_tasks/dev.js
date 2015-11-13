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
    var fs = require('fs');

    grunt.config.merge({
        uglify: {
            test: {
                files: {
                    'clients/web/static/built/testing.min.js': [
                        'clients/web/test/lib/jasmine-1.3.1/jasmine.js',
                        'node_modules/blanket/dist/jasmine/blanket_jasmine.js',
                        'clients/web/test/lib/jasmine-1.3.1/ConsoleReporter.js'
                    ],
                    'clients/web/static/built/testing-no-cover.min.js': [
                        'clients/web/test/lib/jasmine-1.3.1/jasmine.js',
                        'clients/web/test/lib/jasmine-1.3.1/ConsoleReporter.js'
                    ]
                }
            },
            polyfill: {
                files: {
                    'clients/web/static/built/polyfill.min.js': [
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
                dependencies: ['shell:readServerConfig', 'uglify:app']
            }
        }
    });

    grunt.registerTask('test-env-html', 'Build the phantom test html page.', function () {
        grunt.task.requires('shell:readServerConfig');

        var jade = require('jade');
        var buffer = fs.readFileSync('clients/web/test/testEnv.jadehtml');
        var globs = grunt.config('uglify.app.files')['clients/web/static/built/app.min.js'];
        var dependencies = [
            '/clients/web/test/testUtils.js',
            '/clients/web/static/built/libs.min.js'
        ];
        var inputs = [];

        globs.forEach(function (glob) {
            var files = grunt.file.expand(glob);
            files.forEach(function (file) {
                inputs.push('/' + file);
            });
        });

        var fn = jade.compile(buffer, {
            client: false,
            pretty: true
        });
        fs.writeFileSync('clients/web/static/built/testEnv.html', fn({
            cssFiles: [
                '/clients/web/static/lib/bootstrap/css/bootstrap.min.css',
                '/clients/web/static/lib/bootstrap/css/bootstrap-switch.min.css',
                '/clients/web/static/lib/fontello/css/fontello.css',
                '/clients/web/static/lib/jsoneditor/jsoneditor.min.css',
                '/clients/web/static/built/app.min.css'
            ],
            jsFilesUncovered: dependencies,
            jsFilesCovered: inputs,
            staticRoot: grunt.config.get('serverConfig.staticRoot'),
            apiRoot: grunt.config.get('serverConfig.apiRoot')
        }));
    });
};
