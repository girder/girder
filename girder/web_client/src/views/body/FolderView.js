import _ from 'underscore';

import FolderModel from '@girder/core/models/FolderModel';
import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import View from '@girder/core/views/View';
import { cancelRestRequests } from '@girder/core/rest';
import events from '@girder/core/events';

/**
 * This view shows a single folder as a hierarchy widget.
 */
var FolderView = View.extend({
    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.folder = settings.folder;
        this.upload = settings.upload || false;
        this.folderAccess = settings.folderAccess || false;
        this.folderCreate = settings.folderCreate || false;
        this.folderEdit = settings.folderEdit || false;
        this.itemCreate = settings.itemCreate || false;

        this.render();
    },

    render: function () {
        this.hierarchyWidget = new HierarchyWidget({
            el: this.$el,
            parentModel: this.folder,
            upload: this.upload,
            folderAccess: this.folderAccess,
            folderEdit: this.folderEdit,
            folderCreate: this.folderCreate,
            itemCreate: this.itemCreate,
            parentView: this
        });

        return this;
    }
}, {
    /**
     * Helper function for fetching the folder by id, then render the view.
     */
    fetchAndInit: function (id, params) {
        var folder = new FolderModel();
        folder.set({ _id: id }).on('g:fetched', function () {
            events.trigger('g:navigateTo', FolderView, _.extend({
                folder: folder
            }, params || {}));
        }, this).fetch();
    }

});

export default FolderView;
