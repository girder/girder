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
// Resolving the Babel presets here is required to support symlinking plugin directories from
// outside Girder's file tree
const es2015BabelPreset = require.resolve('babel-preset-es2015');
const es2016BabelPreset = require.resolve('babel-preset-es2016');

function fileLoader() {
    return {
        loader: 'file-loader',
        options: {
            name: '[name]-[hash:8].[ext]',
            outputPath: 'assets/'
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
        filename: '[name].min.js',
        path: paths.web_built
        // publicPath must be set to Girder's externally-served static path for built outputs
        // (typically '/static/built/'). This will be done at runtime with
        // '__webpack_public_path__', since it's not always known at build-time.
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
                            presets: [es2015BabelPreset, es2016BabelPreset],
                            env: {
                                cover: _coverageConfig()
                            },
                            cacheDirectory: true
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
                                'resolve url': true,
                                import: [
                                    '~nib/index.styl'
                                ]
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
                            presets: [es2015BabelPreset, es2016BabelPreset],
                            cacheDirectory: true
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
        symlinks: false
    },
    node: {
        canvas: 'empty',
        file: 'empty',
        fs: 'empty',
        jsdom: 'empty',
        system: 'empty',
        xmldom: 'empty'
    },
    stats: {
        assets: true,
        children: false,
        chunks: false,
        chunkModules: false,
        colors: true,
        errorDetails: true,
        hash: false,
        modules: false,
        reasons: false,
        timings: false
    },
    watchOptions: {
        ignored: /node_modules/
    }
};
