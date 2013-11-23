/**
 * This widget is for creating new assetstores. The parent view is responsible
 * for checking admin privileges before rendering this widget.
 */
girder.views.NewAssetstoreWidget = Backbone.View.extend({
    events: {
        'submit #g-new-fs-form': function (e) {
            this.createAssetstore(e, this.$('#g-new-fs-error'), {
                type: girder.AssetstoreType.FILESYSTEM,
                name: this.$('#g-new-fs-name').val(),
                root: this.$('#g-new-fs-root').val()
            });
        },

        'submit #g-new-gridfs-form': function (e) {
            this.createAssetstore(e, this.$('#g-new-gridfs-error'), {
                type: girder.AssetstoreType.GRIDFS,
                name: this.$('#g-new-gridfs-name').val(),
                db: this.$('#g-new-gridfs-db').val()
            });
        },

        'submit #g-new-s3-form': function (e) {
            this.createAssetstore(e, this.$('#g-new-s3-error'), {
                type: girder.AssetstoreType.S3,
                name: this.$('#g-new-s3-name').val()
            });
        }
    },

    render: function () {
        this.$el.html(jade.templates.newAssetstore());
        return this;
    },

    /**
     * Call this to make the request to the server to create the assetstore.
     * @param e The submit event from the form.
     * @param container The element to write the error message into.
     * @param data The form data to POST to /assetstore
     */
    createAssetstore: function (e, container, data) {
        e.preventDefault();
        this.$('.g-new-assetstore-submit').addClass('disabled');
        container.empty();

        girder.restRequest({
            path: 'assetstore',
            type: 'POST',
            data: data,
            error: null
        }).done(_.bind(function (assetstore) {
            this.trigger('g:created', assetstore);
        }, this)).error(_.bind(function (err) {
            container.text(err.responseJSON.message);
        }, this)).complete(_.bind(function () {
            this.$('.g-new-assetstore-submit').removeClass('disabled');
        }, this));
    }
});
