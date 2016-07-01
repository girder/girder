/**
 * This widget shows a list of folders under a given parent.
 * Initialize this with a "parentType" and "parentId" value, which will
 * be passed to the folder GET endpoint.
 */
girder.views.FolderListWidget = girder.View.extend({
    events: {
        'click a.g-folder-list-link': function (event) {
            var cid = $(event.currentTarget).attr('g-folder-cid');
            this.trigger('g:folderClicked', this.collection.get(cid));
        },
        'click a.g-show-more-folders': function () {
            this.collection.fetchNextPage();
        }
    },

    initialize: function (settings) {
        this.checked = [];
        this._checkboxes = settings.checkboxes;

        new girder.views.LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new girder.collections.FolderCollection();
        this.collection.append = true; // Append, don't replace pages
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
        this.$el.html(girder.templates.folderList({
            folders: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            checkboxes: this._checkboxes
        }));

        var view = this;
        this.$('.g-list-checkbox').change(function () {
            var cid = $(this).attr('g-folder-cid');
            if (this.checked) {
                view.checked.push(cid);
            } else {
                var idx = view.checked.indexOf(cid);
                if (idx !== -1) {
                    view.checked.splice(idx, 1);
                }
            }
            view.trigger('g:checkboxesChanged');
        });
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
