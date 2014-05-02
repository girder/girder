/**
 * This widget shows a list of files in a given item.
 */
girder.views.FileListWidget = girder.View.extend({
    events: {
        'click a.g-show-more-files': function () {
            this.collection.fetchNextPage();
        }
    },

    initialize: function (settings) {
        this.checked = [];
        this.collection = new girder.collections.FileCollection();
        this.collection.resourceName = 'item/' + settings.itemId + '/files';
        this.collection.append = true; // Append, don't replace pages
        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.render();
        }, this).fetch();
    },

    render: function () {
        this.checked = [];
        this.$el.html(jade.templates.fileList({
            files: this.collection.models,
            hasMore: this.collection.hasNextPage(),
            girder: girder
        }));

        return this;
    },

    /**
     * Insert a file into the collection and re-render it.
     */
    insertFile: function (file) {
        this.collection.add(file);
        this.trigger('g:changed');
        this.render();
    }

});
