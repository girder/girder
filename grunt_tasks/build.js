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
 * Define tasks that bundle and compile files for deployment.
 */
module.exports = function (grunt) {
    var path = require('path');
    var glob = require('glob');
    var clients_web_dir = path.join(__dirname, '../clients/web');
    var node_modules_dir = path.join(__dirname, '../node_modules');
    var web_src_dir = path.join(clients_web_dir, 'src');
    var webpack = require('webpack');
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
        module: {
            loaders: [
                // { // CSS
                //     test: /\.css$/,
                //     loader: 'style-loader!css-loader'
                // },
                // { // Stylus
                //     test: /\.styl$/,
                //     loader: 'style-loader!css-loader!stylus-loader'
                // },
                { // Jade
                    test: /\.jade$/,
                    loader: 'jade'
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
                'girder': web_src_dir
            },
            extensions: ['.js', '.styl', '.css', '.jade', '']
            // modulesDirectories: [
            //     web_src_dir,
            //     node_modules_dir
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
            new webpack.DefinePlugin({
                'process.env': {
                    'NODE_ENV': JSON.stringify(environment === 'dev' ? 'dev' : 'production')
                }
            }),
            // Automatically detect jQuery and $ as free var in modules
            // and inject the jquery library. This is required by many jquery plugins
            new webpack.ProvidePlugin({
                jQuery: 'jquery',
                $: 'jquery'
            }),
            new webpack.optimize.CommonsChunkPlugin({
                name: 'girder.ext',
                // See http://stackoverflow.com/a/29087883/250457
                minChunks: function (module) {
                    var include = module.resource &&
                        module.resource.indexOf(clients_web_dir) === -1;
                    if (include) {
                        console.log('[girder.ext] <=', module.resource.replace(node_modules_dir, ''));
                    }
                    return include;
                }
            })
        ]
    };

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

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
        jade: {
            options: {
                client: true,
                compileDebug: false,
                namespace: 'girder.templates',
                processName: function (filename) {
                    return path.basename(filename, '.jade');
                }
            },
            core: {
                files: {
                    'clients/web/static/built/templates.js': [
                        'clients/web/src/templates/**/*.jade'
                    ]
                }
            }
        },

        copy: {
            swagger: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/swagger-ui/dist',
                    src: ['lib/**', 'css/**', 'images/**', 'swagger-ui.min.js'],
                    dest: 'clients/web/static/built/swagger'
                }]
            },
            jsoneditor: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/jsoneditor/dist',
                    src: ['img/**'],
                    dest: 'clients/web/static/built/jsoneditor'
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
                    'clients/web/static/built/girder.app.min.css': [
                        'clients/web/src/stylesheets/**/*.styl',
                        '!clients/web/src/stylesheets/apidocs/*.styl'
                    ],
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

        concat: {
            options: {
                stripBanners: {
                    block: true,
                    line: true
                }
            },
            ext_css: {
                files: {
                    'clients/web/static/built/girder.ext.min.css': [
                        'node_modules/bootstrap/dist/css/bootstrap.min.css',
                        'node_modules/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        'node_modules/eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.min.css',
                        'node_modules/jsoneditor/dist/jsoneditor.min.css',
                        'node_modules/as-jqplot/dist/jquery.jqplot.min.css'
                    ]
                }
            }
        },

        uglify: {
            options: uglifyOptions,
            app: {
                files: {
                    'clients/web/static/built/girder.app.min.js': [
                        'clients/web/static/built/templates.js',
                        'clients/web/src/init.js',
                        'clients/web/src/girder-version.js',
                        'clients/web/src/view.js',
                        'clients/web/src/app.js',
                        'clients/web/src/router.js',
                        'clients/web/src/utilities/**/*.js',
                        'clients/web/src/plugin_utils.js',
                        'clients/web/src/collection.js',
                        'clients/web/src/model.js',
                        'clients/web/src/models/**/*.js',
                        'clients/web/src/collections/**/*.js',
                        'clients/web/src/views/**/*.js'
                    ],
                    'clients/web/static/built/girder.main.min.js': [
                        'clients/web/src/main.js'
                    ]
                }
            },
            ext_js: {
                files: {
                    'clients/web/static/built/girder.ext.min.js': [
                        'node_modules/jquery/dist/jquery.js',
                        'node_modules/jade/runtime.js',
                        'node_modules/underscore/underscore.js',
                        'node_modules/backbone/backbone.js',
                        'node_modules/remarkable/dist/remarkable.js',
                        'node_modules/jsoneditor/dist/jsoneditor.js',
                        'node_modules/bootstrap/dist/js/bootstrap.js',
                        'node_modules/bootstrap-switch/dist/js/bootstrap-switch.js',
                        'node_modules/eonasdan-bootstrap-datetimepicker/bower_components/moment/moment.js',
                        'node_modules/eonasdan-bootstrap-datetimepicker/src/js/bootstrap-datetimepicker.js',
                        'node_modules/d3/d3.js',
                        'node_modules/as-jqplot/dist/jquery.jqplot.js',
                        'node_modules/as-jqplot/dist/plugins/jqplot.pieRenderer.js',
                        'node_modules/sprintf-js/src/sprintf.js'
                    ]
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
                    .concat(glob.sync('./clients/web/src/views/**/*.js'))
                }
            }
        },

        symlink: {
            options: {
                overwrite: true
            },
            legacy_names: {
                // Provide static files under old names, for compatibility
                files: [{
                    src: ['clients/web/static/built/girder.app.min.js'],
                    dest: 'clients/web/static/built/app.min.js'
                }, {
                    src: ['clients/web/static/built/girder.app.min.css'],
                    dest: 'clients/web/static/built/app.min.css'
                }, {
                    src: ['clients/web/static/built/girder.main.min.js'],
                    dest: 'clients/web/static/built/main.min.js'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.js'],
                    dest: 'clients/web/static/built/libs.min.js'
                }, {
                    // This provides more than just Bootstrap, but that no
                    // longer exists as a standalone file
                    // Note, girder.ext.min.css was never released as another
                    // name
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/lib/bootstrap/css/bootstrap.min.css'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/lib/bootstrap/css/bootstrap-switch.min.css'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/built/jsoneditor/jsoneditor.min.css'
                }, {
                    src: ['clients/web/static/built/girder.ext.min.css'],
                    dest: 'clients/web/static/lib/jqplot/css/jquery.jqplot.min.css'
                }, {
                    src: ['clients/web/static/built/fontello'],
                    dest: 'clients/web/static/lib/fontello'
                }]
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
            // 'uglify:ext_js': {},
            // 'webpack:ext_js': {},
            'copy:swagger': {},
            'copy:jsoneditor': {},
            'copy:fontello_config': {},
            'concat:ext_css': {},
            'fontello:ext_font': {}
        },

        default: {
            'stylus:core': {},
            'jade:core': {
                dependencies: ['version-info']
            },
            // 'uglify:app': {
            'webpack:app': {
                dependencies: ['jade:core']
            },
            'symlink:legacy_names': {
                dependencies: ['uglify:app']
            }
        }
    });
};
