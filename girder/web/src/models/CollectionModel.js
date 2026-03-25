import _ from 'underscore';

import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import MetadataMixin from '@girder/core/models/MetadataMixin';

var CollectionModel = AccessControlledModel.extend({
    resourceName: 'collection'
});

_.extend(CollectionModel.prototype, MetadataMixin);

export default CollectionModel;
