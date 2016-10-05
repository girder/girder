module.exports = function (grunt) {
    var fs = require('fs');
    var path = require('path');

    var archivePath = 'clients/web/static/built/fontello.zip';

    grunt.config.merge({
        unzip: {
            fontello: {
                src: archivePath,
                dest: 'clients/web/static/built/fontello/',
                router: function (file) {
                    // remove the first path component
                    return file.split(path.sep).slice(1).join(path.sep);
                }
            }
        }
    });

    var localArchive = process.env.GIRDER_LOCAL_FONTELLO_ARCHIVE;
    if (localArchive) {
        // Use an already existing local fontello zip file
        if (!fs.existsSync(localArchive)) {
            grunt.fail.warn('fontello local archive does not exist: ' + localArchive);
        }
        grunt.log.writeln(('Using local fontello archive: ' + localArchive).blue);
        grunt.config.merge({
            copy: {
                fontello: {
                    files: [{
                        src: localArchive,
                        dest: archivePath
                    }]
                }
            },

            init: {
                'copy:fontello': {},
                'unzip:fontello': {
                    dependencies: ['copy:fontello']
                }
            }
        });
    } else {
        // Download font archive from data.kitware.com
        grunt.config.merge({
            curl: {
                fontello: {
                    src: 'https://data.kitware.com/api/v1/file/57c5d1fc8d777f10f269dece/download',
                    dest: archivePath
                }
            },

            init: {
                'curl:fontello': {},
                'unzip:fontello': {
                    dependencies: ['curl:fontello']
                }
            }
        });
    }
};
