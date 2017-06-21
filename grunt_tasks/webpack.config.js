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
        options: {
            name: 'assets/[name]-[hash:8].[ext]'
        }
    };
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
        // Disable writing the output file if a build error occurs
        new webpack.NoEmitOnErrorsPlugin()
    ],
    module: {
        rules: [
            // ES2015
            {
                resource: {
                    test: /\.js$/,
                    include: loaderPaths,
                    exclude: /node_modules/
                },
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: [es2015Preset],
                            env: {
                                cover: _coverageConfig()
                            }
                        }
                    }
                ]
            },
            // Stylus
            {
                resource: {
                    test: /\.styl$/,
                    include: loaderPaths
                },
                use: ExtractTextPlugin.extract({
                    use: [
                        'css-loader',
                        {
                            loader: 'stylus-loader',
                            options: {
                                // The 'resolve url' option is not well-documented, but was
                                // added at https://github.com/shama/stylus-loader/pull/6
                                'resolve url': true
                            }
                        }
                    ],
                    fallback: 'style-loader'
                })
            },
            // CSS
            {
                resource: {
                    test: /\.css$/,
                    include: loaderPathsNodeModules
                },
                use: ExtractTextPlugin.extract({
                    use: ['css-loader'],
                    fallback: 'style-loader'
                })
            },
            // Pug
            {
                resource: {
                    test: /\.(pug|jade)$/,
                    include: loaderPaths
                },
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: [es2015Preset]
                        }
                    },
                    'pug-loader'
                ]
            },
            // PNG, JPEG
            {
                resource: {
                    test: /\.(png|jpg)$/,
                    include: loaderPathsNodeModules
                },
                use: [
                    fileLoader()
                ]
            },
            // WOFF
            {
                resource: {
                    test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                    include: loaderPathsNodeModules
                },
                use: [
                    fileLoader()
                ]
            },
            // WOFF2
            {
                resource: {
                    test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                    include: loaderPathsNodeModules
                },
                use: [
                    fileLoader()
                ]
            },
            // TTF
            {
                resource: {
                    test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                    include: loaderPathsNodeModules
                },
                use: [
                    fileLoader()
                ]
            },
            // EOT
            {
                resource: {
                    test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                    include: loaderPathsNodeModules
                },
                use: [
                    fileLoader()
                ]
            },
            // SVG
            {
                resource: {
                    test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                    include: loaderPathsNodeModules
                },
                use: [
                    fileLoader()
                ]
            }
        ]
    },
    resolve: {
        alias: {
            'girder': paths.web_src
        },
        extensions: ['.js'],
        modules: [
            paths.node_modules
        ],
        symlinks: false
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
