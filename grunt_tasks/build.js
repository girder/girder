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
var glob              = require('glob');
var path              = require('path');
var webpack           = require('webpack');

/**
 * Define tasks that bundle and compile files for deployment.
 */
module.exports = function (grunt) {
    var paths = {
        clients_web: path.join(__dirname, '../clients/web'),
        node_modules: path.join(__dirname, '../node_modules'),
        web_src: path.join(__dirname, '../clients/web/src')
    };
    var environment = grunt.option('env') || 'dev';
    var debugJs = grunt.option('debug-js') || false;
    // vvvvvv TESTING
    environment = 'dev'; debugJs = true;
    // ^^^^^^ TESTING
    var uglifyOptions = {
        ASCIIOnly: true,
        sourceMap: environment === 'dev',
        sourceMapIncludeSources: true,
        report: 'min'
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
        progress: false,    // show progress
        failOnError: true, // report error to grunt if webpack find errors; set to false if
                           // webpack errors are tolerable and grunt should continue
        devtool: environment === 'dev' ? 'source-map' : false,
        output: {
            path: 'clients/web/static/built/',
            filename: '[name].min.js'
        },
        stats: {
            children: false
        },
        // context: __dirname,
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
                    loaders: [ExtractTextPlugin.extract('style-loader'), 'css-loader']
                },
                { // Jade
                    test: /\.jade$/,
                    loader: 'jade-loader'
                },
                { // PNG, JPEG
                    test: /\.(png|jpg)$/,
                    loaders: [urlLoader(), fileLoader()]
                },
                { // WOFF
                    test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader(), fileLoader({ mimetype: 'application/font-woff' })]
                },
                { // WOFF2
                    test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader(), fileLoader({ mimetype: 'application/font-woff2' })]
                },
                { // TTF
                    test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader(), fileLoader({ mimetype: 'application/octet-stream' })]
                },
                { // EOT
                    test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [fileLoader()]
                },
                { // SVG
                    test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                    loaders: [urlLoader(), fileLoader({ mimetype: 'image/svg+xml' })]
                }
            ],
            noParse: [
                // // Avoid warning:
                // //   This seems to be a pre-built javascript file. Though this is
                // //   possible, it's not recommended. Try to require the original source
                // //   to get better results.
                // // This needs fixing later, as Webpack works better when provided with source.
                // /node_modules\/jade/,
                // /node_modules\/remarkable/
            ]
        },
        // context: path.resolve(__dirname, 'web_external', 'src'),
        resolve: {
            alias: {
                'girder': paths.web_src
            },
            extensions: ['.styl', '.css', '.jade', '.js', ''],
            modules: [paths.clients_web, paths.node_modules],
            modulesDirectories: [paths.web_src, paths.node_modules]
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
            new webpack.DefinePlugin({
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
            new webpack.optimize.CommonsChunkPlugin({
                name: 'girder.ext',
                // See http://stackoverflow.com/a/29087883/250457
                minChunks: function (module) {
                    var include = module.resource &&
                        module.resource.indexOf(paths.clients_web) === -1;
                    if (include) {
                        // console.log('[girder.ext] <=', module.resource.replace(paths.node_modules, ''));
                    }
                    return include;
                }
            }),
            new ExtractTextPlugin('[name].min.css', {
                allChunks: true,
                disable: false
            })
        ]
    };

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    // new webpack.LoaderOptionsPlugin({
    //     test: /\.css$/, // optionally pass test, include and exclude, default affects all loaders
    //     minimize: true,
    //     debug: false,
    //     options: {
    //         // pass stuff to the loader
    //     }
    // })
    if (debugJs) {
        console.log('Building JS in debug mode'.yellow);
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

    grunt.config.merge({
        copy: {
            swagger: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/swagger-ui/dist',
                    src: ['lib/**', 'css/**', 'images/**', 'swagger-ui.min.js'],
                    dest: 'clients/web/static/built/swagger'
                }]
            },
            fontello_config: {
                files: [{
                    src: 'clients/web/fontello.config.json',
                    dest: 'clients/web/static/built/fontello.config.json'
                }]
            }
        },

        stylus: {
            core: {
                files: {
                    'clients/web/static/built/swagger/docs.css': [
                        'clients/web/src/stylesheets/apidocs/*.styl'
                    ]
                }
            }
        },

        fontello: {
            ext_font: {
                options: {
                    config: 'clients/web/static/built/fontello.config.json',
                    fonts: 'clients/web/static/built/fontello/font',
                    styles: 'clients/web/static/built/fontello/css',
                    // Create output directories
                    force: true
                }
            }
        },

        webpack: {
            options: webpackOptions,
            app: {
                entry: {
                    'girder.ext': [
                        // 'd3/d3.js'
                    ],
                    'girder.app': [
                        './clients/web/src/main.js'
                    ]
                    // .concat(glob.sync('./clients/web/src/views/**/*.js'))
                }
            }
        },

        watch: {
            stylus_core: {
                files: ['clients/web/src/stylesheets/**/*.styl'],
                tasks: ['stylus:core']
            },
            js_core: {
                files: [
                    'clients/web/src/**/*.js',
                    'clients/static/built/templates.js'
                ],
                tasks: ['uglify:app']
            },
            jade_core: {
                files: ['clients/web/src/templates/**/*.jade'],
                tasks: ['jade:core']
            }
        },

        init: {
            'copy:swagger': {},
            'copy:fontello_config': {},
            'fontello:ext_font': {}
        },

        default: {
            'stylus:core': {},
            'webpack:app': {
                dependencies: ['version-info']
            }
        }
    });
};
