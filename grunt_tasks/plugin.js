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
 * Define tasks related to loading, configuring, and building plugins.
 */
module.exports = function (grunt) {

    var _ = require('underscore');
    var fs = require('fs');
    var path = require('path');

    /**
     * Register a task that will npm install inside plugin directories.
     */
    grunt.config.merge({
        shell: {
            'plugin-install': {
                /**
                 * Run npm install in the plugin directory
                 */
                command: function (plugin) {
                    var pth;
                    if (!plugin) {
                        return 'true';
                    }

                    pth = path.resolve(grunt.config.get('pluginDir'), plugin);
                    if (!fs.existsSync(path.resolve(pth, 'package.json'))) {
                        // do nothing if no plugin was provided
                        // or if it has no package.json file
                        grunt.verbose.writeln('Skipping npm install');
                        return 'true';
                    }
                    return 'cd "' + pth + '" && npm install';
                },
                options: {
                    execOptions: {
                        cwd: path.resolve(process.cwd(), 'plugins')
                    }
                },
                src: ['<%= grunt.config.get("pluginDir") %>/<%= grunt.task.current.args[0] %>/package.json']
            }
        },
        'plugin-install': {}
    });

    grunt.registerTask('plugins-builddir', 'Create the plugins build dir', function () {
        require('mkdirp').sync(grunt.config.get('staticDir') + '/built/plugins');
    });

    grunt.config.merge({
        jade: {
            /**
             * Generic jade compilation task.
             */
            plugin: {
                files: [{
                    src: ['<%= pluginDir %>/<%= grunt.task.current.args[0] %>/web_client/templates/**/*.jade'],
                    dest: '<%= staticDir %>/built/plugins/<%= grunt.task.current.args[0] %>/templates.js'
                }]
            }
        },
        stylus: {
            /**
             * Generic stylus compilation task.
             */
            plugin: {
                files: [{
                    src: ['<%= pluginDir %>/<%= grunt.task.current.args[0] %>/web_client/stylesheets/**/*.styl'],
                    dest: '<%= staticDir %>/built/plugins/<%= grunt.task.current.args[0] %>/plugin.min.css'
                }]
            }
        },
        uglify: {
            /**
             * Generic uglify task.
             */
            plugin: {
                files: [{
                    src: [
                        '<%= pluginDir %>/<%= grunt.task.current.args[0] %>/web_client/js/**/*.js',
                        '<%= grunt.config.getRaw("jade.plugin.files")[0].dest %>'
                    ],
                    dest: '<%= staticDir %>/built/plugins/<%= grunt.task.current.args[0] %>/plugin.min.js'
                }]
            }
        },
        copy: {
            /**
             * Generic copy task.
             */
            plugin: {
                files: [{
                    expand: true,
                    cwd: '<%= pluginDir %>/web_client',
                    src: ['extra/**'],
                    dest: '<%= staticDir %>/built/plugins/<%= grunt.task.current.args[0] %>'
                }]
            }
        },

        /**
         * Set default and init targets.
         */
        default: {
            plugin: {}
        },
        init: {
            'plugin-install': {},
            'plugins-builddir': {}
        }
    });

    /**
     * Insert individual plugins into the plugin meta task.
     */
    grunt.file.expand(grunt.config.get('pluginDir') + '/*')
        .forEach(function (dir) {
            var plugin = path.basename(dir);
            var json = path.resolve(dir, 'plugin.json');
            var yml = path.resolve(dir, 'plugin.yml');
            var config = {}, npm;

            grunt.log.writeln((
                'Found plugin: ' + plugin
            ).bold);

            // add the plugin explicitly to the plugin multitask
            grunt.config.set('plugin.' + plugin, {});

            // add targets to the init task
            grunt.config.set('plugin-install.shell:plugin-install:' + plugin, {});

            if (fs.existsSync(json)) {
                config = grunt.file.readYAML(json);
            }
            if (fs.existsSync(yml)) {
                config = grunt.file.readYAML(yml);
            }

            if (config.grunt) {
                grunt.log.writeln((
                    'Found plugin: ' + plugin + ' (custom Gruntfile)'
                ).bold);

                // install any addition npm packages during init
                npm = _(config.grunt.dependencies || []).map(function (version, dep) {
                    return dep + '@' + version;
                });
                if (npm.length) {
                    grunt.config.set(
                        'init.npm-install:' + npm.join(':'), {}
                    );
                }

                // load the plugin's gruntfile
                try {
                    require(
                        path.resolve(dir, config.grunt.file || 'Gruntfile.js')
                    )(grunt);
                } catch (e) {
                    // the error can be safely ignored when doing `grunt init`
                    // otherwise a default task will most likely fail later on
                    // write out a warning to help the developers debug errors
                    grunt.log.writeln((
                        'Failed to load ' +  plugin + '/' + (config.grunt.file || 'Gruntfile.js') + ':'
                    ).yellow);
                    grunt.log.writeln('>>> ' + e.toString().split('\n').join('\n>>> ').yellow);
                }

                // add default targets
                _(config.grunt.defaultTargets || []).each(function (target) {
                    grunt.config.set('default.' + target, {});
                });
            }
        });

    /**
     * Create a task alias for all plugin npm installs.
     */
    grunt.registerTask(
        'plugin-install',
        'Run npm install in plugin directories',
        _(grunt.config.get('plugin-install')).keys()
    );

    /**
     * Register a "meta" task that will configure and run other tasks
     * to build a plugin.  Keys in the config for this task should be the
     * directory of the plugin with in the base plugins path.
     */
    grunt.registerMultiTask('plugin', 'Build and configure plugins', function () {
        var plugin = this.target;

        this.requiresConfig('pluginDir');

        // configure "watch" tasks
        grunt.config.set(['watch', 'plugin-' + plugin + '-jade'], {
            files: _.pluck(grunt.config.get('jade.plugin.files'), 'src'),
            tasks: ['jade:plugin:' + plugin]
        });
        grunt.config.set(['watch', 'plugin-' + plugin + '-stylus'], {
            files: _.pluck(grunt.config.get('stylus.plugin.files'), 'src'),
            tasks: ['stylus:plugin:' + plugin]
        });
        grunt.config.set(['watch', 'plugin-' + plugin + '-uglify'], {
            files: _.pluck(grunt.config.get('uglify.plugin.files'), 'src'),
            tasks: ['uglify:plugin:' + plugin]
        });
        grunt.config.set(['watch', 'plugin-' + plugin + '-copy'], {
            files: _.pluck(grunt.config.get('copy.plugin.files'), 'src'),
            tasks: ['copy:plugin:' + plugin]
        });
        grunt.config.set(['watch', 'plugin-' + plugin + '-install'], {
            files: [
                path.resolve(
                    grunt.config.get('pluginDir'),
                    plugin,
                    'package.json'
                )
            ],
            tasks: ['shell:plugin-install:' + plugin]
        });

        // queue the generic build tasks
        grunt.task.run('jade:plugin:' + plugin);
        grunt.task.run('uglify:plugin:' + plugin);
        grunt.task.run('stylus:plugin:' + plugin);
        grunt.task.run('copy:plugin:' + plugin);

        grunt.loadNpmTasks('grunt-contrib-watch');
    });
};
