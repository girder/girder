var _             = require('underscore');

var MiscFunctions = require('girder/utilities/MiscFunctions');
var Model         = require('girder/model').Model;
var Rest          = require('girder/rest');

var AssetstoreModel = Model.extend({
    resourceName: 'assetstore',

    capacityKnown: function () {
        var cap = this.get('capacity');
        return cap && cap.free !== null && cap.total !== null;
    },

    capacityString: function () {
        var cap = this.get('capacity');
        return MiscFunctions.formatSize(cap.free) + ' free of ' +
            MiscFunctions.formatSize(cap.total) + ' total';
    },

    import: function (params) {
        Rest.restRequest({
            path: 'assetstore/' + this.get('_id') + '/import',
            type: 'POST',
            data: params,
            error: null
        }).done(_.bind(function (resp) {
            this.trigger('g:imported', resp);
        }, this)).error(_.bind(function (resp) {
            this.trigger('g:error', resp);
        }, this));

        return this;
    }
});

module.exports = AssetstoreModel;
