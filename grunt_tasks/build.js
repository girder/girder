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

var ExtractTextPlugin = require('extract-text-webpack-plugin');
var path              = require('path');
var webpack           = require('webpack');
var fs                = require('fs');

/**
 * Define tasks that bundle and compile files for deployment.
 */
module.exports = function (grunt) {
    var paths = {
        clients_web: path.join(__dirname, '../clients/web'),
        node_modules: path.join(__dirname, '../node_modules'),
        web_src: path.join(__dirname, '../clients/web/src'),
        plugins: path.join(__dirname, '../plugins')
    };
    var environment = grunt.option('env') || 'dev';
    var debugJs = grunt.option('debug-js') || environment === 'dev';

    var uglifyOptions = {
        ASCIIOnly: true,
        sourceMap: environment === 'dev',
        sourceMapIncludeSources: true,
        report: 'min'
    };

    var statsOptions = {
        colors: true,
        modules: true,
        reasons: true,
        errorDetails: true
    };

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

    var webpackOptions = {
        watch: false,      // use webpacks watcher (you need to keep the grunt process alive)
        keepalive: false,  // don't finish the grunt task (in combination with the watch option)
        inline: false,     // embed the webpack-dev-server runtime into the bundle (default false)
        hot: false,        // adds HotModuleReplacementPlugin and switch the server to hot mode
        cache: true,
        progress: true,   // show progress
        failOnError: true, // report error to grunt if webpack find errors; set to false if
                           // webpack errors are tolerable and grunt should continue
        devtool: environment === 'dev' ? 'source-map' : false,
        stats: {
            children: false
        },
        module: {
            loaders: [
                { // Stylus
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
                { // CSS
                    test: /\.css$/,
                    loaders: [
                        ExtractTextPlugin.extract('style-loader'),
                        'css-loader'
                    ]
                },
                { // Jade
                    test: /\.jade$/,
                    loader: 'jade-loader',
                    query: {
                        doctype: 'html' // see @girder/pull/1469
                    }
                },
                { // PNG, JPEG
                    test: /\.(png|jpg)$/,
                    loaders: [urlLoader(), fileLoader()]
                },
                { // WOFF
                    test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader({ mimetype: 'application/font-woff' }), fileLoader()]
                },
                { // WOFF2
                    test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader({ mimetype: 'application/font-woff2' }), fileLoader()]
                },
                { // TTF
                    test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader({ mimetype: 'application/octet-stream' }), fileLoader()]
                },
                { // EOT
                    test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [fileLoader()]
                },
                { // SVG
                    test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader({ mimetype: 'image/svg+xml' }), fileLoader()]
                }
            ],
            noParse: [
                // Avoid warning:
                //   This seems to be a pre-built javascript file. Though this is
                //   possible, it's not recommended. Try to require the original source
                //   to get better results.
                // This needs fixing later, as Webpack works better when provided with source.
                // /node_modules\/jade/,
                // /node_modules\/remarkable/
            ]
        },
        resolve: {
            alias: {
                'girder': paths.web_src
            },
            extensions: ['.styl', '.css', '.jade', '.js', ''],
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
        },
        plugins: [
            new webpack.DefinePlugin({ // IMPORTANT
                'process.env': {
                    'NODE_ENV': JSON.stringify(environment === 'dev' ? 'dev' : 'production')
                }
            }),
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
            }),
            // https://github.com/webpack/webpack/issues/283
            // https://github.com/webpack/webpack/issues/2061#issuecomment-228932941
            // https://gist.github.com/sokra/27b24881210b56bbaff7#loader-options--minimize
            // but unclear and confusing as to how far it has been implemented
            new webpack.LoaderOptionsPlugin({
                minimize: environment !== 'dev',
                debug: debugJs
            })
        ]
    };

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    if (debugJs) {
        uglifyOptions.beautify = {
            beautify: true
        };
        uglifyOptions.mangle = false;
        uglifyOptions.compress = false;
        webpackOptions.debug = true;
    } else {
        webpackOptions.plugins = webpackOptions.plugins.concat(
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
        );
    }

    var webpackTask = {
        options: webpackOptions,
        app: {
            entry: {
                'girder.ext': [],
                'girder.app': './clients/web/src/main.js'
            },
            output: {
                path: 'clients/web/static/built/',
                filename: '[name].min.js'
            },
            // stats: statsOptions,
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
                new webpack.optimize.CommonsChunkPlugin({
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
                })
            ]
        }
    };

    // Add plugin entry points
    grunt.file.expand(grunt.config.get('pluginDir') + '/*').forEach(function (dir) {
        var plugin = path.basename(dir);
        var pluginTarget = 'plugins/' + plugin + '/plugin';
        var webClient = path.resolve('./' + dir + '/web_client');
        var main =  webClient + '/main.js';
        if (fs.existsSync(main)) {
            // grunt.log.writeln(('Using: ' + main).bold);
            webpackTask.app.entry[pluginTarget] = main;
            webpackTask.options.resolve.alias['plugins/' + plugin] = webClient;
        }
    });

    grunt.config.merge({
        webpack: webpackTask,

        // This should be replaced by webpack's own watch/hot-reload
        // watch: {
        //     core: {
        //         files: [
        //             'clients/web/src/**/*.js',
        //             'clients/static/built/templates.js',
        //             'clients/web/src/stylesheets/**/*.styl',
        //             'clients/web/src/templates/**/*.jade'
        //         ],
        //         tasks: ['webpack:app']
        //     }
        // },

        default: {
            'webpack:app': {
                dependencies: ['version-info'] // which generates clients/web/src/version.js
            }
        }
    });
};
