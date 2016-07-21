import router from 'girder/router';
import View from 'girder/views/View';

import HdfsAssetstoreImportViewTemplate from '../templates/hdfsAssetstoreImportView.jade';
import '../stylesheets/hdfsAssetstoreImportView.styl';

var HdfsAssetstoreImportView = View.extend({
    events: {
        'submit .g-hdfs-import-form': function (e) {
            e.preventDefault();
            this.$('.g-validation-failed-message').empty();
            this.$('.g-submit-hdfs-import').addClass('disabled');

            var parentType = this.$('#g-hdfs-import-dest-type').val(),
                parentId = this.$('#g-hdfs-import-dest-id').val();

            this.model.off().on('g:imported', function () {
                router.navigate(parentType + '/' + parentId, {trigger: true});
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
        this.$el.html(HdfsAssetstoreImportViewTemplate({
            assetstore: this.model
        }));
    }
});

export default HdfsAssetstoreImportView;
