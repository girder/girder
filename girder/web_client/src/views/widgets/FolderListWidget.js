import $ from 'jquery';
import _ from 'underscore';

import FolderCollection from '@girder/core/collections/FolderCollection';
import LoadingAnimation from '@girder/core/views/widgets/LoadingAnimation';
import View from '@girder/core/views/View';

import FolderListTemplate from '@girder/core/templates/widgets/folderList.pug';

/**
 * This widget shows a list of folders under a given parent.
 * Initialize this with a "parentType" and "parentId" value, which will
 * be passed to the folder GET endpoint.
 */
var FolderListWidget = View.extend({
    events: {
        'click a.g-folder-list-link': function (event) {
            event.preventDefault();
            var cid = $(event.currentTarget).attr('g-folder-cid');
            this.trigger('g:folderClicked', this.collection.get(cid));
        },
        'click a.g-show-more-folders': function () {
            this.collection.fetchNextPage();
        },
        'change .g-list-checkbox': function (event) {
            const target = $(event.currentTarget);
            const cid = target.attr('g-folder-cid');
            if (target.prop('checked')) {
                this.checked.push(cid);
            } else {
                const idx = this.checked.indexOf(cid);
                if (idx !== -1) {
                    this.checked.splice(idx, 1);
                }
            }
            this.trigger('g:checkboxesChanged');
        }
    },

    initialize: function (settings) {
        this.checked = [];
        this._checkboxes = settings.checkboxes;

        new LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new FolderCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.filterFunc = settings.folderFilter;

        this.collection.on('g:changed', function () {
            this.render();
            this.trigger('g:changed');
        }, this).fetch({
            parentType: settings.parentType || 'folder',
            parentId: settings.parentId
        });
    },

    render: function () {
        this.checked = [];
        this.$el.html(FolderListTemplate({
            folders: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            checkboxes: this._checkboxes
        }));
        return this;
    },

    /**
     * Insert a folder into the collection and re-render it.
     */
    insertFolder: function (folder) {
        this.collection.add(folder);
        this.trigger('g:changed');
        this.render();
    },

    /**
     * Set all folder checkboxes to a certain checked state. The event
     * g:checkboxesChanged is triggered once after checking/unchecking everything.
     * @param {bool} checked The checked state.
     */
    checkAll: function (checked) {
        this.$('.g-list-checkbox').prop('checked', checked);

        this.checked = [];
        if (checked) {
            this.collection.each(function (model) {
                this.checked.push(model.cid);
            }, this);
        }

        this.trigger('g:checkboxesChanged');
    },

    recomputeChecked: function () {
        this.checked = _.map(this.$('.g-list-checkbox:checked'), function (checkbox) {
            return $(checkbox).attr('g-folder-cid');
        }, this);
    }
});

export default FolderListWidget;
