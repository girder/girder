/**
 * Copyright 2016 Kitware Inc.
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

    var buildAll = grunt.option('all-plugins');
    var plugins = grunt.option('plugins');

    if (_.isString(plugins) && plugins) {
        plugins = plugins.split(',');
    } else if (!buildAll) {
        return;
    }

    /**
     * Adds configuration for plugin related multitasks:
     *
     *   * copy:plugin-<plugin name>
     *      Copies any other files that are served statically
     */
    var addMultitasks = function (plugin) {
        var pluginTarget = 'plugin-' + plugin,
            pluginPath = path.resolve(grunt.config.get('pluginDir'), plugin),
            staticPath = path.resolve(grunt.config.get('staticDir'), 'built', 'plugins', plugin),
            cfg = {};

        // create the plugin's build directory under the web-root
        grunt.file.mkdir(staticPath);

        // TODO: this could be moved to Webpack using kevlened/copy-webpack-plugin
        cfg.copy = {
            [pluginTarget]: {
                files: [{
                    expand: true,
                    cwd: pluginPath + '/web_client',
                    src: ['extra/**'],
                    dest: staticPath
                }]
            }
        };

        grunt.config.merge(cfg);
    };

    var configurePluginForBuilding = function (dir) {
        var plugin = path.basename(dir);
        var json = path.resolve(dir, 'plugin.json');
        var yml = path.resolve(dir, 'plugin.yml');
        var config = {}, npm;
        var cfgFile = 'no config file';

        if (!fs.statSync(dir).isDirectory()) {
            grunt.fail.warn('Plugin directory not found: ' + dir);
            return;
        }

        if (fs.existsSync(json)) {
            config = grunt.file.readYAML(json);
            cfgFile = 'plugin.json';
        } else if (fs.existsSync(yml)) {
            cfgFile = 'plugin.yml';
            config = grunt.file.readYAML(yml);
        }

        console.log(`Configuring plugin ${plugin.magenta} (${cfgFile})`);

        var doAutoBuild = (
            !_.isObject(config.grunt) ||
            _.isUndefined(config.grunt.autobuild) ||
            _.isNull(config.grunt.autobuild) ||
            !!config.grunt.autobuild
        );

        if (doAutoBuild) {
            // merge in configuration for the main plugin build tasks
            addMultitasks(plugin);
        }

        // Add webpack target and name resolution for this plugin if web_client/main.js exists
        var webClient = path.resolve(dir + '/web_client');
        var main =  webClient + '/main.js';
        if (fs.existsSync(main)) {
            grunt.config.merge({
                webpack: {
                    options: {
                        entry: {
                            [`plugins/${plugin}/plugin`]: main
                        },
                        resolve: {
                            alias: {
                                [`girder_plugins/${plugin}`]: webClient
                            }
                        }
                    }
                }
            });
        }

        function addDependencies(deps) {
            // install any additional npm packages during init
            npm = (
                _(deps || [])
                    .map(function (version, dep) {
                        return [
                            dep,
                            version
                        ].join('@');
                    })
            );

            if (npm.length) {
                grunt.config.set('default.npm-install:' + grunt.config.escape(npm.join(':')), {});
            }
        }

        if (config.npm) {
            addDependencies(config.npm.dependencies);
        }

        if (config.grunt) {
            grunt.log.writeln((
                'Configuring plugin: ' + plugin + ' (custom Gruntfile)'
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
    };

    if (buildAll) {
        // Glob for plugins and configure each one to be built
        grunt.file.expand(grunt.config.get('pluginDir') + '/*').forEach(function (dir) {
            configurePluginForBuilding(dir);
        });
    } else {
        // Build only the plugins that were requested via --plugins
        plugins.forEach(function (name) {
            configurePluginForBuilding(path.resolve(grunt.config.get('pluginDir'), name));
        });
    }
};
