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
 * Define tasks that bundle and compile files for deployment.
 */
module.exports = function (grunt) {
    var path = require('path');
    var environment = grunt.option('env') || 'dev';
    var debugJs = grunt.option('debug-js') || false;
    var uglifyOptions = {
        ASCIIOnly: true,
        sourceMap: environment === 'dev',
        sourceMapIncludeSources: true,
        report: 'min'
    };

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    if (debugJs) {
        console.log('Building JS in debug mode'.yellow);
        uglifyOptions.beautify = {
            beautify: true
        };
        uglifyOptions.mangle = false;
        uglifyOptions.compress = false;
    }

    grunt.config.merge({
        jade: {
            options: {
                client: true,
                compileDebug: false,
                namespace: 'girder.templates',
                processName: function (filename) {
                    return path.basename(filename, '.jade');
                }
            },
            core: {
                files: {
                    'clients/web/static/built/templates.js': [
                        'clients/web/src/templates/**/*.jade'
                    ]
                }
            }
        },

        copy: {
            swagger: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/swagger-ui/dist',
                    src: ['lib/**', 'css/**', 'images/**', 'swagger-ui.min.js'],
                    dest: 'clients/web/static/built/swagger'
                }]
            },
            jsoneditor: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/jsoneditor/dist',
                    src: ['img/**'],
                    dest: 'clients/web/static/built/jsoneditor'
                }]
            },
            fontello_config: {
                files: [{
                    src: 'clients/web/fontello.config.json',
                    dest: 'clients/web/static/built/fontello.config.json'
                }]
            }
        },

        stylus: {
            core: {
                files: {
                    'clients/web/static/built/girder.app.min.css': [
                        'clients/web/src/stylesheets/**/*.styl',
                        '!clients/web/src/stylesheets/apidocs/*.styl'
                    ],
                    'clients/web/static/built/swagger/docs.css': [
                        'clients/web/src/stylesheets/apidocs/*.styl'
                    ]
                }
            }
        },

        fontello: {
            ext_font: {
                options: {
                    config: 'clients/web/static/built/fontello.config.json',
                    fonts: 'clients/web/static/built/fontello/font',
                    styles: 'clients/web/static/built/fontello/css',
                    // Create output directories
                    force: true
                }
            }
        },

        concat: {
            options: {
                stripBanners: {
                    block: true,
                    line: true
                }
            },
            ext_css: {
                files: {
                    'clients/web/static/built/girder.ext.min.css': [
                        'node_modules/bootstrap/dist/css/bootstrap.min.css',
                        'node_modules/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        'node_modules/eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.min.css',
                        'node_modules/jsoneditor/dist/jsoneditor.min.css',
                        'node_modules/as-jqplot/dist/jquery.jqplot.min.css'
                    ]
                }
            }
        },

        uglify: {
            options: uglifyOptions,
            app: {
                files: {
                    'clients/web/static/built/girder.app.min.js': [
                        'clients/web/static/built/templates.js',
                        'clients/web/src/init.js',
                        'clients/web/src/girder-version.js',
                        'clients/web/src/view.js',
                        'clients/web/src/app.js',
                        'clients/web/src/router.js',
                        'clients/web/src/utilities/**/*.js',
                        'clients/web/src/plugin_utils.js',
                        'clients/web/src/collection.js',
                        'clients/web/src/model.js',
                        'clients/web/src/models/**/*.js',
                        'clients/web/src/collections/**/*.js',
                        'clients/web/src/views/**/*.js'
                    ],
                    'clients/web/static/built/girder.main.min.js': [
                        'clients/web/src/main.js'
                    ]
                }
            },
            ext_js: {
                files: {
                    'clients/web/static/built/girder.ext.min.js': [
                        'node_modules/jquery/dist/jquery.js',
                        'node_modules/jade/runtime.js',
                        'node_modules/underscore/underscore.js',
                        'node_modules/backbone/backbone.js',
                        'node_modules/remarkable/dist/remarkable.js',
                        'node_modules/jsoneditor/dist/jsoneditor.js',
                        'node_modules/bootstrap/dist/js/bootstrap.js',
                        'node_modules/bootstrap-switch/dist/js/bootstrap-switch.js',
                        'node_modules/eonasdan-bootstrap-datetimepicker/bower_components/moment/moment.js',
                        'node_modules/eonasdan-bootstrap-datetimepicker/src/js/bootstrap-datetimepicker.js',
                        'node_modules/d3/d3.js',
                        'node_modules/as-jqplot/dist/jquery.jqplot.js',
                        'node_modules/as-jqplot/dist/plugins/jqplot.pieRenderer.js',
                        'node_modules/sprintf-js/src/sprintf.js'
                    ]
                }
            }
        },

        symlink: {
            options: {
                overwrite: true
            },
            legacy_names: {
                // Provide static files under old names, for compatibility
                files: [{
                    src: ['clients/web/static/built/girder.app.min.js'],
                    dest: 'clients/web/static/built/app.min.js'
                }, {
                    src: ['clients/web/static/built/girder.app.min.css'],
                    dest: 'clients/web/static/built/app.min.css'
                }, {
                    src: ['clients/web/static/built/girder.main.min.js'],
                    dest: 'clients/web/static/built/main.min.js'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.js'],
                    dest: 'clients/web/static/built/libs.min.js'
                }, {
                    // This provides more than just Bootstrap, but that no
                    // longer exists as a standalone file
                    // Note, girder.ext.min.css was never released as another
                    // name
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/lib/bootstrap/css/bootstrap.min.css'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/lib/bootstrap/css/bootstrap-switch.min.css'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/built/jsoneditor/jsoneditor.min.css'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/lib/jqplot/css/jquery.jqplot.min.css'
                }, {
                    src: ['clients/web/static/built/fontello'],
                    dest: 'clients/web/static/lib/fontello'
                }]
            }
        },

        watch: {
            stylus_core: {
                files: ['clients/web/src/stylesheets/**/*.styl'],
                tasks: ['stylus:core']
            },
            js_core: {
                files: [
                    'clients/web/src/**/*.js',
                    'clients/static/built/templates.js'
                ],
                tasks: ['uglify:app']
            },
            jade_core: {
                files: ['clients/web/src/templates/**/*.jade'],
                tasks: ['jade:core']
            }
        },

        init: {
            'uglify:ext_js': {},
            'copy:swagger': {},
            'copy:jsoneditor': {},
            'copy:fontello_config': {},
            'concat:ext_css': {},
            'fontello:ext_font': {}
        },

        default: {
            'stylus:core': {},
            'jade:core': {
                dependencies: ['version-info']
            },
            'uglify:app': {
                dependencies: ['jade:core']
            },
            'symlink:legacy_names': {
                dependencies: ['uglify:app']
            }
        }
    });
};
