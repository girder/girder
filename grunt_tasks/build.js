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
const GoogleFontsPlugin = require('google-fonts-webpack-plugin');

const isTrue = (str) => !!str && !['false', 'off', '0'].includes(str.toString().toLowerCase());

module.exports = function (grunt) {
    // Get and validate options
    const progress = !isTrue(grunt.option('no-progress'));
    const isWatch = isTrue(grunt.option('watch'));
    const pollingWatch = isTrue(process.env.WATCH_USEPOLLING);
    const isDev = grunt.config.get('environment') === 'dev' || isWatch;

    // Set some environment variables
    if (!process.env.NODE_ENV) {
        // This is not explicitly used for anything in Girder, but some Npm packages may respect it.
        // Babel will also fall back to using this if BABEL_ENV is not defined.
        process.env.NODE_ENV = isDev ? 'development' : 'production';
    }

    // Load the global webpack config
    const webpackConfig = require('./webpack.config.js');
    const updateWebpackConfig = _.partial(
        extendify({
            inPlace: true,
            isDeep: false,
            arrays: 'concat'
        }),
        webpackConfig
    );

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

        // Add coverage support (via Istanbul) to Babel
        const istanbulPlugin = require.resolve('babel-plugin-istanbul');
        _.each(webpackConfig.module.rules, (rule) => {
            _.each(_.where(rule.use, {loader: 'babel-loader'}), (useEntry) => {
                useEntry.options.plugins = [
                    [istanbulPlugin, {
                        exclude: ['**/*.pug', '**/*.jade', 'node_modules/**/*']
                    }]
                ];
            });
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
                new webpack.optimize.UglifyJsPlugin({
                    compress: {
                        warnings: false
                    },
                    output: {
                        comments: false
                    }
                })
            ]
        });
    }

    // Add extra config options for grunt-webpack
    updateWebpackConfig({
        progress: progress
    });

    const paths = require('./webpack.paths.js');

    grunt.config.merge({
        webpack: {
            options: webpackConfig,
            core_lib: {
                entry: {
                    girder_lib: [paths.web_src]
                },
                output: {
                    library: '[name]'
                },
                plugins: [
                    // Remove this if it turns out we don't want to use it for every bundle target.
                    new webpack.DllPlugin({
                        path: path.join(paths.web_built, '[name]-manifest.json'),
                        name: '[name]'
                    }),
                    new ExtractTextPlugin({
                        filename: '[name].min.css',
                        allChunks: true
                    }),
                    new GoogleFontsPlugin({
                        filename: 'googlefonts.css',
                        fonts: [{
                            family: 'Open Sans',
                            variants: ['regular', '700', 'italic', '700italic']
                        }]
                    })
                ]
            },
            core_app: {
                entry: {
                    girder_app: [path.join(paths.web_src, 'main.js')]
                },
                plugins: [
                    new webpack.DllReferencePlugin({
                        context: '.',
                        manifest: path.join(paths.web_built, 'girder_lib-manifest.json')
                    }),
                    new ExtractTextPlugin({
                        filename: '[name].min.css',
                        allChunks: true
                    })
                ]
            }
        },
        default: {
            build: {
                dependencies: ['version-info']
            }
        }
    });

    // Need an alias that can be used as a dependency (for testing). It will then trigger dev or
    // prod based on options passed
    grunt.registerTask('build', 'Build the web client.', [
        'webpack:core_lib',
        'webpack:core_app'
    ]);
};
