import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';
import View from '@girder/core/views/View';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

import ThumbnailModel from '../models/ThumbnailModel';

import CreateThumbnailViewDialogTemplate from '../templates/createThumbnailViewDialog.pug';
import CreateThumbnailViewTargetDescriptionTemplate from '../templates/createThumbnailViewTargetDescription.pug';

import '../stylesheets/createThumbnailView.styl';

/**
 * A dialog for creating thumbnails from a specific file.
 */
var CreateThumbnailView = View.extend({
    events: {
        'change .g-thumbnail-attach-container input[type="radio"]': function () {
            this.$('.g-target-result-container').empty();

            if (this.$('.g-thumbnail-attach-this-item').is(':checked')) {
                this.attachToType = 'item';
                this.attachToId = this.item.id;
                this.$('.g-thumbnail-custom-target-container').addClass('hide');
                this.$('.g-submit-create-thumbnail').girderEnable(true);
            } else {
                this.attachToType = null;
                this.attachToId = null;
                this.$('.g-thumbnail-custom-target-container').removeClass('hide');
                this.$('.g-submit-create-thumbnail').girderEnable(false);
            }
        },

        'submit #g-create-thumbnail-form': function (e) {
            e.preventDefault();

            this.$('.g-validation-failed-message').empty();
            this.$('.g-submit-create-thumbnail').girderEnable(false);

            new ThumbnailModel({
                width: Number(this.$('#g-thumbnail-width').val()) || 0,
                height: Number(this.$('#g-thumbnail-height').val()) || 0,
                crop: this.$('#g-thumbnail-crop').is(':checked'),
                fileId: this.file.id,
                attachToId: this.attachToId,
                attachToType: this.attachToType
            }).on('g:saved', function () {
                this.$el.on('hidden.bs.modal', () => {
                    this.trigger('g:created', {
                        attachedToType: this.attachToType,
                        attachedToId: this.attachToId
                    });
                }).modal('hide');
            }, this).on('g:error', function (resp) {
                this.$('.g-submit-create-thumbnail').girderEnable(true);
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            }, this).save();
        }
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.file = settings.file;
        this.attachToType = 'item';
        this.attachToId = this.item.id;

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Start typing a name...',
            types: ['collection', 'folder', 'item', 'user'],
            parentView: this
        }).on('g:resultClicked', this.pickTarget, this);
    },

    render: function () {
        this.$el.html(CreateThumbnailViewDialogTemplate({
            file: this.file,
            item: this.item
        })).girderModal(this).on('shown.bs.modal', () => {
            this.$('#g-thumbnail-width').focus();
        });

        this.$('#g-thumbnail-width').focus();

        this.searchWidget.setElement(this.$('.g-search-field-container')).render();

        return this;
    },

    pickTarget: function (target) {
        this.searchWidget.resetState();
        this.attachToType = target.type;
        this.attachToId = target.id;
        this.$('.g-submit-create-thumbnail').girderEnable(true);

        this.$('.g-target-result-container').html(CreateThumbnailViewTargetDescriptionTemplate({
            text: target.text,
            icon: target.icon
        }));
    }
});

export default CreateThumbnailView;
