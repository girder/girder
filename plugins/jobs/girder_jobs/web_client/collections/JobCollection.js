import JobModel from '../models/JobModel';

const Collection = girder.collections.Collection;

var JobCollection = Collection.extend({
    resourceName: 'job',
    model: JobModel
});

export default JobCollection;
