/**
 * Define tasks that download and copy fontello font files.
 */
module.exports = function (grunt) {
    var path = require('path');

    grunt.config.merge({
        curl: {
            fontello: {
                src: 'https://data.kitware.com/api/v1/file/57c5d1fc8d777f10f269dece/download',
                dest: 'clients/web/static/built/fontello.zip'
            }
        },

        unzip: {
            fontello: {
                src: 'clients/web/static/built/fontello.zip',
                dest: 'clients/web/static/built/fontello/',
                router: function (file) {
                    // remove the first path component
                    return file.split(path.sep).slice(1).join(path.sep);
                }
            }
        },

        init: {
            'curl:fontello': {},
            'unzip:fontello': {
                dependencies: ['curl:fontello']
            }
        }
    });
};
