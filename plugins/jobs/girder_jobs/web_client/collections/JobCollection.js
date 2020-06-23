import Collection from '@girder/core/collections/Collection';

import JobModel from '../models/JobModel';

const JobCollection = Collection.extend({
    resourceName: 'job',
    model: JobModel
});

export default JobCollection;
