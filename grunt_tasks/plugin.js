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
    var webpackPlugins = require('./webpack.plugins.js');

    var configurePlugins = grunt.option('configure-plugins');
    var plugins = grunt.option('plugins');

    if (grunt.option('all-plugins')) {
        grunt.fail.warn(
            'The --all-plugins option no longer works, use `girder-install web --all-plugins` instead.');
    }

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

    if (!plugins.length && !configurePlugins.length) {
        return;
    }

    require('colors');

    grunt.config.merge({
        default: {
            plugin: {}
        }
    });

    /**
     * Collect dependencies from a package.json-like object.
     */
    function getDependencies(obj, fields, deps) {
        deps = deps || {};
        fields = fields || ['dependencies'];

        _.each(fields, function (field) {
            _.extend(deps, obj[field]);
        });
        return deps;
    }

    /**
     * Run npm install in the given prefix directory.
     *
     * @param {object} [deps]
     *   A dependency -> version mapping in the same syntax provided
     *   in a package.json file.
     *
     * @param {string} [prefix]
     *   The `--prefix` argument to the npm command.
     */
    function npmInstall(deps, prefix) {
        var args = [];

        if (prefix) {
            args = ['--prefix', prefix];
        }
        args = args.concat(['--color=always', 'install', '--no-save']);

        if (deps) {
            args = args.concat(
                _.map(deps, function (version, dep) {
                    return dep + '@' + version;
                })
            );
        }

        var child = child_process.spawnSync('npm', args, {
            stdio: 'inherit'
        });

        if (child.status !== 0) {
            grunt.fail.fatal(`"npm ${args.join(' ')}" failed`);
        }
    }

    /**
     * Handle a request for extra dependencies.  Those provided will
     * be stored in the grunt config object and installed in a task
     * added after all plugins have been configured.
     *
     * @param {object} deps
     *   A dependency -> version mapping in the same syntax provided
     *   in a package.json file.  If no object is given, it will fall
     *   back to the default behavior of `npm install` executed in
     *   the given path.
     *
     * @param {string} [prefix]
     *   The path where the packages will be installed.  By default,
     *   this will be the main girder directory.
     */
    function addDependencies(deps, prefix) {
        var config = {};

        if (prefix) {
            config.local = {[prefix]: deps};
        } else {
            config.global = deps;
        }

        grunt.config.merge({
            'npm-install-plugins': config
        });
    }

    /**
     * This inspects the plugin directory to configure installation of external
     * dependencies that must by installed via npm prior to building the
     * plugin.  There are several cases that this handles:
     *
     *   1. `package.json` in the plugin directory
     *   2. `plugin.json` dependencies installed to a custom prefix
     *   3. `plugin.json` dependencies installed to girder's prefix
     *   4. `plugin.json` grunt dependencies installed into girder's prefix
     *
     * Cases (1) and (2) are handled by running a custom invocation `npm install`
     * for each plugin.  For cases (3) and (4), the dependency lists are aggregated
     * and installed in a single invocation for all plugins.  This is done for two
     * reasons: it reduces the number of time `npm install` is executed (which is
     * slow) and it eliminates the problem of autopruning the `node_modules`
     * directory by npm@5.
     *
     * @param {string} pluginName
     *   The name of the plugin.
     * @param {string} pluginDir
     *   The path to the plugin's directory.
     * @param {object} pluginConfig
     *   The plugin config object.
     */
    function processPluginDependencies(pluginName, pluginDir, pluginConfig) {
        var npmConfig = pluginConfig.npm || {};
        var fields, npmFile, prefix, deps;

        // get dependencies from the plugin config object
        deps = getDependencies(npmConfig);

        // `npm.install` is a shortcut to installing directly from package.json
        if (npmConfig.install) {
            npmConfig.file = 'package.json';
            npmConfig.fields = ['dependencies'];
        }

        // get dependencies from a package.json file
        if (npmConfig.file) {
            npmFile = path.resolve(pluginDir, npmConfig.file);
            fields = npmConfig.fields || [
                'devDependencies', 'dependencies', 'optionalDependencies'
            ];

            grunt.log.writeln('  >> Loading NPM dependencies from: ' + npmFile);
            grunt.log.writeln('  >> Using fields: ' + fields.join(', '));

            getDependencies(require(npmFile), fields, deps);
        }

        if (npmConfig.install) {
            /*
             * Case 1:
            */
            prefix = path.resolve(pluginDir, 'package.json');
            grunt.log.writeln('  >> Installing NPM dependencies in-place from: ' + prefix);
            addDependencies({}, prefix);
        }

        // The configuration for cases 2 and 3 are mutually exclusive
        if (npmConfig.localNodeModules) {
            /*
             * Case 2:
             */
            grunt.log.writeln(`  >> Installing NPM dependencies to dedicated directory: girder_plugin_${pluginName}/node_modules`);
            addDependencies(deps, getPluginLocalNodePath(pluginName));
            deps = {};
        } else {
            /*
             * Case 3:
             */
            grunt.verbose.writeln('  >> Installing NPM dependencies to Girder node_modules directory');
        }

        if (pluginConfig.grunt && pluginConfig.grunt.dependencies) {
            /*
             * Case 4:
             */
            deps = getDependencies(pluginConfig.grunt, null, deps);
        }

        // Add the collected dependencies to the global install list.
        addDependencies(deps);
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
        var webpackHelperFile = path.resolve(dir, (config.webpack && config.webpack.configHelper) || 'webpack.helper.js');
        var webpackHelper;
        if (fs.existsSync(webpackHelperFile)) {
            grunt.log.writeln(`  >> Loading webpack helper from ${webpackHelperFile}`);
            webpackHelper = require(webpackHelperFile);
        } else {
            grunt.verbose.writeln('  >> No webpack helper file found.');
            webpackHelper = (x) => x;
        }

        // Configure the output file; default to 'plugin.min.js' - Girder loads
        // files named "plugin.min.js" into the Girder web client at runtime, so
        // the user can control whether this is a "Girder client extension" or
        // just a standalone web client.
        var output = (config.webpack && config.webpack.output) || 'plugin';
        var deps = config.dependencies || [];
        var pluginNodeDir = path.join(getPluginLocalNodePath(plugin), 'node_modules');

        // Add webpack target and name resolution for this plugin if
        // web_client/main.js (or user-specified name) exists.
        var webClient = path.resolve(dir + '/web_client');
        var mains = (config.webpack && config.webpack.main) || {};

        if (_.isString(mains)) {
            // If main was specified as a string, convert to an object
            mains = {
                [output]: mains
            };
        } else if (_.isEmpty(mains)) {
            // By default, use web_client/main.js if it exists.
            var mainJs = path.resolve(webClient, 'main.js');

            if (fs.existsSync(mainJs)) {
                mains = {
                    [output]: mainJs
                };
            }
        }

        _.each(mains, (main, output) => {
            if (!path.isAbsolute(main)) {
                main = path.resolve(dir, main);
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
                            }
                        }
                    }
                }
            };

            if (buildPlugin) {
                configOpts.webpack[`${output}_${plugin}`] = {
                    entry: {
                        [helperConfig.pluginEntry]: [main]
                    },
                    module: {
                        // We set these since webpack.helper.js functions may
                        // expect these properties to be defined.
                        loaders: [],
                        rules: []
                    },
                    output: {
                        path: path.join(grunt.config.get('builtPath'), 'plugins', plugin),
                        filename: `${output}.min.js`,
                        library: `girder_plugin_${plugin}`
                    },
                    resolve: {
                        alias: {
                            // Make sure we use the core jquery rather than pulling one
                            // from a plugin's local node modules. Multiple jquery versions
                            // breaks due to use of side effects for jquery plugins.
                            'jquery': path.resolve(paths.node_modules, 'jquery')
                        },
                        modules: [
                            pluginNodeDir,
                            path.resolve(dir, 'node_modules'),
                            paths.node_modules
                        ]
                    },
                    resolveLoader: {
                        modules: [
                            pluginNodeDir,
                            path.resolve(dir, 'node_modules'),
                            paths.node_modules
                        ]
                    },
                    plugins: [
                        // DllPlugin causes the plugin bundle to build a manifest so that
                        // downstream bundles can share its modules at runtime rather
                        // than copying them in statically.
                        new webpack.DllPlugin({
                            path: path.join(grunt.config.get('builtPath'), 'plugins', plugin, `${output}-manifest.json`),
                            name: `girder_plugin_${plugin}`
                        }),
                        // DllBootstrapPlugin allows the same plugin bundle to also
                        // execute an entry point at load time instead of just exposing symbols
                        // as a library.
                        new webpackPlugins.DllBootstrapPlugin({
                            [helperConfig.pluginEntry]: main
                        }),
                        // This plugin allows this bundle to dynamically link against girder's
                        // core library bundle.
                        new webpack.DllReferencePlugin({
                            context: '.',
                            manifest: path.join(grunt.config.get('builtPath'), 'girder_lib-manifest.json')
                        }),
                        // This plugin pulls the CSS out of the bundle and into a separate file.
                        new ExtractTextPlugin({
                            filename: `${output}.min.css`,
                            allChunks: true
                        })
                    ].concat(_.map(deps, (dep) => {
                        // This dynamically links the current plugin against its
                        // dependencies' bundles so they can share code.
                        return new webpack.DllReferencePlugin({
                            context: '.',
                            manifest: path.join(grunt.config.get('builtPath'), 'plugins', dep, 'plugin-manifest.json')
                        });
                    }))
                };
                configOpts.default = {
                    [`webpack:${output}_${plugin}`]: {
                        dependencies: ['build'] // plugin builds must run after core build
                    }
                };

                var baseConfig = configOpts.webpack[`${output}_${plugin}`];
                var newConfig = webpackHelper(baseConfig, helperConfig);
                if (_.has(newConfig.module, 'loaders')) {
                    if (!_.isEmpty(newConfig.module.loaders)) {
                        grunt.log.writeln(`  >> "module.loaders" is deprecated, use "module.rules" in ${webpackHelperFile} instead.`.yellow);
                        newConfig.module.rules = newConfig.module.rules || [];
                        newConfig.module.rules = newConfig.module.rules.concat(newConfig.module.loaders);
                    }
                    delete newConfig.module.loaders;
                }
                grunt.config.set(`webpack.${output}_${plugin}`, newConfig);
            }

            // If the plugin config has no webpack section, no defaultLoaders
            // property in the webpack section, or the defaultLoaders is
            // explicitly set to anything besides false, then augment the
            // webpack loader configurations with the plugin source directory.
            if (!config.webpack || config.webpack.defaultLoaders === undefined || config.webpack.defaultLoaders !== false) {
                var numLoaders = grunt.config.get('webpack.options.module.rules').length;
                for (var i = 0; i < numLoaders; i++) {
                    var selector = `webpack.options.module.rules.${i}.resource.include`;
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
            grunt.config.merge(configOpts);
        });

        if (config.grunt) {
            grunt.log.writeln((
                'Configuring plugin: ' + plugin + ' (custom Gruntfile)'
            ).bold);

            // load the plugin's gruntfile
            try {
                require(
                    path.resolve(dir, config.grunt.file || 'Gruntfile.js')
                )(grunt);
            } catch (e) {
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

        // process all external dependencies when building
        processPluginDependencies(plugin, dir, config);

        // Make sure the npm task runs before plugin build tasks
        grunt.config.set(`default.plugin:${plugin}`, {
            dependencies: ['npm-install-plugins']
        });

        // For backward compatibility, we still generate the old 'npm-install'
        // task as a noop, but ensure that the real npm install task is
        // executed as a prerequisite.
        grunt.config.set(`default.npm-install:${plugin}`, {
            dependencies: ['npm-install-plugins']
        });
    };

    // Configure the plugins that were requested via --configure-plugins in order
    configurePlugins.forEach(function (name) {
        configurePluginForBuilding(path.resolve(grunt.config.get('pluginDir'), name), false);
    });
    // Build the plugins that were requested via --plugins in order
    plugins.forEach(function (name) {
        configurePluginForBuilding(path.resolve(grunt.config.get('pluginDir'), name), true);
    });

    /**
     * This task is noop that exists for backwards compatibility in case any plugins rely
     * on its existence.
     * @deprecated: remove in v3
     */
    grunt.registerTask(
        'npm-install', 'Install plugin NPM dependencies (deprecated)',
        _.constant(true)
    );

    grunt.registerTask(
        'npm-install-plugins', 'Install all NPM dependencies',
        function () {
            var local = grunt.config.get('npm-install-plugins.local') || {};
            var global = grunt.config.get('npm-install-plugins.global') || {};

            if (!_.isEmpty(global)) {
                npmInstall(global);
            }
            _.each(local, npmInstall);
        }
    );

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

    grunt.config.set('default.npm-install-plugins', []);
};
