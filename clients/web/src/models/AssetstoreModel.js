girder.models.AssetstoreModel = girder.Model.extend({
    resourceName: 'assetstore',

    capacityKnown: function () {
        var cap = this.get('capacity');
        return cap && cap.free !== null && cap.total !== null;
    },

    capacityString: function () {
        if (!this.capacityKnown()) {
            return 'Unknown';
        }
        var cap = this.get('capacity');
        return girder.formatSize(cap.free) + ' free of ' +
            girder.formatSize(cap.total) + ' total';
    },

    /**
     * Save this model to the server. If this is a new model, meaning it has no
     * _id attribute, this will create it. If the _id is set, we update the
     * existing model. Triggers g:saved on success, and g:error on error.
     */
    save: function () {
        var path, type;
        if (this.has('_id')) {
            path = this.resourceName + '/' + this.get('_id');
            type = 'PUT';
        } else {
            path = this.resourceName;
            type = 'POST';
        }

        girder.restRequest({
            path: path,
            type: type,
            data: this.attributes,
            error: null // don't do default error behavior (validation may fail)
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:saved');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    }
});
