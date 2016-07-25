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

var fs = require('fs');
var path = require('path');
var _ = require('underscore');

var paths = require('./webpack.paths.js');
var webpackConfig = require('./webpack.config.js');
var webpackDevConfig = require('./webpack.dev.js');
var webpackProdConfig = require('./webpack.prod.js');

function getWatchFiles(dir) {
    return [
        path.join(dir, '**/*.js'),
        path.join(dir, 'stylesheets/**/*.styl'),
        path.join(dir, 'templates/**/*.jade')
    ];
}

module.exports = function (grunt) {
    var environment = grunt.option('env') || 'dev';
    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }
    var isDev = environment === 'dev';
    var isWatch = grunt.option('watch');
    var skipPlugins = grunt.option('skip-plugins');

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
        // The grunt-contrib-watch task below is one option for dev, as described here:
        // https://github.com/webpack/webpack-with-common-libs/blob/master/Gruntfile.js
        // but it could also be done using the webpack dev server.
        // It is however A LOT SLOWER than using the built-in watch options in grunt-webpack
        watch: {
            app: {
                files: getWatchFiles(paths.web_src),
                tasks: ['warnWatch', isDev ? 'webpack:dev' : 'webpack:prod'],
                options: {
                    atBegin: true,
                    spawn: false
                }
            }
        },
        default: {}
    };
    var defaultTask = isWatch ? 'webpack:watch' : (isDev ? 'webpack:dev' : 'webpack:prod');
    config.default[defaultTask] = {
        dependencies: ['version-info'] // which generates clients/web/src/version.js
    };

    grunt.registerTask('warnWatch', function () {
        grunt.log.warn('WARNING: the "watch" task is a lot slower than the "webpack:watch" or running grunt --watch'['yellow']);
    });

    // Add plugin entry points (should be in webpack.config.js but skipPlugins is a grunt option)
    if (!skipPlugins) {
        grunt.file.expand(grunt.config.get('pluginDir') + '/*').forEach(function (dir) {
            var plugin = path.basename(dir);
            var pluginTarget = 'plugins/' + plugin + '/plugin';
            var webClient = path.resolve('./' + dir + '/web_client');
            var main =  webClient + '/main.js';
            if (fs.existsSync(main)) {
                config.webpack.options.entry[pluginTarget] = main;
                config.webpack.options.resolve.alias['plugins/' + plugin] = webClient;
            }
        });
    }

    grunt.config.merge(config);
};
