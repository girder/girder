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

module.exports = function (grunt) {
    const confDir = `${grunt.config.get('girderDir')}/conf`;
    const localConfigPath = `${confDir}/girder.local.cfg`;

    grunt.config.merge({
        copy: {
            'local-config': {
                src: `${confDir}/girder.dist.cfg`,
                dest: localConfigPath
            }
        }
    });

    // This task should be run once manually at install time.
    grunt.registerTask('local-config', 'Ensure the girder.local.cfg file exists', function () {
        // If the local config file doesn't exist, we make it
        if (!fs.existsSync(localConfigPath)) {
            grunt.task.run('copy:local-config');
            grunt.log.writeln('Created local config file.');
        }
    });
    grunt.config.merge({
        default: {
            'local-config': {}
        }
    });
};
