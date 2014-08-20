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
    var apiRoot;
    var staticRoot;
    var fs = require('fs');
    var jade = require('jade');
    var path = require('path');
    require('colors');

    var defaultTasks = ['stylus', 'build-js'];

    // Pass a "--env=<value>" argument to grunt. Default value is "dev".
    var environment = grunt.option('env') || 'dev';

    var setServerConfig = function (err, stdout, stderr, callback) {
        if (err) {
            grunt.fail.fatal('config_parse failed on local.server.cfg: ' + stderr);
        }
        try {
            var cfg = JSON.parse(stdout);
            apiRoot = (cfg.server.api_root || '/api/v1').replace(/\"/g, "");
            staticRoot = (cfg.server.static_root || '/static').replace(/\"/g, "");
            console.log('Static root: ' + staticRoot.bold);
            console.log('API root: ' + apiRoot.bold);
        }
        catch (e) {
            grunt.warn('Invalid json from config_parse: ' + stdout);
        }
        callback();
    };

    // Project configuration.
    grunt.config.init({
        pkg: grunt.file.readJSON('package.json'),

        jade: {
            options: {
                client: true,
                compileDebug: false,
                namespace: 'jade.templates',
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
                }, {
                    expand: true,
                    cwd: 'node_modules/requirejs',
                    src: ['require.js'],
                    dest: 'clients/web/static/built/swagger/lib'
                }]
            }
        },

        stylus: {
            core: {
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
            },
            readServerConfig: {
                command: 'python config_parse.py girder/conf/girder.local.cfg',
                options: {
                    stdout: false,
                    callback: setServerConfig
                }
            }
        },

        uglify: {
            options: {
                sourceMap: environment === 'dev',
                sourceMapIncludeSources: true,
                report: 'min',
                beautify: {
                    ascii_only: true
                }
            },
            app: {
                files: {
                    'clients/web/static/built/app.min.js': [
                        'clients/web/static/built/templates.js',
                        'clients/web/src/init.js',
                        'clients/web/src/app.js',
                        'clients/web/src/router.js',
                        'clients/web/src/utilities/**/*.js',
                        'clients/web/src/plugin_utils.js',
                        'clients/web/src/collection.js',
                        'clients/web/src/model.js',
                        'clients/web/src/view.js',
                        'clients/web/src/models/**/*.js',
                        'clients/web/src/collections/**/*.js',
                        'clients/web/src/views/**/*.js'
                    ],
                    'clients/web/static/built/main.min.js': [
                        'clients/web/src/main.js'
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
                        'clients/web/lib/js/d3.js',
                        'clients/web/lib/js/bootstrap.js',
                        'clients/web/lib/js/bootstrap-switch.js',
                        'clients/web/lib/js/jquery.jqplot.js',
                        'clients/web/lib/js/jqplot.pieRenderer.js'
                    ],
                    'clients/web/static/built/testing.min.js': [
                        'clients/web/test/lib/jasmine-1.3.1/jasmine.js',
                        'node_modules/blanket/dist/jasmine/blanket_jasmine.js',
                        'clients/web/test/lib/jasmine-1.3.1/ConsoleReporter.js'
                    ]
                }
            }
        },

        watch: {
            stylus_core: {
                files: ['clients/web/src/stylesheets/**/*.styl'],
                tasks: ['stylus:core']
            },
            js_core: {
                files: ['clients/web/src/**/*.js'],
                tasks: ['uglify:app']
            },
            jade_core: {
                files: ['clients/web/src/templates/**/*.jade'],
                tasks: ['build-js']
            },
            swagger: {
                files: ['clients/web/src/templates/swagger/swagger.jadehtml'],
                tasks: ['swagger-ui']
            },
            sphinx: {
                files: ['docs/*.rst'],
                tasks: ['docs']
            }
        }
    });

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    // Configure a given plugin for building
    var configurePlugin = function (pluginDir) {
        var pluginName = path.basename(pluginDir);
        var staticDir = 'clients/web/static/built/plugins/' + pluginName;

        console.log(('Found plugin: ' + pluginName).bold.underline);

        if (!fs.existsSync(staticDir)) {
            fs.mkdirSync(staticDir);
        }

        var jadeDir = pluginDir + '/web_client/templates';
        if (fs.existsSync(jadeDir)) {
            var files = {};
            files[staticDir + '/templates.js'] = [jadeDir + '/**/*.jade'];
            grunt.config.set('jade.plugin_' + pluginName, {
                files: files
            });
            grunt.config.set('watch.jade_' + pluginName, {
                files: [jadeDir + '/**/*.jade'],
                tasks: ['jade:plugin_' + pluginName, 'uglify:plugin_' + pluginName]
            });
        }

        var cssDir = pluginDir + '/web_client/stylesheets';
        if (fs.existsSync(cssDir)) {
            var files = {};
            files[staticDir + '/plugin.min.css'] = [cssDir + '/**/*.styl'];
            grunt.config.set('stylus.plugin_' + pluginName, {
                files: files
            });
            grunt.config.set('watch.stylus_' + pluginName, {
                files: [cssDir + '/**/*.styl'],
                tasks: ['stylus:plugin_' + pluginName]
            });
        }

        var jsDir = pluginDir + '/web_client/js';
        if (fs.existsSync(jsDir)) {
            var files = {};
            files[staticDir + '/plugin.min.js'] = [
                staticDir + '/templates.js',
                jsDir + '/**/*.js'
            ];
            grunt.config.set('uglify.plugin_' + pluginName, {
                files: files
            });
            grunt.config.set('watch.js_' + pluginName, {
                files: [jsDir + '/**/*.js'],
                tasks: ['uglify:plugin_' + pluginName]
            });
            defaultTasks.push('uglify:plugin_' + pluginName);
        }

        var extraDir = pluginDir + '/web_client/extra';
        if (fs.existsSync(extraDir)) {
            grunt.config.set('copy.plugin_' + pluginName, {
                expand: true,
                cwd: pluginDir + '/web_client',
                src: ['extra/**'],
                dest: staticDir
            });
            grunt.config.set('watch.copy_' + pluginName, {
                files: [extraDir + '/**/*'],
                tasks: ['copy:plugin_' + pluginName]
            });
            defaultTasks.push('copy:plugin_' + pluginName);
        }

        // Handle external grunt targets specified for the plugin
        var pluginDescription = grunt.file.readJSON(pluginDir + '/plugin.json');
        if (pluginDescription.hasOwnProperty('grunt')) {
            var pluginGruntCfg = pluginDescription.grunt;

            // Merge plugin Grunt file
            require('./' + pluginDir + '/' + pluginGruntCfg.file)(grunt);

            // Register default targets
            pluginGruntCfg.defaultTargets.forEach(function (defaultTarget) {
                defaultTasks.push(defaultTarget);
            });
        }
    };

    // Glob for front-end plugins and configure each one to build
    var pluginDirs = grunt.file.expand('plugins/*');

    if (!fs.existsSync('clients/web/static/built/plugins')) {
        fs.mkdirSync('clients/web/static/built/plugins');
    }

    pluginDirs.forEach(function (pluginDir) {
        if (fs.existsSync(pluginDir + '/web_client')) {
            configurePlugin(pluginDir);
        }
    });

    grunt.loadNpmTasks('grunt-shell');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-jade');
    grunt.loadNpmTasks('grunt-contrib-stylus');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-copy');

    grunt.registerTask('swagger-ui', 'Build swagger front-end requirements.', function () {
        var buffer = fs.readFileSync('clients/web/src/templates/swagger/swagger.jadehtml');

        var fn = jade.compile(buffer, {
            client: false
        });
        fs.writeFileSync('clients/web/static/built/swagger/swagger.html', fn({
            staticRoot: staticRoot
        }));
    });

    grunt.registerTask('test-env-html', 'Build the phantom test html page.', function () {
        var buffer = fs.readFileSync('clients/web/test/testEnv.jadehtml');
        var globs = grunt.config('uglify.app.files')['clients/web/static/built/app.min.js'];
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
                '/clients/web/static/built/app.min.css'
            ],
            jsFiles: inputs,
            staticRoot: staticRoot,
            apiRoot: apiRoot
        }));
    });

    // This task should be run once manually at install time.
    grunt.registerTask('setup', 'Initial install/setup tasks', function () {
        // If the local config file doesn't exist, we make it
        var confDir = 'girder/conf';
        if (!fs.existsSync(confDir + '/girder.local.cfg')) {
            fs.writeFileSync(
                confDir + '/girder.local.cfg',
                fs.readFileSync(confDir + '/girder.dist.cfg')
            );
            console.log('Created local config file.');
        }
    });

    grunt.registerTask('build-js', [
        'jade',
        'uglify:app',
        'shell:readServerConfig',
        'test-env-html'
    ]);
    grunt.registerTask('init', [
        'setup',
        'uglify:libs',
        'copy:swagger',
        'shell:readServerConfig',
        'swagger-ui'
    ]);
    grunt.registerTask('docs', ['shell:sphinx']);
    grunt.registerTask('default', defaultTasks);
};
