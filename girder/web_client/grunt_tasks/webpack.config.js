/**
 * This file contains options that apply to ALL target build configurations. Because we use
 * the DllPlugin for dynamic loading, each individual bundle has its own config options
 * that can extend these.
 */
var path = require('path');

var webpack = require('webpack');
var ExtractTextPlugin = require('extract-text-webpack-plugin');

const nodeModules = require('./webpack.paths').node_modules;

// Resolving the Babel presets here is required to support symlinking plugin directories from
// outside Girder's file tree
const babelPresets = require.resolve('babel-preset-env');

function fileLoader() {
    return {
        loader: 'file-loader',
        options: {
            name: '[name]-[hash:8].[ext]',
            outputPath: 'assets/'
        }
    };
}

var loaderPaths = [path.dirname(require.resolve('@girder/core'))];
var loaderPathsNodeModules = loaderPaths.concat([nodeModules]);

module.exports = {
    output: {
        // pathinfo: true,  // for debugging
        filename: '[name].min.js'
    },
    plugins: [
        // Exclude all of Moment.js's extra locale files except English
        // to reduce build size.  See https://webpack.js.org/plugins/context-replacement-plugin/
        new webpack.ContextReplacementPlugin(/moment[/\\]locale$/, /en/),

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
            // ES2015+
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
                            // Without any options, 'preset-env' behavies like 'preset-latest'
                            presets: [babelPresets],
                            cacheDirectory: true
                        }
                    }
                ]
            },
            // Stylus
            {
                resource: {
                    test: /\.styl$/,
                    include: loaderPathsNodeModules
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
                    include: loaderPathsNodeModules
                },
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: [babelPresets],
                            cacheDirectory: true
                        }
                    },
                    'pug-loader'
                ]
            },
            // PNG, JPEG
            {
                resource: {
                    test: /\.(png|jpg|gif)$/,
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
        extensions: ['.js'],
        symlinks: false,
        alias: {
            'jquery': require.resolve('jquery'), // ensure that all plugins use the same "jquery"
            // For some reason, this is necessary to ensure DllPlugin splitting works properly
            '@girder/core': path.dirname(require.resolve('@girder/core'))
        }
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
    }
};
