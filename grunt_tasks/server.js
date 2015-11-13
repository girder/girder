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
 * Define a task to set server information variables in the grunt config.
 */
module.exports = function (grunt) {
    var setServerConfig = function (err, stdout, stderr, callback) {
        var cfg, apiRoot, staticRoot;

        if (err) {
            grunt.fail.fatal('config_parse failed on local.server.cfg: ' + stderr);
        }
        try {
            cfg = JSON.parse(stdout);
            apiRoot = ((cfg.server && cfg.server.api_root) || '/api/v1').replace(/\"/g, '');
            staticRoot = ((cfg.server && cfg.server.static_root) || '/static').replace(/\"/g, '');
            grunt.config.set('serverConfig', {
                staticRoot: staticRoot,
                apiRoot: apiRoot
            });
            console.log('Static root: ' + staticRoot.bold);
            console.log('API root: ' + apiRoot.bold);
        }
        catch (e) {
            grunt.warn('Invalid JSON from config_parse: ' + stdout);
        }
        callback();
    };

    grunt.config.merge({
        shell: {
            readServerConfig: {
                command: 'env python config_parse.py ' +
                         grunt.config.get('girderDir') + '/conf/girder.local.cfg',
                options: {
                    stdout: false,
                    callback: setServerConfig
                }
            }
        },
        init: {
            'shell:readServerConfig': {
                dependencies: ['setup']
            }
        },
        default: {
            'shell:readServerConfig': {}
        }
    });
};
