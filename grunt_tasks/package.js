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
 * Define tasks related to packaging girder for release.
 */
module.exports = function (grunt) {

    var fs = require('fs');

    grunt.config.merge({
        shell: {
            // create girder-[version].tar.gz
            'package-server': {
                command: 'env python setup.py sdist --dist-dir .',
                options: {
                    stdout: false,
                    callback: function (err, stdout, stderr, callback) {
                        grunt.config.requires('pkg.version');

                        var fname = 'girder-' +
                            grunt.config.get('pkg').version +
                            '.tar.gz';
                        var stat = fs.statSync(fname);
                        if (!err && stat.isFile() && stat.size > 0) {
                            grunt.verbose.write(stdout);
                            grunt.log
                                .write('Created ')
                                .write(grunt.log.wordlist([fname]))
                                .write(' (' + stat.size + ' bytes)\n');
                        } else {
                            grunt.verbose.write(stdout).write(stderr).write('\n');
                            grunt.fail.warn('python setup.py sdist failed.');
                        }
                        callback();
                    }
                }
            }
        },
        compress: {
            // create girder-web-[version].tar.gz
            'package-web': {
                options: {
                    mode: 'tgz',
                    archive: function () {
                        grunt.config.requires('pkg.version');
                        return 'girder-web-' +
                            grunt.config.get('pkg').version +
                            '.tar.gz';
                    },
                    level: 9
                },
                expand: true,
                cwd: 'clients/web',
                src: ['lib/**', 'static/**'],
                dest: 'clients/web/'
            },
            // create girder-plugins-[version].tar.gz
            'package-plugins': {
                options: {
                    mode: 'tgz',
                    archive: function () {
                        grunt.config.requires('pkg.version');
                        return 'girder-plugins-' +
                            grunt.config.get('pkg').version +
                            '.tar.gz';
                    },
                    level: 9
                },
                expand: true,
                cwd: 'plugins',
                src: ['**'],
                dest: '',
                filter: function (fname) {
                    return !fname.match(/\/plugin_tests/) &&
                           !fname.match(/cmake$/) &&
                           !fname.match(/py[co]$/);
                }
            }
        }
    });

    // Remove all old packaging files
    grunt.registerTask('remove-packaging', function () {
        // match things that look like girder packages
        grunt.file.expand('girder-*.tar.gz').forEach(function (f) {
            // use regex's to further filter
            if (f.match(/girder(-web-|-plugins-|-)[0-9]+\.[0-9]+.[0-9]+.*\.tar\.gz/)) {
                grunt.file.delete(f);
            }
        });
    });

    // Create tarballs for distribution through pip and github releases
    grunt.registerTask('package', 'Generate a python package for distribution.', [
        'remove-packaging',
        'compress:package-web',
        'compress:package-plugins',
        'shell:package-server'
    ]);

};
