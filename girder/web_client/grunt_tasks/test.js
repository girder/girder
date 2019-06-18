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
