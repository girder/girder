import _ from 'underscore';

import { getCurrentUser } from 'girder/auth';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import View from 'girder/views/View';
import ItemModel from 'girder/models/ItemModel';
import FileModel from 'girder/models/FileModel';

import itemSelectorWidget from '../templates/itemSelectorWidget.pug';

var ItemSelectorWidget = View.extend({
    events: {
        'submit .s-new-file-select-form': '_selectButton'
    },

    initialize: function (settings) {
        if (!this.model) {
            this.model = new ItemModel();
        }
        this.rootPath = settings.rootPath || getCurrentUser();
    },

    render: function () {
        this._hierarchyView = new HierarchyWidget({
            parentView: this,
            parentModel: this.rootPath,
            checkboxes: false,
            routing: false,
            showActions: false,
            showMetadata: false,
            downloadLinks: false,
            viewLinks: false,
            onItemClick: _.bind(this._selectItem, this)
        });

        this.$el.html(
            itemSelectorWidget(this.model.attributes)
        ).girderModal(this);

        this._hierarchyView.setElement(this.$('.s-hierarchy-widget')).render();
        return this;
    },

    /**
     * Get the currently displayed path in the hierarchy view.
     */
    _path: function () {
        var path = this._hierarchyView.breadcrumbs.map(function (d) {
            return d.get('name');
        });

        if (this.model.get('type') === 'directory') {
            path = _.initial(path);
        }
        return path;
    },

    _selectItem: function (item) {
        var image, file;

        if (this.model.get('type') === 'file') {
            this.model.set({
                path: this._path(),
                value: item
            });
            this.trigger('g:saved');
            this.$el.modal('hide');
        } else if (this.model.get('type') === 'image') {
            image = item.get('largeImage');

            if (!image) {
                this.$('.s-modal-error').removeClass('hidden')
                    .text('Please select a "large_image" item.');
                return;
            }

            // For now, use the original file id rather than the large image id
            file = new FileModel({_id: image.originalId || image.fileId});
            file.once('g:fetched', _.bind(function () {
                this.model.set({
                    path: this._path(),
                    value: file
                });
                this.trigger('g:saved');
            }, this)).fetch();
            this.$el.modal('hide');
        }
    },

    _selectButton: function (e) {
        e.preventDefault();

        var inputEl = this.$('#s-new-file-name');
        var inputElGroup =  inputEl.parent();
        var fileName = inputEl.val();
        var type = this.model.get('type');
        var parent = this._hierarchyView.parentModel;
        var errorEl = this.$('.s-modal-error').addClass('hidden');

        inputElGroup.removeClass('has-error');

        switch (type) {
            case 'new-file':

                // a file name must be provided
                if (!fileName) {
                    inputElGroup.addClass('has-error');
                    errorEl.removeClass('hidden')
                        .text('You must provide a name for the new file.');
                    return;
                }

                // the parent must be a folder
                if (parent.resourceName !== 'folder') {
                    errorEl.removeClass('hidden')
                        .text('Files cannot be added under collections.');
                    return;
                }

                this.model.set({
                    path: this._path(),
                    parent: parent,
                    value: new ItemModel({
                        name: fileName,
                        folderId: parent.id
                    })
                });
                break;

            case 'directory':
                this.model.set({
                    path: this._path(),
                    value: parent
                });
                break;
        }
        this.trigger('g:saved');
        this.$el.modal('hide');
    }
});

export default ItemSelectorWidget;
