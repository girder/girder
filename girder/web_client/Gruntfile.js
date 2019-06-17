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
        girderVersion: grunt.option('girder-version') || null,
        staticPublicPath: grunt.option('static-public-path') || '/static',
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
