girder.models.ItemModel = girder.Model.extend({
    resourceName: 'item',

    /**
     * Get the access level of the item and pass it to the callback
     * function passed in as a parameter.
     */
    getAccessLevel: function (callback) {
        if (this.parent && this.parent.getAccessLevel()) {
            callback(this.parent.getAccessLevel());
        } else {
            this.parent = new girder.models.FolderModel();
            this.parent.set({
                _id: this.get('folderId')
            }).on('g:fetched', function () {
                callback(this.parent.getAccessLevel());
            }, this).fetch();
        }
    }

});
