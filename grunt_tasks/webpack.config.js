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
 * This file contains options that apply to ALL target build configurations. Because we use
 * the DllPlugin for dynamic loading, each individual bundle has its own config options
 * that can extend these.
 */
var fs = require('fs');
var path = require('path');
var yaml = require('js-yaml');
var webpack = require('webpack');

var ExtractTextPlugin = require('extract-text-webpack-plugin');

var paths = require('./webpack.paths.js');
var es2015Preset = require.resolve('babel-preset-es2015');
var istanbulPlugin = require.resolve('babel-plugin-istanbul');

function fileLoader() {
    return {
        loader: 'file-loader',
        query: {
            name: 'assets/[name]-[hash:8].[ext]'
        }
    };
}

function urlLoader(options) {
    options = options || {};
    var loader = {
        loader: 'url-loader',
        query: {
            limit: 4096
        }
    };
    if (options.mimetype) {
        loader.query.mimetype = options.mimetype;
    }
    return loader;
}

function defaultLoaderPlugins() {
    // Computes a list of plugin paths that are opting to use Girder's loader
    // configuration directly; these paths will be added to the "include"
    // directive for the loaders in the config template below.
    var dirs = fs.readdirSync('plugins');
    var paths = [];

    dirs.forEach(function (dir) {
        // Find a plugin config file.
        var pluginFile = path.resolve('plugins', dir, 'plugin.yml');
        if (!fs.existsSync(pluginFile)) {
            pluginFile = path.resolve('plugins', dir, 'plugin.json');
            if (!fs.existsSync(pluginFile)) {
                pluginFile = null;
            }
        }

        // If there's a plugin file, and it has no config, no webpack section,
        // no defaultLoaders property, or the defaultLoaders property is
        // explicitly set to anything besdies false, then add the plugin to the
        // list of plugins that want to use Girder's loader configuration.
        if (pluginFile) {
            var config = yaml.safeLoad(fs.readFileSync(pluginFile));
            if (!config || !config.webpack || config.webpack.defaultLoaders === undefined || config.webpack.defaultLoaders !== false) {
                paths.push(path.resolve('plugins', dir));
            }
        }
    });

    return paths;
}

var loaderPaths = defaultLoaderPlugins().concat([/clients\/web\/src/]);

module.exports = {
    output: {
        path: paths.web_built,
        filename: '[name].min.js'
    },
    plugins: [
        // Automatically detect jQuery and $ as free var in modules
        // and inject the jquery library. This is required by many jquery plugins
        new webpack.ProvidePlugin({
            jQuery: 'jquery',
            $: 'jquery',
            'window.jQuery': 'jquery'
        }),
        new ExtractTextPlugin({
            filename: '[name].min.css',
            allChunks: true,
            disable: false
        })
    ],
    module: {
        loaders: [
            // ES2015
            {
                test: /\.js$/,
                include: loaderPaths,
                loader: 'babel-loader',
                exclude: /node_modules/,
                query: {
                    presets: [es2015Preset],
                    env: {
                        cover: {
                            plugins: [[
                                istanbulPlugin, {
                                    exclude: ['**/*.pug', '**/*.jade', 'node_modules/**/*']
                                }
                            ]]
                        }
                    }
                }
            },
            // JSON files
            {
                test: /\.json$/,
                include: loaderPaths,
                loader: 'json-loader'
            },
            // Stylus
            {
                test: /\.styl$/,
                include: loaderPaths,
                loaders: [
                    ExtractTextPlugin.extract('style-loader'),
                    'css-loader',
                    {
                        loader: 'stylus-loader',
                        query: {
                            'resolve url': true
                        }
                    }
                ]
            },
            // CSS
            {
                test: /\.css$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    ExtractTextPlugin.extract('style-loader'),
                    'css-loader'
                ]
            },
            // Pug
            {
                test: /\.(pug|jade)$/,
                include: loaderPaths,
                loaders: [
                    {
                        loader: 'babel-loader',
                        query: {
                            presets: [es2015Preset]
                        }
                    },
                    'pug-loader'
                ]
            },
            // PNG, JPEG
            {
                test: /\.(png|jpg)$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    fileLoader()
                ]
            },
            // WOFF
            {
                test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    urlLoader({ mimetype: 'application/font-woff' }),
                    fileLoader()
                ]
            },
            // WOFF2
            {
                test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    urlLoader({ mimetype: 'application/font-woff2' }),
                    fileLoader()
                ]
            },
            // TTF
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    urlLoader({ mimetype: 'application/octet-stream' }),
                    fileLoader()
                ]
            },
            // EOT
            {
                test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    fileLoader()
                ]
            },
            // SVG
            {
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPaths.concat([
                    /node_modules/
                ]),
                loaders: [
                    urlLoader({ mimetype: 'image/svg+xml' }),
                    fileLoader()
                ]
            }
        ],
        noParse: [
            // Avoid warning:
            //   This seems to be a pre-built javascript file. Though this is
            //   possible, it's not recommended. Try to require the original source
            //   to get better results.
            // This needs fixing later, as Webpack works better when provided with source.
            // /node_modules\/pug/,
            // /node_modules\/remarkable/
        ]
    },
    resolve: {
        alias: {
            'girder': paths.web_src
        },
        extensions: ['.styl', '.css', '.pug', '.jade', '.js', ''],
        modules: [
            paths.clients_web,
            paths.plugins,
            paths.node_modules
        ]
    },
    node: {
        canvas: 'empty',
        file: 'empty',
        fs: 'empty',
        jsdom: 'empty',
        system: 'empty',
        xmldom: 'empty'
    }
};
