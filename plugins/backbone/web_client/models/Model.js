import _ from 'underscore';

import Backbone from 'backbone';
import { apiRoot } from 'girder/rest';

export default Backbone.Model.extend({
    idAttribute: '_id',
    resource: null,
    parent: _.constant(null),
    children: _.constant([]),
    urlRoot() {
        return `${apiRoot}/${this.resource}`;
    },
    sync(method, model, options = {}) {
        options.data = model.attributes;
        options.processData = true;
        return Backbone.sync.apply(this, arguments);
    }
});
