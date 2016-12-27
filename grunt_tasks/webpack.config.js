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
var path = require('path');
var webpack = require('webpack');

var ExtractTextPlugin = require('extract-text-webpack-plugin');

var paths = require('./webpack.paths.js');
var es2015Preset = require.resolve('babel-preset-es2015');

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

function _coverageConfig() {
    try {
        var istanbulPlugin = require.resolve('babel-plugin-istanbul');
        return {
            plugins: [[
                istanbulPlugin, {
                    exclude: ['**/*.pug', '**/*.jade', 'node_modules/**/*']
                }
            ]]
        };
    } catch (e) {
        // We won't have the istanbul plugin installed in a prod env.
        return {};
    }
}

var loaderPaths = [path.resolve('clients', 'web', 'src')];
var loaderPathsNodeModules = loaderPaths.concat([path.resolve('node_modules')]);

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
                        cover: _coverageConfig()
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
                include: loaderPathsNodeModules,
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
                include: loaderPathsNodeModules,
                loaders: [
                    fileLoader()
                ]
            },
            // WOFF
            {
                test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPathsNodeModules,
                loaders: [
                    urlLoader({ mimetype: 'application/font-woff' }),
                    fileLoader()
                ]
            },
            // WOFF2
            {
                test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPathsNodeModules,
                loaders: [
                    urlLoader({ mimetype: 'application/font-woff2' }),
                    fileLoader()
                ]
            },
            // TTF
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPathsNodeModules,
                loaders: [
                    urlLoader({ mimetype: 'application/octet-stream' }),
                    fileLoader()
                ]
            },
            // EOT
            {
                test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPathsNodeModules,
                loaders: [
                    fileLoader()
                ]
            },
            // SVG
            {
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                include: loaderPathsNodeModules,
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
