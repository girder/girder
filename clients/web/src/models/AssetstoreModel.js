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
    }
});
