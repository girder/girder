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

const path = require('path');

require('colors');
const mkdirp = require('mkdirp');
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
    return sorted;
}

module.exports = function (grunt) {
    var environment = grunt.option('env') || 'dev';

    if (['dev', 'prod'].indexOf(environment) === -1) {
        grunt.fatal('The "env" argument must be either "dev" or "prod".');
    }

    // Project configuration.
    grunt.config.init({
        environment: environment,
        pkg: grunt.file.readJSON('package.json'),
        staticDir: '.',
        builtPath: path.resolve(grunt.option('static-path') || '.', 'built'),
        staticUrl: grunt.option('static-url') || '/static',
        default: {}
    });

    grunt.config.set('girderDir', path.resolve('..'));

    // Ensure our build directory exists
    try {
        mkdirp(grunt.config.get('builtPath'));
    } catch (e) {
        if (e.code !== 'EEXIST') {
            throw e;
        }
    }

    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-contrib-pug');
    grunt.loadNpmTasks('grunt-contrib-stylus');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-gitinfo');
    grunt.loadNpmTasks('grunt-webpack');

    /**
     * Load task modules inside `grunt_tasks`.
     */
    grunt.loadTasks('grunt_tasks');

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
