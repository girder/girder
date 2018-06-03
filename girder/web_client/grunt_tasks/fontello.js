/**
 * Copyright Kitware Inc.
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
const process = require('process');

const srcUrl = 'https://data.kitware.com/api/v1/file/57c5d1fc8d777f10f269dece/download';

module.exports = function (grunt) {
    const archivePath = path.resolve(grunt.config.get('builtPath'), 'fontello.zip');
    const localArchive = process.env.GIRDER_LOCAL_FONTELLO_ARCHIVE;
    let fetchTask;
    if (localArchive) {
        // Use an already existing local fontello zip file
        if (!fs.existsSync(localArchive)) {
            grunt.fail.warn(`Fontello local archive does not exist: ${localArchive}`);
        }
        grunt.log.writeln(`Using local Fontello archive: ${localArchive}`.blue);
        grunt.config.merge({
            copy: {
                fontello: {
                    files: [{
                        src: localArchive,
                        dest: archivePath
                    }]
                }
            }
        });
        fetchTask = 'copy:fontello';
    } else {
        // Download font archive from data.kitware.com
        grunt.config.merge({
            shell: {
                fontello: {
                    command: `curl "${srcUrl}" -o "${archivePath}"`
                }
            }
        });
        fetchTask = 'shell:fontello';
    }

    grunt.config.merge({
        unzip: {
            fontello: {
                src: archivePath,
                dest: path.resolve(grunt.config.get('builtPath'), 'fontello/'),
                router: function (file) {
                    // remove the first path component
                    return file.split(path.sep).slice(1).join(path.sep);
                }
            }
        }
    });

    grunt.registerTask('fontello', [
        fetchTask,
        'unzip:fontello'
    ]);
    grunt.config.merge({
        default: {
            fontello: {}
        }
    });
};
