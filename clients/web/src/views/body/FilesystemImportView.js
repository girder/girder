import BrowserWidget from 'girder/views/widgets/BrowserWidget';
import router from 'girder/router';
import View from 'girder/views/View';

import FilesystemImportTemplate from 'girder/templates/body/filesystemImport.pug';

var FilesystemImportView = View.extend({
    events: {
        'submit .g-filesystem-import-form': function (e) {
            e.preventDefault();

            var destId = this.$('#g-filesystem-import-dest-id').val().trim(),
                destType = this.$('#g-filesystem-import-dest-type').val(),
                foldersAsItems = this.$('#g-filesystem-import-leaf-items').val();

            this.$('.g-validation-failed-message').empty();

            this.assetstore.off('g:imported').on('g:imported', function () {
                router.navigate(destType + '/' + destId, {trigger: true});
            }, this).on('g:error', function (resp) {
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            }, this).import({
                importPath: this.$('#g-filesystem-import-path').val().trim(),
                leafFoldersAsItems: foldersAsItems,
                destinationId: destId,
                destinationType: destType,
                progress: true
            });
        },
        'click .g-open-browser': '_openBrowser'
    },

    initialize: function (settings) {
        this._browserWidgetView = new BrowserWidget({
            parentView: this,
            titleText: 'Destination',
            helpText: 'Browse to a location to select it as the destination.',
            submitText: 'Select Destination',
            validate: function (id) {
                if (!id) {
                    return 'Please select a valid root.';
                }
            }
        });
        this.listenTo(this._browserWidgetView, 'g:saved', function (val) {
            this.$('#g-filesystem-import-dest-id').val(val);
        });
        this.assetstore = settings.assetstore;
        this.render();
    },

    render: function () {
        this.$el.html(FilesystemImportTemplate({
            assetstore: this.assetstore
        }));
    },

    _openBrowser: function () {
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    }
});

export default FilesystemImportView;
