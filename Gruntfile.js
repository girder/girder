module.exports = function (grunt) {
    var fs = require('fs');
    var path = require('path');

    // Project configuration.
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        config: {
        },

        jade: {
            inputDir: 'templates',
            outputFile: 'clients/web/static/built/templates.js'
        },

        stylus: {
            compile: {
                files: {
                    'clients/web/static/built/dmtk.min.css': ['stylesheets/*.styl']
                }
            }
        },

        uglify: {
            app: {
                files: {
                    'clients/web/static/built/dmtk.min.js': [
                        'clients/web/static/built/templates.js'
                    ]
                }
            },
            libs: {
                files: {
                    'clients/web/static/built/libs.min.js': [
                        'node_modules/jquery-browser/lib/jquery.js',
                        'node_modules/jade/runtime.js',
                        'node_modules/underscore/underscore.js',
                        'node_modules/backbone/backbone.js',
                        'clients/web/lib/js/bootstrap.min.js'
                    ]
                }
            }
        },

        watch: {
            css: {
                files: ['stylesheets/*.styl'],
                tasks: ['stylus'],
                options: {failOnError: false}
            },
            js: {
                files: ['clients/web/static/src/**/*.js'],
                tasks: ['uglify'],
                options: {failOnError: false}
            },
            jade: {
                files: ['templates/*.jade'],
                tasks: ['build-js'],
                options: {failOnError: false}
            }
        }
    });
    grunt.loadNpmTasks('grunt-shell');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-qunit');
    grunt.loadNpmTasks('grunt-contrib-stylus');
    grunt.loadNpmTasks('grunt-contrib-uglify');

    // Compile the jade templates into a single js file
    grunt.registerTask('jade', 'Build the templates', function () {
        var config = grunt.config.get('jade');
        var outputFile = config.outputFile;
        var jade = require('jade');

        var task = this;
        var inputFiles = grunt.file.expand(config.inputDir+"/*.jade");

        fs.writeFileSync(outputFile, '\nvar jade=jade||{};jade.templates=jade.templates||{};\n');

        inputFiles.forEach(function (filename, i) {
            var buffer = fs.readFileSync(filename);
            var basename = path.basename(filename, '.jade');
            console.log('Compiling template: ' + basename);

            var fn = jade.compile(buffer, {
                client: true,
                compileDebug: false
            });

            var jt = "\njade.templates['" + basename + "']=" + fn.toString() + ';';
            fs.appendFileSync(outputFile, jt);
        });
        console.log('Wrote ' + inputFiles.length + ' templates into ' + outputFile);
    });

    // This task should be run once manually at install time.
    grunt.registerTask('init', 'Initial install/setup tasks', function () {
        if (!fs.existsSync('server/conf/db.local.cfg')) {
            console.log('Creating local config file');
            fs.writeFileSync('server/conf/db.local.cfg', fs.readFileSync('server/conf/db.cfg'));
        }
    });

    grunt.registerTask('build-js', ['jade', 'uglify']);
    grunt.registerTask('default', ['stylus', 'build-js']);
};
