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
    var fs = require('fs');
    var path = require('path');
    var defaultTasks = grunt.config.get('defaultTasks');

    // bring plugin Grunt targets into default Girder Grunt tasks
    var extractPluginGruntTargets = function (pluginDir) {
        var pluginJson = pluginDir + '/plugin.json',
            pluginYml = pluginDir + '/plugin.yml',
            pluginConfigFile;

        if (fs.existsSync(pluginJson)) {
            pluginConfigFile = pluginJson;
        } else if (fs.existsSync(pluginYml)) {
            pluginConfigFile = pluginYml;
        } else {
            return;
        }

        var pluginDescription = grunt.file.readYAML(pluginConfigFile);
        if (pluginDescription.hasOwnProperty('grunt')) {
            console.log(('Found plugin: ' + path.basename(pluginDir) +
                         ' (custom Gruntfile)').bold);

            var pluginGruntCfg = pluginDescription.grunt;

            // Merge plugin Grunt file
            require('./' + pluginDir + '/' + pluginGruntCfg.file)(grunt);

            // Register default targets
            if (pluginGruntCfg.defaultTargets) {
                pluginGruntCfg.defaultTargets.forEach(function (defaultTarget) {
                    defaultTasks.push(defaultTarget);
                });
            }
        }
    };

    // Configure a given plugin for building
    var configurePlugin = function (pluginDir) {
        var pluginName = path.basename(pluginDir);
        var staticDir = 'clients/web/static/built/plugins/' + pluginName;

        console.log(('Found plugin: ' + pluginName).bold);

        if (!fs.existsSync(staticDir)) {
            fs.mkdirSync(staticDir);
        }

        var files;
        var jadeDir = pluginDir + '/web_client/templates';
        if (fs.existsSync(jadeDir)) {
            files = {};
            files[staticDir + '/templates.js'] = [jadeDir + '/**/*.jade'];
            grunt.config.set('jade.plugin_' + pluginName, {
                files: files
            });
            grunt.config.set('watch.jade_' + pluginName, {
                files: [jadeDir + '/**/*.jade'],
                tasks: ['jade:plugin_' + pluginName, 'uglify:plugin_' + pluginName]
            });
        }

        var cssDir = pluginDir + '/web_client/stylesheets';
        if (fs.existsSync(cssDir)) {
            files = {};
            files[staticDir + '/plugin.min.css'] = [cssDir + '/**/*.styl'];
            grunt.config.set('stylus.plugin_' + pluginName, {
                files: files
            });
            grunt.config.set('watch.stylus_' + pluginName, {
                files: [cssDir + '/**/*.styl'],
                tasks: ['stylus:plugin_' + pluginName]
            });
        }

        var jsDir = pluginDir + '/web_client/js';
        if (fs.existsSync(jsDir)) {
            files = {};
            files[staticDir + '/plugin.min.js'] = [
                staticDir + '/templates.js',
                jsDir + '/**/*.js'
            ];
            grunt.config.set('uglify.plugin_' + pluginName, {
                files: files
            });
            grunt.config.set('watch.js_' + pluginName, {
                files: [jsDir + '/**/*.js'],
                tasks: ['uglify:plugin_' + pluginName]
            });
            defaultTasks.push('uglify:plugin_' + pluginName);
        }

        var extraDir = pluginDir + '/web_client/extra';
        if (fs.existsSync(extraDir)) {
            grunt.config.set('copy.plugin_' + pluginName, {
                expand: true,
                cwd: pluginDir + '/web_client',
                src: ['extra/**'],
                dest: staticDir
            });
            grunt.config.set('watch.copy_' + pluginName, {
                files: [extraDir + '/**/*'],
                tasks: ['copy:plugin_' + pluginName]
            });
            defaultTasks.push('copy:plugin_' + pluginName);
        }

        // Handle external grunt targets specified for the plugin
        extractPluginGruntTargets(pluginDir);
    };

    // Glob for front-end plugins and configure each one to build
    var pluginDirs = grunt.file.expand('plugins/*');

    if (!fs.existsSync('clients/web/static/built/plugins')) {
        fs.mkdirSync('clients/web/static/built/plugins');
    }

    pluginDirs.forEach(function (pluginDir) {
        if (fs.existsSync(pluginDir + '/web_client')) {
            configurePlugin(pluginDir);
        } else {
            // plugins lacking a web_client dir might have grunt tasks
            extractPluginGruntTargets(pluginDir);
        }
    });

};
