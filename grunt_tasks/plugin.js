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

    var skipPlugins = grunt.option('skip-plugins');
    if (skipPlugins) {
        return;
    }

    /**
     * Adds configuration for plugin related multitasks:
     *
     *   * copy:plugin-<plugin name>
     *      Copies any other files that are served statically
     */
    var configurePlugin = function (plugin) {
        var pluginTarget = 'plugin-' + plugin,
            pluginPath = path.resolve(grunt.config.get('pluginDir'), plugin),
            staticPath = path.resolve(grunt.config.get('staticDir'), 'built', 'plugins', plugin),
            cfg = {
                copy: {},
                default: {},
                plugin: {}
            };

        // create the plugin's build directory under the web-root
        grunt.file.mkdir(staticPath);

        // TODO: this could be moved to Webpack using kevlened/copy-webpack-plugin
        cfg.copy[pluginTarget] = {
            files: [{
                expand: true,
                cwd: pluginPath + '/web_client',
                src: ['extra/**'],
                dest: staticPath
            }]
        };

        // the task 'plugin:<plugin name>' is a task alias to run all
        // of the main tasks defined above and possibly more if
        // the plugin itself appends tasks to this array
        cfg.plugin[plugin] = {
            tasks: [
                'copy:' + pluginTarget
            ]
        };

        grunt.config.merge(cfg);
    };

    grunt.config.merge({
        default: {
            plugin: {}
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

            function addDependencies (deps) {
                // install any additional npm packages during init
                npm = (
                    _(deps || [])
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
            }

            if (config.npm) {
                addDependencies(config.npm.dependencies);
            }

            if (config.grunt) {
                grunt.log.writeln((
                    'Found plugin: ' + plugin + ' (custom Gruntfile)'
                ).bold);

                addDependencies(config.grunt.dependencies);

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
