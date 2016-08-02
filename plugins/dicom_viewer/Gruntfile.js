module.exports = function (grunt) {
    require('load-grunt-tasks')(grunt);

    grunt.config.set('webpack.dicom_viewer', require('./webpack.config.js'));

    grunt.config.set('watch.dicom_viewer', {
        files: ['plugins/dicom_viewer/**/*'],
        tasks: ['dicom_viewer']
    });

    grunt.registerTask('dicom_viewer', 'webpack:dicom_viewer');
};
