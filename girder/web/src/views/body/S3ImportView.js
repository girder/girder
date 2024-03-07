import $ from 'jquery';

import BrowserWidget from '@girder/core/views/widgets/BrowserWidget';
import router from '@girder/core/router';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';

import S3ImportTemplate from '@girder/core/templates/body/s3Import.pug';

var S3ImportView = View.extend({
    events: {
        'submit .g-s3-import-form': function (e) {
            e.preventDefault();

            var destId = this.$('#g-s3-import-dest-id').val().trim().split(/\s/)[0],
                destType = this.$('#g-s3-import-dest-type').val();

            this.$('.g-validation-failed-message').empty();

            this.assetstore.off('g:imported').on('g:imported', function () {
                router.navigate(destType + '/' + destId, { trigger: true });
            }, this).on('g:error', function (resp) {
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            }, this).import({
                importPath: this.$('#g-s3-import-path').val().trim(),
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
            validate: function (model) {
                const isValid = $.Deferred();
                if (!model) {
                    isValid.reject('Please select a valid root.');
                } else {
                    isValid.resolve();
                }
                return isValid.promise();
            }
        });
        this.listenTo(this._browserWidgetView, 'g:saved', function (val) {
            this.$('#g-s3-import-dest-id').val(val.id);
            this.$('#g-s3-import-dest-type').val(val.get('_modelType'));
            restRequest({
                url: `resource/${val.id}/path`,
                method: 'GET',
                data: { type: val.get('_modelType') }
            }).done((result) => {
                // Only add the resource path if the value wasn't altered
                if (this.$('#g-s3-import-dest-id').val() === val.id) {
                    this.$('#g-s3-import-dest-id').val(`${val.id} (${result})`);
                }
            });
        });
        this.assetstore = settings.assetstore;
        this.render();
    },

    render: function () {
        this.$el.html(S3ImportTemplate({
            assetstore: this.assetstore
        }));
        return this;
    },

    _openBrowser: function () {
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    }
});

export default S3ImportView;
