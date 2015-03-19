girder.views.hdfs_assetstore_ImportView = girder.View.extend({
    events: {
        'submit .g-hdfs-import-form': function (e) {
            e.preventDefault();
            this.$('.g-validation-failed-message').empty();
            this.$('.g-submit-hdfs-import').addClass('disabled');

            var parentType = this.$('#g-hdfs-import-dest-type').val(),
                parentId = this.$('#g-hdfs-import-dest-id').val();

            this.model.off().on('g:imported', function () {
                girder.router.navigate(parentType + '/' + parentId, {trigger: true});
            }, this).on('g:error', function (err) {
                this.$('.g-submit-hdfs-import').removeClass('disabled');
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
            }, this).hdfsImport({
                path: this.$('#g-hdfs-import-path').val(),
                parentId: parentId,
                parentType: parentType,
                progress: true
            });
        }
    },

    initialize: function () {
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.hdfs_assetstore_import({
            assetstore: this.model
        }));
    }
});

girder.router.route('hdfs_assetstore/:id/import', 'hdfsImport', function (id) {
    // Fetch the folder by id, then render the view.
    var assetstore = new girder.models.AssetstoreModel({
        _id: id
    }).once('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.hdfs_assetstore_ImportView, {
            model: assetstore
        });
    }).once('g:error', function () {
        girder.router.navigate('assetstores', {trigger: true});
    }).fetch();
});
