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
    var child_process = require('child_process'); // eslint-disable-line camelcase

    var ExtractTextPlugin = require('extract-text-webpack-plugin');
    var webpack = require('webpack');
    var paths = require('./webpack.paths.js');

    var buildAll = grunt.option('all-plugins');
    var configurePlugins = grunt.option('configure-plugins');
    var plugins = grunt.option('plugins');

    if (_.isString(plugins) && plugins) {
        plugins = plugins.split(',');
    } else {
        plugins = [];
    }

    if (_.isString(configurePlugins) && configurePlugins) {
        configurePlugins = configurePlugins.split(',');
    } else {
        configurePlugins = [];
    }

    if (!buildAll && !plugins.length && !configurePlugins.length) {
        return;
    }

    require('colors');

    grunt.config.merge({
        default: {
            plugin: {}
        }
    });

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

    var getPluginLocalNodePath = function (plugin) {
        return path.resolve(path.join('node_modules', `girder_plugin_${plugin}`));
    };

    var configurePluginForBuilding = function (dir, buildPlugin) {
        var plugin = path.basename(dir);
        var json = path.resolve(dir, 'plugin.json');
        var yml = path.resolve(dir, 'plugin.yml');
        var config = {};
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

        var buildText = `build=${buildPlugin ? 'ON'.green : 'OFF'.red}`;
        grunt.log.writeln(`Configuring plugin ${plugin.magenta} (${cfgFile}, ${buildText})`);

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

        // Find the plugin's webpack helper file; default to the identity
        // function.
        var webpackHelperFile = path.resolve(dir, config.webpack && config.webpack.configHelper || 'webpack.helper.js');
        var webpackHelper;
        if (fs.existsSync(webpackHelperFile)) {
            grunt.log.writeln(`  >> Loading webpack helper from ${webpackHelperFile}`);
            webpackHelper = require(webpackHelperFile);
        } else {
            grunt.verbose.writeln('  >> No webpack helper file found.');
            webpackHelper = x => x;
        }

        // Configure the output file; default to 'plugin.min.js' - Girder loads
        // files named "plugin.min.js" into the Girder web client at runtime, so
        // the user can control whether this is a "Girder client extension" or
        // just a standalone web client.
        var output = config.webpack && config.webpack.output || 'plugin';

        var pluginNodeDir = path.join(getPluginLocalNodePath(plugin), 'node_modules');

        // Add webpack target and name resolution for this plugin if
        // web_client/main.js (or user-specified name) exists.
        var webClient = path.resolve(dir + '/web_client');
        var mains = config.webpack && config.webpack.main || {};

        if (_.isString(mains)) {
            // If main was specified as a string, convert to an object
            mains = {
                [output]: mains
            };
        } else if (_.isEmpty(mains)) {
            // By default, use web_client/main.js if it exists.
            var mainJs = path.join(webClient, 'main.js');

            if (fs.existsSync(mainJs)) {
                mains = {
                    [output]: mainJs
                };
            }
        }

        _.each(mains, (main, output) => {
            if (!path.isAbsolute(main)) {
                main = path.join(dir, main);
            }
            if (!fs.existsSync(main)) {
                throw new Error(`Entry point file ${main} not found.`);
            }

            var helperConfig = {
                plugin,
                output,
                main,
                pluginEntry: `plugins/${plugin}/${output}`,
                pluginDir: dir,
                nodeDir: pluginNodeDir
            };

            var configOpts = {
                webpack: {
                    options: {
                        // Add an import alias to the global config for this plugin
                        resolve: {
                            alias: {
                                [`girder_plugins/${plugin}/node`]: pluginNodeDir,
                                [`girder_plugins/${plugin}`]: webClient
                            },
                            modules: [
                                path.resolve(process.cwd(), 'node_modules'),
                                pluginNodeDir
                            ]
                        },
                        resolveLoader: {
                            modules: [
                                path.resolve(process.cwd(), 'node_modules'),
                                pluginNodeDir
                            ]
                        }
                    }
                }
            };

            if (buildPlugin) {
                configOpts.webpack[`${output}_${plugin}`] = {
                    entry: {
                        [helperConfig.pluginEntry]: [main]
                    },
                    output: {
                        path: path.join(paths.web_built, 'plugins', plugin),
                        filename: `${output}.min.js`
                    },
                    resolve: {
                        modules: [
                            path.resolve(dir, 'node_modules')
                        ]
                    },
                    resolveLoader: {
                        modules: [
                            path.resolve(dir, 'node_modules')
                        ]
                    },
                    plugins: [
                        new webpack.DllReferencePlugin({
                            context: '.',
                            manifest: path.join(paths.web_built, 'girder_lib-manifest.json')
                        }),
                        new ExtractTextPlugin({
                            filename: `${output}.min.css`,
                            allChunks: true
                        })
                    ]
                };
                configOpts.default = {
                    [`webpack:${output}_${plugin}`]: {
                        dependencies: ['build'] // plugin builds must run after core build
                    }
                };
            }
            grunt.config.merge(configOpts);

            // If the plugin config has no webpack section, no defaultLoaders
            // property in the webpack section, or the defaultLoaders is
            // explicitly set to anything besides false, then augment the
            // webpack loader configurations with the plugin source directory.
            if (!config.webpack || config.webpack.defaultLoaders === undefined || config.webpack.defaultLoaders !== false) {
                var numLoaders = grunt.config.get('webpack.options.module.loaders').length;
                for (var i = 0; i < numLoaders; i++) {
                    var selector = 'webpack.options.module.loaders.' + i + '.include';
                    var loaders = grunt.config.get(selector) || [];
                    var pluginPath = path.resolve(dir);
                    var realPath = fs.realpathSync(dir);
                    var loaderIncludes = [pluginPath];

                    // We add the plugin path to the include list for the loaders, and also
                    // add the realpath (i.e. following symlinks) to workaround an issue where
                    // webpack doesn't resolve symlinked include directories correctly.
                    if (realPath !== pluginPath) {
                        loaderIncludes.push(realPath);
                    }

                    grunt.config.set(selector, loaders.concat(loaderIncludes));
                }
            }

            var newConfig = webpackHelper(grunt.config.getRaw('webpack.options'), helperConfig);
            grunt.config.set('webpack.options', newConfig);
        });

        grunt.registerTask('npm-install', 'Install plugin NPM dependencies', function (plugin, localNodeModules) {
            var args, child;
            if (localNodeModules === 'install') {
                args = ['--color=always', 'install'];

                child = child_process.spawnSync('npm', args, {
                    cwd: path.resolve(dir),
                    stdio: 'inherit'
                });

                return child.status === 0;
            }

            // Start building the list of arguments to the NPM executable.
            //
            // We want color output embedded in the Grunt output.
            args = ['--color=always'];

            // If the plugin requested to install the dependencies in its own
            // dedicated directory, set the prefix option.
            if (localNodeModules === 'true') {
                args = args.concat(['--prefix', getPluginLocalNodePath(plugin)]);
            }

            // Get the list of the packages to install and append them to the
            // args object.
            var modules = Array.prototype.slice.call(arguments, 2);
            args = args.concat(['install'], modules);

            // Launch the child process.
            child = child_process.spawnSync('npm', args, {
                stdio: 'inherit'
            });

            return child.status === 0;
        });

        function addDependencies(deps, localNodeModules) {
            if (arguments.length === 0) {
                grunt.config.set('default.npm-install:' + plugin + ':install', {});
                return;
            }

            // install any additional npm packages during init
            var npm = (
                _(deps || {})
                    .map(function (version, dep) {
                        return [
                            dep.replace(':', '\\:'),
                            version.replace(':', '\\:')
                        ].join('@');
                    })
            );

            if (npm.length) {
                grunt.config.set('default.npm-install:' + plugin + ':' + !!localNodeModules + ':' + grunt.config.escape(npm.join(':')), {});
            }
        }

        if (config.npm && config.npm.install) {
            grunt.log.writeln('  >> Installing NPM dependencies in-place from: ' + path.resolve(dir, 'package.json'));
            addDependencies();
        } else if (config.npm) {
            var modules = {};

            // If the config contains a "file" section, load NPM dependencies
            // from it.
            if (config.npm.file) {
                var npmFile = require(path.resolve(dir, config.npm.file));
                var fields = config.npm.fields || ['devDependencies', 'dependencies', 'optionalDependencies'];

                grunt.log.writeln('  >> Loading NPM dependencies from: ' + config.npm.file);
                grunt.log.writeln('  >> Using fields: ' + fields.join(', '));

                fields.forEach(function (field) {
                    _.each(npmFile[field] || {}, function (version, dep) {
                        modules[dep] = version;
                    });
                });
            }

            // Additionally add any extra dependencies found in the
            // "dependencies" property.
            if (config.npm.dependencies) {
                if (config.npm.file) {
                    grunt.log.writeln('  >> Loading additional NPM dependencies');
                } else {
                    grunt.log.writeln('  >> Loading NPM dependencies');
                }

                _.each(config.npm.dependencies, function (version, dep) {
                    modules[dep] = version;
                });
            }

            if (config.npm.localNodeModules) {
                grunt.log.writeln(`  >> Installing NPM dependencies to dedicated directory: node_modules_${plugin}`);
            } else {
                grunt.verbose.writeln('  >> Installing NPM dependencies to Girder node_modules directory');
            }

            // Invoke the npm installation task.
            addDependencies(modules, config.npm.localNodeModules);
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

    // Glob for plugins and configure each one to be built
    if (buildAll) {
        // Glob for plugins and configure each one to be built
        grunt.file.expand(grunt.config.get('pluginDir') + '/*').forEach(function (dir) {
            configurePluginForBuilding(path.resolve(dir), true);
        });
    } else {
        // Configure only the plugins that were requested via --configure-plugins
        configurePlugins.forEach(function (name) {
            configurePluginForBuilding(path.resolve(grunt.config.get('pluginDir'), name), false);
        });
        // Build only the plugins that were requested via --plugins
        plugins.forEach(function (name) {
            configurePluginForBuilding(path.resolve(grunt.config.get('pluginDir'), name), true);
        });
    }

    /**
     * Register a "meta" task that will configure and run other tasks
     * to build a plugin. Keys in the config for this task should be the
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
