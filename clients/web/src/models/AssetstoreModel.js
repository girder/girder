import _ from 'underscore';

import { formatSize } from 'girder/utilities/MiscFunctions';
import Model from 'girder/models/Model';
import { restRequest } from 'girder/rest';

var AssetstoreModel = Model.extend({
    resourceName: 'assetstore',

    capacityKnown: function () {
        var cap = this.get('capacity');
        return cap && cap.free !== null && cap.total !== null;
    },

    capacityString: function () {
        var cap = this.get('capacity');
        return formatSize(cap.free) + ' free of ' +
            formatSize(cap.total) + ' total';
    },

    import: function (params) {
        restRequest({
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
    },

    save: function () {
        if (_.isNumber(this.get('perms'))) {
            // Coerce to an octal string to disambiguate
            this.set('perms', this.get('perms').toString(8));
        }
        Model.prototype.save.call(this, arguments);
    }
});

export default AssetstoreModel;
