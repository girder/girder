import $ from 'jquery';
import Backbone from 'backbone';
import { apiRoot } from 'girder/rest';

export default Backbone.Model.extend({
    idAttribute: '_id',
    resource: null,
    url() {
        return `${apiRoot}/${this.resource}/this.id`;
    },
    parent() {
        return $.Deferred().resolve(null).promise();
    },
    children() {
        return $.Deferred().resolve([]).promise();
    }
});
