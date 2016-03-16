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
 * Define tasks related to loading, configuring, and building plugins.
 */
module.exports = function (grunt) {
    var _ = require('underscore');
    var fs = require('fs');
    var path = require('path');

    /**
     * Adds configuration for plugin related multitasks:
     *
     *   * shell:plugin-<plugin name>
     *      Runs npm install in the plugin directory
     *   * jade:plugin-<plugin name>
     *      Compiles jade templates into the plugin's template.js
     *   * stylus:plugin-<plugin name>
     *      Compiles stylus files into the plugin's main css file
     *   * uglify:plugin-<plugin name>
     *      Compiles all javascript sources into the plugin's main js file
     *   * copy:plugin-<plugin name>
     *      Copies any other files that are served statically
     *
     *  This will also add watch tasks for each of the above.
     */
    var configurePlugin = function (plugin) {
        var pluginTarget = 'plugin-' + plugin,
            pluginPath = path.resolve(grunt.config.get('pluginDir'), plugin),
            staticPath = path.resolve(
                grunt.config.get('staticDir'), 'built', 'plugins', plugin
            ),
            packageJson = path.resolve(pluginPath, 'package.json'),
            cfg = {
                shell: {},
                jade: {},
                stylus: {},
                uglify: {},
                copy: {},
                watch: {},
                default: {},
                plugin: {},
                'plugin-install': {}
            };

        // create the plugin's build directory under the web-root
        grunt.file.mkdir(staticPath);

        cfg.shell[pluginTarget] = {
            command: function () {
                // do nothing if it has no package.json file
                if (!fs.existsSync(packageJson)) {
                    grunt.verbose.writeln('Skipping npm install');
                    return 'true';
                }
                return 'npm install';
            },
            options: {
                execOptions: {
                    cwd: pluginPath
                }
            },
            src: [packageJson]
        };
        cfg.watch[pluginTarget + '-shell'] = {
            files: [packageJson],
            tasks: ['shell:' + pluginTarget]
        };

        cfg.jade[pluginTarget] = {
            files: [{
                src: [pluginPath + '/web_client/templates/**/*.jade'],
                dest: staticPath + '/templates.js'
            }]
        };
        cfg.watch[pluginTarget + '-jade'] = {
            files: [pluginPath + '/web_client/templates/**/*.jade'],
            tasks: ['jade:' + pluginTarget]
        };

        cfg.stylus[pluginTarget] = {
            files: [{
                src: [pluginPath + '/web_client/stylesheets/**/*.styl'],
                dest: staticPath + '/plugin.min.css'
            }]
        };
        cfg.watch[pluginTarget + '-stylus'] = {
            files: [pluginPath + '/web_client/stylesheets/**/*.styl'],
            tasks: ['stylus:' + pluginTarget]
        };

        cfg.uglify[pluginTarget] = {
            files: [{
                src: [
                    pluginPath + '/web_client/js/**/*.js',
                    staticPath + '/templates.js'
                ],
                dest: staticPath + '/plugin.min.js'
            }]
        };
        cfg.watch[pluginTarget + '-uglify'] = {
            files: [
                pluginPath + '/web_client/js/**/*.js',
                staticPath + '/templates.js'
            ],
            tasks: ['uglify:' + pluginTarget]
        };

        cfg.copy[pluginTarget] = {
            files: [{
                expand: true,
                cwd: pluginPath + '/web_client',
                src: ['extra/**'],
                dest: staticPath
            }]
        };
        cfg.watch[pluginTarget + '-copy'] = {
            files: [pluginPath + '/extra/**'],
            tasks: ['copy:' + pluginTarget]
        };

        // the task 'plugin:<plugin name>' is a task alias to run all
        // of the main tasks defined above and possibly more if
        // the plugin itself appends tasks to this array
        cfg.plugin[plugin] = {
            tasks: [
                'jade:' + pluginTarget,
                'stylus:' + pluginTarget,
                'uglify:' + pluginTarget,
                'copy:' + pluginTarget
            ]
        };

        // finally, 'plugin-install:<plugin name>' is a task alias for
        // tasks that are run with `grunt init`
        cfg['plugin-install'][plugin] = {
            tasks: ['shell:' + pluginTarget]
        };

        grunt.config.merge(cfg);
    };

    grunt.config.merge({
        default: {
            plugin: {}
        },
        init: {
            'plugin-install': {}
        }
    });

    /**
     * Insert individual plugins into the plugin meta task.
     */
    grunt.file.expand(grunt.config.get('pluginDir') + '/*')
        .forEach(function (dir) {
            var plugin = path.basename(dir);
            var json = path.resolve(dir, 'plugin.json');
            var yml = path.resolve(dir, 'plugin.yml');
            var config = {}, npm;

            grunt.log.writeln((
                'Found plugin: ' + plugin
            ).bold);

            if (fs.existsSync(json)) {
                config = grunt.file.readYAML(json);
            }
            if (fs.existsSync(yml)) {
                config = grunt.file.readYAML(yml);
            }

            var doAutoBuild = (
               !_.isObject(config.grunt) ||
                _.isUndefined(config.grunt.autobuild) ||
                _.isNull(config.grunt.autobuild) ||
              !!config.grunt.autobuild
            );

            if (doAutoBuild) {
                // merge in configuration for the main plugin build tasks
                configurePlugin(plugin);
            }

            if (config.grunt) {
                grunt.log.writeln((
                    'Found plugin: ' + plugin + ' (custom Gruntfile)'
                ).bold);

                // install any additional npm packages during init
                npm = (
                    _(config.grunt.dependencies || [])
                        .map(function (version, dep) {
                            // escape any periods in the dependency version so
                            // that grunt.config.set does not descend on each
                            // version number component
                            var escapedVersion = version.replace(/\./g, '\\.');

                            return [
                                dep,
                                escapedVersion
                            ].join('@');
                        })
                );

                if (npm.length) {
                    grunt.config.set(
                        'init.npm-install:' + npm.join(':'), {}
                    );
                }

                // load the plugin's gruntfile
                try {
                    require(
                        path.resolve(dir, config.grunt.file || 'Gruntfile.js')
                    )(grunt);
                } catch (e) {
                    // the error can be safely ignored when doing `grunt init`
                    // otherwise a default task will most likely fail later on
                    // write out a warning to help the developers debug errors
                    grunt.log.writeln((
                        'Failed to load ' + plugin + '/' + (config.grunt.file || 'Gruntfile.js') + ':'
                    ).yellow);
                    grunt.log.writeln('>>> ' + e.toString().split('\n').join('\n>>> ').yellow);
                }

                // add default targets
                _(config.grunt.defaultTargets || []).each(function (target) {
                    grunt.config.set('default.' + target, {});
                });
            }
        });

    /**
     * Create a multi-task for all plugin npm installs.
     */
    grunt.registerMultiTask(
        'plugin-install',
        'Run npm install in plugin directories',
        function () {
            var plugin = this.target,
                tasks = 'plugin-install.' + plugin + '.tasks';

            this.requiresConfig(tasks);

            // queue the install tasks
            grunt.config.get(tasks).forEach(function (task) {
                grunt.task.run(task);
            });
        }
    );

    /**
     * Register a "meta" task that will configure and run other tasks
     * to build a plugin.  Keys in the config for this task should be the
     * directory of the plugin within the base plugins path.
     */
    grunt.registerMultiTask('plugin', 'Build and configure plugins', function () {
        var plugin = this.target,
            tasks = 'plugin.' + plugin + '.tasks';

        this.requiresConfig('pluginDir', tasks);

        // queue the build tasks
        grunt.config.get(tasks).forEach(function (task) {
            grunt.task.run(task);
        });
    });
};
