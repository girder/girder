girder.models.FolderModel = Backbone.Model.extend({
    /**
     * Delete the folder on the server.
     */
    deleteFolder: function () {
        girder.restRequest({
            path: 'folder/' + this.get('_id'),
            type: 'DELETE'
        }).done(_.bind(function () {
            if (this.collection) {
                this.collection.remove(this);
            }
            this.trigger('g:deleted');
        }, this)).error(_.bind(function () {
            this.trigger('g:error');
        }, this));

        return this;
    }
});
