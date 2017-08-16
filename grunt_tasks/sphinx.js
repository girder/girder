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
 * Define tasks that build sphinx documentation.
 */
module.exports = function (grunt) {
    grunt.config.merge({
        shell: {
            sphinx: {
                command: 'make html',
                cwd: 'docs'
            },
            sphinx_clean: {
                command: 'make clean',
                cwd: 'docs'
            }
        }
    });

    grunt.registerTask('docs', function (target) {
        let tasks = ['shell:sphinx'];
        if (target === 'clean') {
            tasks.unshift('shell:sphinx_clean');
        }
        grunt.task.run(tasks);
    });
};
