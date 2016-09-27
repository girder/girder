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

var _ = require('underscore');
var noptFix = require('nopt-grunt-fix');

var webpackConfig = require('./webpack.config.js');
var webpackDevConfig = require('./webpack.dev.js');
var webpackProdConfig = require('./webpack.prod.js');

module.exports = function (grunt) {
    noptFix(grunt);
    var environment = grunt.option('env') || 'dev';
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

    // https://github.com/webpack/grunt-webpack
    var gruntWebpackConfig = {
        stats: {
            children: false,
            colors: true,
            modules: false,
            reasons: false,
            errorDetails: true
        },
        progress: true,    // show progress
        failOnError: true, // report error to grunt if webpack find errors; set to false if
        watch: false,      // use webpacks watcher (you need to keep the grunt process alive)
        keepalive: false,  // don't finish the grunt task (in combination with the watch option)
        inline: false,     // embed the webpack-dev-server runtime into the bundle (default false)
        hot: false         // adds HotModuleReplacementPlugin and switch the server to hot mode
    };

    var config = {
        webpack: {
            options: _.extend({}, webpackConfig, gruntWebpackConfig),
            prod: webpackProdConfig,
            dev: webpackDevConfig,
            // This watch subtask is a lot faster than using grunt-contrib-watch below
            watch: _.extend({}, isDev ? webpackDevConfig : webpackProdConfig, {
                watch: true,
                keepalive: true
            })
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
        isWatch ? 'webpack:watch' : (isDev ? 'webpack:dev' : 'webpack:prod')
    ]);

    // Warn about not using grunt-contrib-watch, use webpack:watch or grunt --watch instead
    grunt.registerTask('warnWatch', function () {
        grunt.log.warn('WARNING: the "watch" task will not build; use the "webpack:watch" task or run grunt --watch'['yellow']);
    });

    grunt.config.merge(config);
};
