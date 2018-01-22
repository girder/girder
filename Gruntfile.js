/**
 * Copyright 2013 Kitware Inc.
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

const fs = require('fs');
const path = require('path');

require('colors');
const toposort = require('toposort');
const _ = require('underscore');

/**
 * This function takes an object like `grunt.config.get('default')` and
 * returns a topologically sorted array of tasks.
 */
function sortTasks(obj) {
    var nodes = _.keys(obj);
    var edges = _(obj).chain()
        .pairs()
        .map(function (o) {
            return _.map(o[1].dependencies || [], function (d) {
                return [d, o[0]];
            });
        })
        .flatten(true)
        .value();
    var sorted = toposort.array(nodes, edges);

    // We need to ensure that the npm install task is run first.
    // This is currently necessary because some external plugins
    // don't specify any external tasks as dependencies.
    var installIndex = _.indexOf(sorted, 'npm-install-plugins');
    if (installIndex >= 0) {
        sorted.splice(installIndex, 1);
        sorted.splice(0, 0, 'npm-install-plugins');
    }
    return sorted;
}

module.exports = function (grunt) {
    var isSourceBuild = fs.existsSync('girder/__init__.py');
    var environment = grunt.option('env') || 'dev';

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    // Project configuration.
    grunt.config.init({
        environment: environment,
        pkg: grunt.file.readJSON('package.json'),
        pluginDir: 'plugins',
        staticDir: '.',
        builtPath: path.resolve(grunt.option('static-path') || '.', 'built'),
        isSourceBuild: isSourceBuild,
        default: {}
    });

    if (isSourceBuild) {
        // We are in a source tree
        grunt.config.set('girderDir', 'girder');
    } else {
        // We are in an installed package
        grunt.config.set('girderDir', '.');
    }

    // Ensure our build directory exists
    try {
        fs.mkdirSync('built');
    } catch (e) {
        if (e.code !== 'EEXIST') {
            throw e;
        }
    }

    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-contrib-pug');
    grunt.loadNpmTasks('grunt-contrib-stylus');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-file-creator');
    grunt.loadNpmTasks('grunt-gitinfo');
    grunt.loadNpmTasks('grunt-shell');
    grunt.loadNpmTasks('grunt-webpack');
    grunt.loadNpmTasks('grunt-zip');

    /**
     * Load task modules inside `grunt_tasks`.
     */
    grunt.loadTasks('grunt_tasks');

    /**
     * This task is noop that exists for backwards compatibility in case any plugins rely
     * on its existence.
     * @deprecated: remove in v3
     */
    grunt.registerTask('init', 'This task is deprecated, in favor of "default".', _.constant(true));
    grunt.config.merge({
        default: grunt.config.get('init')
    });

    /**
     * Load `default` target by topologically sorting the tasks given by keys the config object.
     * As in:
     * {
     *   'default': {
     *     'copy:a': {}
     *     'uglify:a': {
     *       'dependencies': ['copy:a']
     *     }
     *   }
     * }
     *
     * The 'default' task will run `copy:a` followed by `uglify:a`.
     */
    grunt.registerTask('default', sortTasks(grunt.config.get('default')));
};
