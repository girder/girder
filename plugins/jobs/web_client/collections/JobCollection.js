import Collection from 'girder/collections/Collection';
import JobModel from '../models/JobModel';

var JobCollection = Collection.extend({
    resourceName: 'job',
    model: JobModel
});

export default JobCollection;
