import FilesystemImportTemplate from 'girder/templates/body/filesystemImport.jade';
import router                   from 'girder/router';
import View                     from 'girder/view';

export var FilesystemImportView = View.extend({
    events: {
        'submit .g-filesystem-import-form': function (e) {
            e.preventDefault();

            var destId = this.$('#g-filesystem-import-dest-id').val().trim(),
                destType = this.$('#g-filesystem-import-dest-type').val();

            this.$('.g-validation-failed-message').empty();

            this.assetstore.off('g:imported').on('g:imported', function () {
                router.navigate(destType + '/' + destId, {trigger: true});
            }, this).on('g:error', function (resp) {
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            }, this).import({
                importPath: this.$('#g-filesystem-import-path').val().trim(),
                destinationId: destId,
                destinationType: destType,
                progress: true
            });
        }
    },

    initialize: function (settings) {
        this.assetstore = settings.assetstore;
        this.render();
    },

    render: function () {
        this.$el.html(FilesystemImportTemplate({
            assetstore: this.assetstore
        }));
    }
});
