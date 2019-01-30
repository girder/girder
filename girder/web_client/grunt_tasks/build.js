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

const path = require('path');
const process = require('process');

const _ = require('underscore');
const extendify = require('extendify');
const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const UglifyJsPlugin = require('uglifyjs-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

const webpackPlugins = require('./webpack.plugins.js');
const { version: girderVersion } = require('@girder/core/package.json');
const { getGitSha } = require('./git.js');

const isTrue = (str) => !!str && !['false', 'off', '0'].includes(str.toString().toLowerCase());

module.exports = function (grunt) {
    // Get and validate options
    const progress = !isTrue(grunt.option('no-progress'));
    const isWatch = isTrue(grunt.option('watch'));
    const pollingWatch = isTrue(process.env.WATCH_USEPOLLING);
    const isDev = grunt.config.get('environment') === 'dev' || isWatch;

    function injectIstanbulCoverage(config) {
        if (!isDev) {
            return;
        }
        const istanbulPlugin = require.resolve('babel-plugin-istanbul');
        _.each(config.module.rules, (rule) => {
            _.each(_.where(rule.use, {loader: 'babel-loader'}), (useEntry) => {
                useEntry.options.plugins = [
                    [istanbulPlugin, {
                        exclude: ['**/*.pug', '**/*.jade']
                    }]
                ];
            });
        });
    }

    // Set some environment variables
    if (!process.env.NODE_ENV) {
        // This is not explicitly used for anything in Girder, but some Npm packages may respect it.
        // Babel will also fall back to using this if BABEL_ENV is not defined.
        process.env.NODE_ENV = isDev ? 'development' : 'production';
    }

    // nyc will only instrument files whose *real* path is inside the working directory.  Because we
    // want to instrument files that could be symlinked into node_modules from outside the girder
    // web_client directory, we just set this to the system root.  There do not seem to be any
    // consequences to this beyond the path lookup performed in nyc.
    process.env.NYC_CWD = '/';

    // Load the global webpack config
    const webpackConfig = require('./webpack.config.js');
    const updateWebpackConfig = _.partial(
        extendify({
            inPlace: true,
            isDeep: true,
            arrays: 'concat'
        }),
        webpackConfig
    );
    const plugins = grunt.config.get('pkg.girder.plugins') || [];

    // Extend the global webpack config options with environment-specific changes
    if (isDev) {
        updateWebpackConfig({
            devtool: 'source-map',
            cache: true,
            plugins: [
                new webpack.LoaderOptionsPlugin({
                    minimize: false,
                    debug: true
                })
            ]
        });

        if (isWatch) {
            updateWebpackConfig({
                watch: true
                // When "watch" is enabled for webpack, grunt-webpack will intelligently set its own
                // options for "keepalive" and "failOnError"
            });
            if (pollingWatch) {
                updateWebpackConfig({
                    watchOptions: {
                        // For Girder's current number of files, 500ms is a reasonable polling
                        // interval to keep CPU utilization from going too high, particularly in a
                        // VM (where this option is most likely to be used)
                        poll: 500
                    }
                });
                // Chokidar is used internally for almost all file polling, so enable it globally
                // for other packages to potentially benefit too
                process.env.CHOKIDAR_USEPOLLING = 'TRUE';
                process.env.CHOKIDAR_INTERVAL = '500';
            }
        }
    } else {
        updateWebpackConfig({
            // "devtool" is off by default
            cache: false,
            plugins: [
                // https://github.com/webpack/webpack/issues/283
                // https://github.com/webpack/webpack/issues/2061#issuecomment-228932941
                // https://gist.github.com/sokra/27b24881210b56bbaff7#loader-options--minimize
                // but unclear and confusing as to how far it has been implemented
                new webpack.LoaderOptionsPlugin({
                    minimize: true,
                    debug: false
                }),
                new UglifyJsPlugin({
                    uglifyOptions: {
                        ecma: 6
                    }
                })
            ]
        });
    }

    // Inject environment variables
    updateWebpackConfig({
        plugins: [
            new webpack.EnvironmentPlugin({
                NODE_ENV: null,
                GIRDER_VERSION_RELEASE: girderVersion,
                GIRDER_VERSION_GIT: getGitSha(),
                GIRDER_VERSION_DATE: new Date().toISOString(),
            })
        ]
    });

    // Add extra config options for grunt-webpack
    updateWebpackConfig({
        progress: progress
    });

    // Set the publicPath based on Girder's static root
    updateWebpackConfig({
        output: {
            publicPath: path.join(grunt.config.get('staticUrl'), 'built/')
        }
    });

    // add coverage to all babel loader rules when in dev mode
    injectIstanbulCoverage(webpackConfig);

    grunt.config.merge({
        webpack: {
            options: webpackConfig,
            core_lib: {
                entry: {
                    girder_lib: [require.resolve('@girder/core')] // main is index.js
                },
                output: {
                    library: '[name]',
                    path: grunt.config.get('builtPath')
                },
                plugins: [
                    // Remove this if it turns out we don't want to use it for every bundle target.
                    new webpack.DllPlugin({
                        path: path.join(grunt.config.get('builtPath'), '[name]-manifest.json'),
                        name: '[name]'
                    }),
                    new ExtractTextPlugin({
                        filename: '[name].min.css',
                        allChunks: true
                    })
                ]
            },
            core_app: {
                entry: {
                    girder_app: [require.resolve('@girder/core/main.js')]
                },
                output: {
                    path: grunt.config.get('builtPath')
                },
                plugins: [
                    new webpack.DllReferencePlugin({
                        context: '.',
                        manifest: path.join(grunt.config.get('builtPath'), 'girder_lib-manifest.json')
                    }),
                    new ExtractTextPlugin({
                        filename: '[name].min.css',
                        allChunks: true
                    }),
                    new CopyWebpackPlugin([{
                        from: 'static/img/Girder_Favicon.png',
                        to: grunt.config.get('builtPath'),
                        toType: 'dir'
                    }])
                ]
            }
        },
        default: {
            build: {}
        }
    });

    // Get a list of entry points for each installed plugin.
    plugins.forEach(function (plugin) {
        const pluginDef = require(path.join(plugin, 'package.json'))['girderPlugin'];
        const name = pluginDef.name;
        const main = pluginDef.main;
        const babelRule = {
            resource: {
                test: /\.js$/,
                include: [path.resolve(`node_modules/${plugin}`)],
                exclude: new RegExp(`node_modules/${plugin}/node_modules`)
            },
            use: [{
                loader: 'babel-loader',
                options: {
                    presets: [require.resolve('babel-preset-env')],
                    cacheDirectory: true
                }
            }]
        };
        let pluginWebpackConfig = {
            entry: {
                [`plugins/${name}/plugin`]: [`${plugin}/${main}`]
            },
            output: {
                path: path.resolve(grunt.config.get('builtPath'), 'plugins', name),
                filename: 'plugin.min.js',
                library: `girder_plugin_${name}`
            },
            module: {
                rules: [babelRule]
            },
            plugins: [
                new webpack.DllPlugin({
                    path: path.join(grunt.config.get('builtPath'), 'plugins', name, 'plugin-manifest.json'),
                    name: `girder_plugin_${name}`
                }),
                // DllBootstrapPlugin allows the same plugin bundle to also
                // execute an entry point at load time instead of just exposing symbols
                // as a library.
                new webpackPlugins.DllBootstrapPlugin({
                    [`plugins/${name}/plugin`]: `${plugin}/${main}`
                }),
                // This plugin allows this bundle to dynamically link against girder's
                // core library bundle.
                new webpack.DllReferencePlugin({
                    context: '.',
                    manifest: path.join(grunt.config.get('builtPath'), 'girder_lib-manifest.json')
                }),
                // This plugin pulls the CSS out of the bundle and into a separate file.
                new ExtractTextPlugin({
                    filename: 'plugin.min.css',
                    allChunks: true
                }),
                // Copy assets from the "extras" directory.
                new CopyWebpackPlugin([{
                    context: path.resolve(`node_modules/${plugin}/extra`),
                    from: '**',
                    to: path.join(grunt.config.get('builtPath'), 'plugins', name, 'extra'),
                    toType: 'dir'
                }])
            ].concat(_.map(pluginDef.dependencies || [], (dep) => {
                return new webpack.DllReferencePlugin({
                    context: '.',
                    manifest: path.join(grunt.config.get('builtPath'), 'plugins', dep, 'plugin-manifest.json')
                });
            }))
        };
        injectIstanbulCoverage(pluginWebpackConfig);

        // allow the plugin to mutate its own webpack config
        if (pluginDef.webpack) {
            pluginWebpackConfig = require(path.join(plugin, pluginDef.webpack))(pluginWebpackConfig);
        }
        grunt.config.set(`webpack.plugin_${name}`, pluginWebpackConfig);

        // Make dependent plugins build before this one to create the DLL manifest.
        grunt.config.set(`default.webpack:plugin_${name}`, {
            dependencies: _.map(pluginDef.dependencies, (dep) => `webpack:plugin_${dep}`)
        });
    });

    // Need an alias that can be used as a dependency (for testing). It will then trigger dev or
    // prod based on options passed
    grunt.registerTask('build', 'Build the web client.', [
        'webpack:core_lib',
        'webpack:core_app'
    ]);
};
