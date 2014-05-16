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
    var path = require('path');
    require('colors');

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
            grunt.fail.fatal('Invalid json from config_parse: ' + stdout);
        }
        callback();
    };

    // Builds all the static components for a given plugin
    var buildPlugin = function (pluginDir) {
        var pluginName = path.basename(pluginDir);
        var staticDir = 'clients/web/static/built/plugins/' + pluginName;

        console.log(('BUILDING PLUGIN: ' + pluginName).bold.underline);

        if (!fs.existsSync(staticDir)) {
            fs.mkdirSync(staticDir);
        }

        if (fs.existsSync(pluginDir + '/web_client/templates')) {
            var templates = grunt.file.expand(
                pluginDir + '/web_client/templates/**/*.jade');
            compileJade(templates, staticDir + '/templates.js');
        }

        var cssDir = pluginDir + '/web_client/stylesheets';
        if (fs.existsSync(cssDir)) {
            var files = {};
            files[staticDir + '/plugin.min.css'] = [cssDir + '/**/*.styl'];
            grunt.config.set('stylus.plugin_' + pluginName, {
                files: files
            });
            grunt.task.run('stylus:plugin_' + pluginName);
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
            grunt.task.run('uglify:plugin_' + pluginName);
        }
    };

    // Pass a "--env=<value>" argument to grunt. Default value is "dev".
    var environment = grunt.option('env') || 'dev';

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    // Project configuration.
    grunt.config.init({
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
                command: 'python config_parse.py girder/conf/local.server.cfg',
                options: {
                    callback: setServerConfig
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
                        'clients/web/lib/js/bootstrap.min.js',
                        'clients/web/lib/js/bootstrap-switch.min.js',
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
            swagger: {
                files: ['clients/web/src/templates/swagger/swagger.jadehtml'],
                tasks: ['swagger-ui'],
                options: {failOnError: false}
            },
            sphinx: {
                files: ['docs/*.rst'],
                tasks: ['docs'],
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
        fs.writeFileSync('clients/web/static/built/swagger/swagger.html', fn({staticRoot: staticRoot}));
    });


    // Compile a set of jade templates into a single js file
    var compileJade = function (inputFiles, outputFile) {
        var jade = require('jade');

        fs.writeFileSync(outputFile, '\nvar jade=jade||{};jade.templates=jade.templates||{};\n');

        inputFiles.forEach(function (filename, i) {
            var buffer = fs.readFileSync(filename);
            var basename = path.basename(filename, '.jade');
            console.log('Compiling template: ' + basename.magenta);

            var fn = jade.compile(buffer, {
                client: true,
                compileDebug: false
            });

            var jt = "\njade.templates['" + basename + "']=" + fn.toString() + ';';
            fs.appendFileSync(outputFile, jt);
        });
        console.log('Wrote ' + inputFiles.length + ' templates into ' + outputFile);
    };

    // Build the core jade templates into javascript
    grunt.registerTask('jade', 'Build the templates', function () {
        var config = grunt.config.get('jade');
        var inputFiles = grunt.file.expand(config.inputDir + '/**/*.jade');
        var outputFile = config.outputFile;

        compileJade(inputFiles, outputFile);
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
                console.log('Created config ' + local.magenta + '.');
            }
        });
    });

    grunt.registerTask('plugins', 'Build static content for plugins', function () {
        var pluginDirs = grunt.file.expand('plugins/*');

        if (!fs.existsSync('clients/web/static/built/plugins')) {
            fs.mkdirSync('clients/web/static/built/plugins');
        }

        pluginDirs.forEach(function (pluginDir) {
            if (fs.existsSync(pluginDir + '/web_client')) {
                buildPlugin(pluginDir);
            }
        });
    });

    grunt.registerTask('build-js', ['shell:readServerConfig', 'jade', 'uglify:app', 'plugins']);
    grunt.registerTask('init', ['setup', 'uglify:libs', 'copy:swagger', 'shell:readServerConfig', 'swagger-ui']);
    grunt.registerTask('docs', ['shell:sphinx']);
    grunt.registerTask('default', ['stylus', 'build-js']);
};
