import _ from 'underscore';

import Backbone from 'backbone';
import { apiRoot } from 'girder/rest';

export default Backbone.Model.extend({
    idAttribute: '_id',
    resource: null,
    parent: _.constant(null),
    children: _.constant([]),
    url() {
        return `${apiRoot}/${this.resource}/this.id`;
    }
});
