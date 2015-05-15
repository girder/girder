girder.views.S3ImportView = girder.View.extend({
    events: {
        'submit .g-s3-import-form': function (e) {
            e.preventDefault();

            this.assetstore.off('g:imported').on('g:imported', function () {
                console.log('done!');
            }, this).import({
                importPath: this.$('#g-s3-import-path').val().trim(),
                destinationId: this.$('#g-s3-import-dest-id').val().trim(),
                destinationType: this.$('#g-s3-import-dest-type').val()
            });
        }
    },

    initialize: function (settings) {
        this.assetstore = settings.assetstore;
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.s3Import({
            assetstore: this.assetstore
        }));
    }
});

girder.router.route('assetstore/:id/s3import', 's3Import', function (assetstoreId) {
    var assetstore = new girder.models.AssetstoreModel({
        _id: assetstoreId
    });

    assetstore.once('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.S3ImportView, {
            assetstore: assetstore
        });
    }).fetch();
});
