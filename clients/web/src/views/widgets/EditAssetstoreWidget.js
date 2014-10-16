/**
 * This widget is used to edit an existing assetstore.
 */
girder.views.EditAssetstoreWidget = girder.View.extend({
    events: {
        'submit #g-assetstore-edit-form': function (e) {
            e.preventDefault();

            var view = this;
            var fields;
            if (view.model.get('type') === girder.AssetstoreType.FILESYSTEM) {
                fields = {
                    name: this.$('#g-edit-name').val(),
                    root: this.$('#g-edit-fs-root').val()
                };
            } else if (view.model.get('type') === girder.AssetstoreType.GRIDFS) {
                fields = {
                    name: this.$('#g-edit-name').val(),
                    db: this.$('#g-edit-gridfs-db').val()
                };
            } else if (view.model.get('type') === girder.AssetstoreType.S3) {
                fields = {
                    name: this.$('#g-edit-name').val(),
                    bucket: this.$('#g-edit-s3-bucket').val(),
                    prefix: this.$('#g-edit-s3-prefix').val(),
                    accessKeyId: this.$('#g-edit-s3-access-key-id').val(),
                    secret: this.$('#g-edit-s3-secret').val(),
                    service: this.$('#g-edit-s3-service').val()
                };
            }
            this.updateAssetstore(fields);

            this.$('button.g-save-assetstore').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        }
    },

    initialize: function (settings) {
        this.model = settings.model || null;
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.editAssetstoreWidget({
            assetstore: view.model,
            types: girder.AssetstoreType
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-edit-name').val(view.model.get('name'));
            if (view.model.get('type') === girder.AssetstoreType.FILESYSTEM) {
                view.$('#g-edit-fs-root').val(view.model.get('root'));
            } else if (view.model.get('type') === girder.AssetstoreType.GRIDFS) {
                view.$('#g-edit-gridfs-db').val(view.model.get('db'));
            } else if (view.model.get('type') === girder.AssetstoreType.S3) {
                view.$('#g-edit-s3-bucket').val(view.model.get('bucket'));
                view.$('#g-edit-s3-prefix').val(view.model.get('prefix'));
                view.$('#g-edit-s3-access-key-id').val(view.model.get('accessKeyId'));
                view.$('#g-edit-s3-secret').val(view.model.get('secret'));
                view.$('#g-edit-s3-service').val(view.model.get('service'));
            }
            view.$('#g-edit-name').focus();
        }).on('hidden.bs.modal', function () {
            girder.dialogs.handleClose('edit');
        });
        this.$('#g-name').focus();

        girder.dialogs.handleOpen('edit');

        return this;
    },

    updateAssetstore: function (fields) {
        var oldfields = {};
        for (var key in fields) {
            if (fields.hasOwnProperty(key)) {
                oldfields[key] = this.model.get(key);
            }
        }
        this.model.set(fields);
        this.model.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.model);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-assetstore').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
            this.model.set(oldfields);
        }, this).save();
    }
});
