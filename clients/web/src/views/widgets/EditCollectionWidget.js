import $ from 'jquery';

import CollectionModel from 'girder/models/CollectionModel';
import View from 'girder/views/View';
import { handleClose, handleOpen } from 'girder/utilities/DialogHelper';

import EditCollectionWidgetTemplate from 'girder/templates/widgets/editCollectionWidget.jade';

import 'bootstrap/js/modal';
import 'girder/utilities/JQuery'; // $.girderModal

/**
 * This widget is used to create a new collection or edit an existing one.
 */
var EditCollectionWidget = View.extend({
    events: {
        'submit #g-collection-edit-form': function (e) {
            e.preventDefault();

            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val()
            };

            if (this.model) {
                this.updateCollection(fields);
            } else {
                this.createCollection(fields);
            }

            this.$('button.g-save-collection').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        }
    },

    initialize: function (settings) {
        this.model = settings.model || null;
    },

    render: function () {
        var view = this;
        var modal = this.$el.html(EditCollectionWidgetTemplate({
            collection: view.model
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-name').focus();
        }).on('hidden.bs.modal', function () {
            if (view.create) {
                handleClose('create');
            } else {
                handleClose('edit');
            }
        }).on('ready.girder.modal', function () {
            if (view.model) {
                view.$('#g-name').val(view.model.get('name'));
                view.$('#g-description').val(view.model.get('description'));
                view.create = false;
            } else {
                view.create = true;
            }
        });
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));
        this.$('#g-name').focus();

        if (view.model) {
            handleOpen('edit');
        } else {
            handleOpen('create');
        }

        return this;
    },

    createCollection: function (fields) {
        var collection = new CollectionModel();
        collection.set(fields);
        collection.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', collection);
        }, this).off('g:error').on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-collection').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },

    updateCollection: function (fields) {
        this.model.set(fields);
        this.model.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.model);
        }, this).off('g:error').on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-collection').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    }
});

export default EditCollectionWidget;

