module.exports = function (grunt) {
    grunt.initConfig({
        clean: {
            dist: ['dist', '.fontello-session'],
            extra: [
                'dist/css/fontello-codes.css',
                'dist/css/fontello-embedded.css',
                'dist/css/fontello-ie7.css',
                'dist/css/fontello-ie7-codes.css'
            ]
        },
        shell: {
            dist: {
                command: 'fontello-cli install --config fontello.config.json --css dist/css --font dist/fonts --host https://fontello.com'
            },
            adjust: {
                command: "sed -i 's/\\/font\\//\\/fonts\\//g' dist/css/fontello.css"
            }
        }
    });

    grunt.loadNpmTasks('grunt-contrib-clean');
    grunt.loadNpmTasks('grunt-shell');

    grunt.registerTask('default', ['clean:dist', 'shell:dist', 'shell:adjust', 'clean:extra']);
};
