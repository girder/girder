import _ from 'underscore';

import { getCurrentUser } from 'girder/auth';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import RootSelectorWidget from 'girder/views/widgets/RootSelectorWidget';
import View from 'girder/views/View';
import ItemModel from 'girder/models/ItemModel';
import FileModel from 'girder/models/FileModel';
import { restRequest } from 'girder/rest';

import itemSelectorWidget from '../templates/itemSelectorWidget.pug';

var ItemSelectorWidget = View.extend({
    events: {
        'submit .g-new-file-select-form': '_selectButton'
    },

    initialize: function (settings) {
        if (!this.model) {
            this.model = new ItemModel();
        }
        this.root = settings.root || getCurrentUser();

        this._rootSelectionView = new RootSelectorWidget(_.extend({
            parentView: this
        }, settings.rootSelectorSettings));
        this.listenTo(this._rootSelectionView, 'g:selected', function (event) {
            this.root = event.root;
            this._renderHierarchyView();
        });
    },

    render: function () {
        this.$el.html(
            itemSelectorWidget(this.model.attributes)  // eslint-disable-line backbone/no-view-model-attributes
        ).girderModal(this);

        this._renderRootSelection();
        return this;
    },

    _renderRootSelection: function () {
        this._rootSelectionView.setElement(this.$('.g-hierarchy-root-container')).render();
        this._renderHierarchyView();
    },

    _renderHierarchyView: function () {
        if (this._hierarchyView) {
            this.stopListening(this._hierarchyView);
            this._hierarchyView.off();
            this.$('.g-hierarchy-widget-container').empty();
        }
        if (!this.root) {
            return;
        }
        this.$('.g-wait-for-root').removeClass('hidden');
        this._hierarchyView = new HierarchyWidget({
            el: this.$('.g-hierarchy-widget-container'),
            parentView: this,
            parentModel: this.root,
            checkboxes: false,
            routing: false,
            showActions: false,
            showMetadata: false,
            downloadLinks: false,
            viewLinks: false,
            onItemClick: _.bind(this._selectItem, this)
        });
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

        switch (this.model.get('type')) {
            case 'item':
                this.model.set({
                    path: this._path(),
                    value: item
                });
                this.trigger('g:saved');
                this.$el.modal('hide');
                break;
            case 'file':
                restRequest({path: '/item/' + item.id + '/files', data: {limit: 1}}).done((resp) => {
                    if (!resp.length) {
                        this.$('.g-modal-error').removeClass('hidden')
                            .text('Please select an item with at least one file.');
                        return;
                    }
                    file = new FileModel({_id: resp[0]._id});
                    file.once('g:fetched', _.bind(function () {
                        this.model.set({
                            path: this._path(),
                            value: file
                        });
                        this.trigger('g:saved');
                    }, this)).fetch();
                    this.$el.modal('hide');
                }).fail(() => {
                    this.$('.g-modal-error').removeClass('hidden')
                        .text('There was an error listing files for the selected item.');
                });
                break;
            case 'image':
                image = item.get('largeImage');

                if (!image) {
                    this.$('.g-modal-error').removeClass('hidden')
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
                break;
        }
    },

    _selectButton: function (e) {
        e.preventDefault();

        var inputEl = this.$('#g-new-file-name');
        var inputElGroup =  inputEl.parent();
        var fileName = inputEl.val();
        var type = this.model.get('type');
        var parent = this._hierarchyView.parentModel;
        var errorEl = this.$('.g-modal-error').addClass('hidden');

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
