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

/**
 * This function takes an object like `grunt.config.get('init')` and
 * returns a topologically sorted array of tasks.
 */
function sortTasks(obj) {
    var toposort = require('toposort');
    var _ = require('underscore');
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
    return toposort.array(nodes, edges);
}

module.exports = function (grunt) {
    var fs = require('fs');
    var isSourceBuild = fs.existsSync('girder/__init__.py');
    require('colors');

    // Project configuration.
    grunt.config.init({
        pkg: grunt.file.readJSON('package.json'),
        pluginDir: 'plugins',
        staticDir: 'clients/web/static',
        isSourceBuild: isSourceBuild,
        init: {
            setup: {}
        },
        default: {}
    });

    if (isSourceBuild) {
        // We are in a source tree
        grunt.config.set('girderDir', 'girder');
    } else {
        // We are in an installed package
        grunt.config.set('girderDir', '.');
    }

    /**
     * Load task modules inside `grunt_tasks`.
     */
    grunt.loadTasks('grunt_tasks');
    grunt.loadNpmTasks('grunt-shell');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-stylus');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-contrib-symlink');
    grunt.loadNpmTasks('grunt-gitinfo');
    grunt.loadNpmTasks('grunt-curl');
    grunt.loadNpmTasks('grunt-zip');
    grunt.loadNpmTasks('grunt-file-creator');
    grunt.loadNpmTasks('grunt-npm-install');
    grunt.loadNpmTasks('grunt-webpack');

    // This task should be run once manually at install time.
    grunt.registerTask('setup', 'Initial install/setup tasks', function () {
        // If the local config file doesn't exist, we make it
        var confDir = grunt.config.get('girderDir') + '/conf';
        if (!fs.existsSync(confDir + '/girder.local.cfg')) {
            fs.writeFileSync(
                confDir + '/girder.local.cfg',
                fs.readFileSync(confDir + '/girder.dist.cfg')
            );
            console.log('Created local config file.');
        }
    });

    /**
     * Load `default` and `init` targets by topologically sorting the
     * tasks given by keys the config object.  As in:
     * {
     *   'init': {
     *     'copy:a': {}
     *     'uglify:a': {
     *       'dependencies': ['copy:a']
     *     }
     *   }
     * }
     *
     * The init task will run `copy:a` followed by `uglify:a`.
     */
    grunt.registerTask('init', sortTasks(grunt.config.get('init')));
    grunt.registerTask('default', sortTasks(grunt.config.get('default')));
};
