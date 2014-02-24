/**
 * Copyright 2013 Kitware Inc.
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

module.exports = function (grunt) {
    var fs = require('fs');
    var path = require('path');

    // Pass a "--env=<value>" argument to grunt. Default value is "dev".
    var environment = grunt.option('env') || 'dev';

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    // Project configuration.
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        jade: {
            inputDir: 'clients/web/src/templates',
            outputFile: 'clients/web/static/built/templates.js'
        },

        copy: {
            swagger: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/swagger-ui/dist',
                    src: ['lib/**', 'css/**', 'images/**', 'swagger-ui.min.js'],
                    dest: 'clients/web/static/built/swagger'
                }, {
                    expand: true,
                    cwd: 'node_modules/requirejs',
                    src: ['require.js'],
                    dest: 'clients/web/static/built/swagger/lib'
                }]
            }
        },

        stylus: {
            compile: {
                files: {
                    'clients/web/static/built/app.min.css': [
                        'clients/web/src/stylesheets/**/*.styl',
                        '!clients/web/src/stylesheets/apidocs/*.styl'
                    ],
                    'clients/web/static/built/swagger/docs.css': [
                        'clients/web/src/stylesheets/apidocs/*.styl'
                    ]
                }
            }
        },

        shell: {
            sphinx: {
                command: [
                    'cd docs',
                    'make html'
                ].join('&&'),
                options: {
                    stdout: true
                }
            }
        },

        uglify: {
            options: {
                sourceMap: environment === 'dev',
                sourceMapIncludeSources: true,
                report: 'min'
            },
            app: {
                files: {
                    'clients/web/static/built/app.min.js': [
                        'clients/web/static/built/templates.js',
                        'clients/web/src/init.js',
                        'clients/web/src/app.js',
                        'clients/web/src/router.js',
                        'clients/web/src/utilities.js',
                        'clients/web/src/collection.js',
                        'clients/web/src/model.js',
                        'clients/web/src/models/**/*.js',
                        'clients/web/src/collections/**/*.js',
                        'clients/web/src/views/**/*.js'
                    ]
                }
            },
            libs: {
                files: {
                    'clients/web/static/built/libs.min.js': [
                        'node_modules/jquery-browser/lib/jquery.js',
                        'node_modules/jade/runtime.js',
                        'node_modules/underscore/underscore.js',
                        'node_modules/backbone/backbone.js',
                        'clients/web/lib/js/bootstrap.min.js',
                        'clients/web/lib/js/jquery.jqplot.min.js',
                        'clients/web/lib/js/jqplot.pieRenderer.min.js'
                    ]
                }
            }
        },

        watch: {
            css: {
                files: ['clients/web/src/stylesheets/**/*.styl'],
                tasks: ['stylus'],
                options: {failOnError: false}
            },
            js: {
                files: ['clients/web/src/**/*.js'],
                tasks: ['uglify:app'],
                options: {failOnError: false}
            },
            jade: {
                files: ['clients/web/src/templates/**/*.jade'],
                tasks: ['build-js'],
                options: {failOnError: false}
            },
            jadeindex: {
                files: ['clients/web/src/templates/index.jadehtml'],
                tasks: ['jade-index'],
                options: {failOnError: false}
            },
            swagger: {
                files: ['clients/web/src/templates/swagger/swagger.jadehtml'],
                tasks: ['swagger-ui'],
                options: {failOnError: false}
            }
        }
    });

    grunt.loadNpmTasks('grunt-shell');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-qunit');
    grunt.loadNpmTasks('grunt-contrib-stylus');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-copy');

    grunt.registerTask('swagger-ui', 'Build swagger front-end requirements.', function () {

        var jade = require('jade');
        var buffer = fs.readFileSync('clients/web/src/templates/swagger/swagger.jadehtml');

        var fn = jade.compile(buffer, {
            client: false
        });
        fs.writeFileSync('clients/web/static/built/swagger/swagger.html', fn({}));
    });

    // Compile the jade templates into a single js file
    grunt.registerTask('jade', 'Build the templates', function () {
        var config = grunt.config.get('jade');
        var outputFile = config.outputFile;
        var jade = require('jade');

        var task = this;
        var inputFiles = grunt.file.expand(config.inputDir+"/**/*.jade");

        fs.writeFileSync(outputFile, '\nvar jade=jade||{};jade.templates=jade.templates||{};\n');

        inputFiles.forEach(function (filename, i) {
            var buffer = fs.readFileSync(filename);
            var basename = path.basename(filename, '.jade');
            console.log('Compiling template: ' + basename);

            var fn = jade.compile(buffer, {
                client: true,
                compileDebug: false
            });

            var jt = "\njade.templates['" + basename + "']=" + fn.toString() + ';';
            fs.appendFileSync(outputFile, jt);
        });
        console.log('Wrote ' + inputFiles.length + ' templates into ' + outputFile);
    });

    grunt.registerTask('jade-index', 'Build index.html using jade', function () {
        var jade = require('jade');
        var buffer = fs.readFileSync('clients/web/src/templates/index.jadehtml');

        var fn = jade.compile(buffer, {
            client: false,
            pretty: true
        });
        var html = fn({
            stylesheets: ['lib/bootstrap/css/bootstrap.min.css',
                          'lib/fontello/css/fontello.css',
                          'lib/fontello/css/animation.css',
                          'lib/jqplot/css/jquery.jqplot.min.css',
                          'built/app.min.css'],
            scripts: ['built/libs.min.js',
                      'built/app.min.js']
        });
        fs.writeFileSync('clients/web/static/built/index.html', html);
        console.log('Built index.html.');
    });

    // This task should be run once manually at install time.
    grunt.registerTask('setup', 'Initial install/setup tasks', function () {
        // Copy all configuration files that don't already exist
        var cfgDir = 'girder/conf';
        var configs = grunt.file.expand(cfgDir + '/*.cfg');
        configs.forEach(function (config) {
            var name = path.basename(config);
            if (name.substring(0, 5) === 'local') {
                return;
            }
            var local = cfgDir + '/local.' + name;
            if (!fs.existsSync(local)) {
                fs.writeFileSync(local, fs.readFileSync(config));
                console.log('Created config ' + local + '.');
            }
        });
    });

    grunt.registerTask('build-js', ['jade', 'jade-index', 'uglify:app']);
    grunt.registerTask('init', ['setup', 'uglify:libs', 'copy:swagger', 'swagger-ui']);
    grunt.registerTask('docs', ['shell']);
    grunt.registerTask('default', ['stylus', 'build-js']);
};
