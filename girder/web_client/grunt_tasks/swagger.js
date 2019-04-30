const path = require('path');

/**
 * Define tasks that copy and configure swagger API/doc files.
 */
module.exports = function (grunt) {
    const builtPath = path.resolve(grunt.config.get('builtPath'), 'swagger');
    // require.resolve('@girder/core') finds the main index.js
    const webSrc = path.dirname(require.resolve('@girder/core'));
    grunt.config.merge({
        copy: {
            swagger: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/swagger-ui/dist',
                    src: ['lib/**', 'css/**', 'images/**', 'swagger-ui.min.js'],
                    dest: builtPath
                }]
            },
            'girder-swagger': {
                files: [{
                    expand: true,
                    cwd: 'static',
                    src: ['girder-swagger.js'],
                    dest: builtPath
                }]
            }
        },

        stylus: {
            swagger: {
                files: {
                    [path.resolve(builtPath, 'docs.css')]: [
                        path.resolve(webSrc, 'stylesheets/apidocs/*.styl')
                    ]
                }
            }
        },

        default: {
            'copy:swagger': {},
            'copy:girder-swagger': {},
            'stylus:swagger': {}
        }
    });
};
