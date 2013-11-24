/**
 * This widget shows a list of folders under a given parent.
 * Initialize this with a "parentType" and "parentId" value, which will
 * be passed to the folder GET endpoint.
 */
girder.views.FolderListWidget = Backbone.View.extend({
    events: {
        'click a.g-folder-list-link': function (event) {
            var cid = $(event.currentTarget).attr('g-folder-cid');
            this.trigger('g:folderClicked', this.collection.get(cid));
        }
    },

    initialize: function (settings) {
        this.collection = new girder.collections.FolderCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch({
            parentType: settings.parentType || 'folder',
            parentId: settings.parentId
        });
    },

    render: function () {
        this.checked = [];
        this.$el.html(jade.templates.folderList({
            folders: this.collection.models
        }));

        var view = this;
        this.$('.g-list-checkbox').unbind('change').change(function () {
            var cid = $(this).attr('g-folder-cid');
            if (this.checked) {
                view.checked.push(cid);
            }
            else {
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
            _.each(this.collection.models, function (model) {
                this.checked.push(model.cid);
            }, this);
        }

        this.trigger('g:checkboxesChanged');
    }
});
