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

const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const GoogleFontsPlugin = require('google-fonts-webpack-plugin');

module.exports = function (grunt) {
    // Get and validate options
    const progress = !grunt.option('no-progress');
    const environment = grunt.config.get('environment');
    const isWatch = grunt.option('watch');

    // Set some environment variables
    if (!process.env.BABEL_ENV) {
        // https://babeljs.io/docs/usage/babelrc/#env-option
        process.env.BABEL_ENV = environment;
    }
    if (!process.env.NODE_ENV) {
        // https://stackoverflow.com/a/16979503
        process.env.NODE_ENV = environment;
    }

    // Load the global webpack config
    const webpackConfig = require('./webpack.config.js');

    // Extend the global webpack config options with environment-specific changes
    if (environment === 'dev') {
        webpackConfig.devtool = 'source-map';
        webpackConfig.cache = true;
        webpackConfig.plugins = webpackConfig.plugins.concat([
            new webpack.LoaderOptionsPlugin({
                minimize: false,
                debug: true
            })
        ]);
    } else {
        // "devtool" is off by default
        webpackConfig.cache = false;
        webpackConfig.plugins = webpackConfig.plugins.concat([
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
        ]);
    }
    if (isWatch) {
        // When "watch" is enabled for webpack, grunt-webpack will intelligently set its own options
        // for "keepalive" and "failOnError"
        webpackConfig.watch = true;
    }

    // Add extra config options for grunt-webpack
    webpackConfig.progress = progress;

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
                            family: 'Droid Sans',
                            variants: ['regular', '700']
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
        // The grunt-contrib-watch task can be used with webpack, as described here:
        // https://github.com/webpack/webpack-with-common-libs/blob/master/Gruntfile.js
        // BUT it is A LOT SLOWER than using the built-in watch options in grunt-webpack
        watch: {
            warn: {
                files: [],
                tasks: 'warnWatch',
                options: {
                    atBegin: true
                }
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

    // Warn about not using grunt-contrib-watch, use webpack:watch or grunt --watch instead
    grunt.registerTask('warnWatch', function () {
        grunt.log.warn('WARNING: the "watch" task will not build; run grunt --watch'.yellow);
    });
};
