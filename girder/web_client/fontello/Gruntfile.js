module.exports = function(grunt) {
    grunt.initConfig({
        clean: [
            'dist',
        ],
        fontello: {
            dist: {
                options: {
                    config: 'fontello.config.json',
                    fonts: 'dist/fonts',
                    styles: 'dist/css',
                    exclude: [
                        'fontello-codes.css',
                        'fontello-embedded.css',
                        'fontello-ie7.css',
                        'fontello-ie7-codes.css',
                    ],
                    force: true
                }
            }
        },
    });

    grunt.loadNpmTasks('grunt-contrib-clean');
    grunt.loadNpmTasks('grunt-fontello');

    grunt.registerTask('default', ['clean', 'fontello']);
};
