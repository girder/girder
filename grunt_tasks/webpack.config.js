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

var webpack = require('webpack');
var path = require('path');

var CommonsChunkPlugin = webpack.optimize.CommonsChunkPlugin;
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var ProvidePlugin = webpack.ProvidePlugin;

var paths = require('./webpack.paths.js');

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

module.exports = {
    entry: {
        'girder.ext': [
            // This make sure some globals like $, moment, Backbone are available for testing
            path.join(paths.web_src, 'globals.js')
        ],
        'girder.app': path.join(paths.web_src, 'main.js')
    },
    output: {
        path: paths.web_built,
        filename: '[name].min.js'
    },
    plugins: [
        // See http://stackoverflow.com/a/29087883/250457
        // TODO: there is still too much code going in each plugin.min.js
        // new webpack.optimize.CommonsChunkPlugin({
        //     name: 'girder.app',
        //     minChunks: function (module) {
        //         var include = module.resource &&
        //             module.resource.indexOf(paths.clients_web) !== -1;
        //         if (include) {
        //           // console.log('[girder.app] <=', module.resource.replace(paths.node_modules, ''));
        //         }
        //         return include;
        //     }
        // }),
        new CommonsChunkPlugin({
            name: 'girder.ext',
            minChunks: function (module) {
                var include = module.resource &&
                    module.resource.indexOf(paths.clients_web) === -1 &&
                    module.resource.indexOf(paths.plugins) === -1;
                if (include) {
                  // console.log('[girder.ext] <=', module.resource.replace(paths.node_modules, ''));
                }
                return include;
            }
        }),
        // Automatically detect jQuery and $ as free var in modules
        // and inject the jquery library. This is required by many jquery plugins
        new ProvidePlugin({
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
                loader: 'babel-loader',
                exclude: [paths.node_modules]
            },
            // Stylus
            {
                test: /\.styl$/,
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
                loaders: [
                    ExtractTextPlugin.extract('style-loader'),
                    'css-loader'
                ]
            },
            // Pug
            {
                test: /\.(pug|jade)$/,
                loaders: [
                    'babel-loader',
                    'pug-loader'
                ]
            },
            // PNG, JPEG
            {
                test: /\.(png|jpg)$/,
                loaders: [
                    urlLoader(),
                    fileLoader()
                ]
            },
            // WOFF
            {
                test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                loaders: [
                    urlLoader({ mimetype: 'application/font-woff' }),
                    fileLoader()
                ]
            },
            // WOFF2
            {
                test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                loaders: [
                    urlLoader({ mimetype: 'application/font-woff2' }),
                    fileLoader()
                ]
            },
            // TTF
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                loaders: [
                    urlLoader({ mimetype: 'application/octet-stream' }),
                    fileLoader()
                ]
            },
            // EOT
            {
                test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                loaders: [
                    fileLoader()
                ]
            },
            // SVG
            {
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
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
        // modulesDirectories: [ // deprecated in Webpack 2 beta, remove once 100% sure
        //     paths.web_src,
        //     paths.plugins,
        //     paths.node_modules
        // ]
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
