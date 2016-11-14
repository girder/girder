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

var path = require('path');
var _ = require('underscore');
var noptFix = require('nopt-grunt-fix');

var webpack = require('webpack');
var webpackGlobalConfig = require('./webpack.config.js');
var paths = require('./webpack.paths.js');
var customWebpackPlugins = require('./webpack.plugins.js');

module.exports = function (grunt) {
    noptFix(grunt);
    var environment = grunt.option('env') || 'dev';
    var progress = !grunt.option('no-progress');

    var webpackConfig = _.extend({}, webpackGlobalConfig);

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }
    var isDev = environment === 'dev';
    if (!process.env.BABEL_ENV) {
        process.env.BABEL_ENV = environment;
    }
    if (!process.env.NODE_ENV) {
        process.env.NODE_ENV = environment;
    }
    var isWatch = grunt.option('watch');

    // Extend the global webpack config options with environment-specific changes
    if (isDev) {
        webpackConfig.devtool = 'source-map';
        webpackConfig.cache = true;
        webpackConfig.plugins.push(new webpack.LoaderOptionsPlugin({
            minimize: false,
            debug: true
        }));
    } else {
        webpackConfig.devtool = false;
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
            new webpack.optimize.DedupePlugin(),
            new webpack.optimize.UglifyJsPlugin({
                // ASCIIOnly: true,
                // sourceMapIncludeSources: true,
                compress: {
                    warnings: false
                },
                output: {
                    comments: false
                }
            })
        ]);
    }

    // https://github.com/webpack/grunt-webpack
    var gruntWebpackConfig = {
        stats: {
            children: false,
            colors: true,
            modules: false,
            reasons: false,
            errorDetails: true
        },
        progress: progress,    // show progress
        failOnError: !isWatch, // report error to grunt if webpack find errors; set to false if
        watch: isWatch,        // use webpacks watcher (you need to keep the grunt process alive)
        keepalive: isWatch,    // don't finish the grunt task (in combination with the watch option)
        inline: false,         // embed the webpack-dev-server runtime into the bundle (default false)
        hot: false             // adds HotModuleReplacementPlugin and switch the server to hot mode
    };

    var config = {
        webpack: {
            options: _.extend({}, webpackConfig, gruntWebpackConfig),
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
                    })
                ]
            },
            core_app: {
                entry: {
                    girder_app: [path.join(paths.web_src, 'main.js')]
                },
                plugins: [
                    new customWebpackPlugins.DllReferenceByPathPlugin({
                        context: '.',
                        manifest: path.join(paths.web_built, 'girder_lib-manifest.json')
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
    };

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

    grunt.config.merge(config);
};
