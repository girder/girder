import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import View from '@girder/core/views/View';
import { AssetstoreType } from '@girder/core/constants';

import NewAssetstoreTemplate from '@girder/core/templates/widgets/newAssetstore.pug';

import 'bootstrap/js/collapse';
import 'bootstrap/js/transition';

import '@girder/core/utilities/jquery/girderEnable';

/**
 * This widget is for creating new assetstores. The parent view is responsible
 * for checking admin privileges before rendering this widget.
 */
var NewAssetstoreWidget = View.extend({
    events: {
        'submit #g-new-fs-form': function (e) {
            this.createAssetstore(e, this.$('#g-new-fs-error'), {
                type: AssetstoreType.FILESYSTEM,
                name: this.$('#g-new-fs-name').val(),
                root: this.$('#g-new-fs-root').val()
            });
        },

        'submit #g-new-gridfs-form': function (e) {
            this.createAssetstore(e, this.$('#g-new-gridfs-error'), {
                type: AssetstoreType.GRIDFS,
                name: this.$('#g-new-gridfs-name').val(),
                db: this.$('#g-new-gridfs-db').val(),
                mongohost: this.$('#g-new-gridfs-mongohost').val(),
                replicaset: this.$('#g-new-gridfs-replicaset').val(),
                shard: this.$('#g-new-gridfs-shard-auto').is(':checked') ? 'auto' : false
            });
        },

        'submit #g-new-s3-form': function (e) {
            this.createAssetstore(e, this.$('#g-new-s3-error'), {
                type: AssetstoreType.S3,
                name: this.$('#g-new-s3-name').val(),
                bucket: this.$('#g-new-s3-bucket').val(),
                prefix: this.$('#g-new-s3-prefix').val(),
                accessKeyId: this.$('#g-new-s3-access-key-id').val(),
                secret: this.$('#g-new-s3-secret').val(),
                service: this.$('#g-new-s3-service').val(),
                region: this.$('#g-new-s3-region').val(),
                readOnly: this.$('#g-new-s3-readonly').is(':checked'),
                inferCredentials: this.$('#g-new-s3-infercredentials').is(':checked'),
                serverSideEncryption: this.$('#g-new-s3-sse').is(':checked')
            });
        }
    },

    render: function () {
        this.$el.html(NewAssetstoreTemplate());
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
        this.$('.g-new-assetstore-submit').girderEnable(false);
        container.empty();

        var assetstore = new AssetstoreModel();
        assetstore.set(data);
        assetstore.on('g:saved', function () {
            this.$('.g-new-assetstore-submit').girderEnable(true);
            this.trigger('g:created', assetstore);
        }, this).on('g:error', function (err) {
            this.$('.g-new-assetstore-submit').girderEnable(true);
            container.text(err.responseJSON.message);
        }, this).save();
    }
});

export default NewAssetstoreWidget;
