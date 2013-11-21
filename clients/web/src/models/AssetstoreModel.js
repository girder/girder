girder.models.AssetstoreModel = Backbone.Model.extend({

    fetch: function () {
        girder.restRequest({
            path: 'assetstore/' + this.get('_id'),
            error: null
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:fetched');
        }, this)).error(_.bind(function () {
            this.trigger('g:error');
        }, this));
    },

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
    }
});
