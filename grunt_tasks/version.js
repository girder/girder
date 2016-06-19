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
 * Define a task to get version information from the repository.
 */
module.exports = function (grunt) {
    // Returns a JSON string containing information from the current Git repository.
    var versionInfoObject = function () {
        // extract information from the config
        var gitVersion = grunt.config.get('gitinfo');
        var local = gitVersion.local || {};
        var branch = local.branch || {};
        var current = branch.current || {};

        return JSON.stringify(
            {
                git: !!current.SHA,
                SHA: current.SHA,
                shortSHA: current.shortSHA,
                date: grunt.template.date(new Date(), 'isoDateTime', true),
                apiVersion: grunt.config.get('pkg').version
            },
            null,
            '  '
        );
    };

    grunt.config.merge({
        'file-creator': {
            'python-version': {
                'girder/girder-version.json': function (fs, fd, done) {
                    var girderVersion = versionInfoObject();
                    fs.writeSync(fd, girderVersion);
                    done();
                }
            },

            'javascript-version': {
                'clients/web/src/version.js': function (fs, fd, done) {
                    var girderVersion = versionInfoObject();
                    fs.writeSync(
                        fd, [
                            '/*eslint-disable */',
                            '// THIS FILE IS AUTO-GENERATED',
                            'var versionInfo = ',
                            girderVersion,
                            ';',
                            'export default versionInfo;',
                            '/*eslint-enable */'
                        ].join('\n') + '\n'
                    );
                    done();
                }
            }
        },
        default: {
            'version-info': {}
        }
    });

    grunt.registerTask('version-info', [
        'gitinfo',
        'file-creator:python-version',
        'file-creator:javascript-version'
    ]);
};
