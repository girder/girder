import { AccessControlledModel } from 'girder/models/Model';

var JobModel = AccessControlledModel.extend({
    resourceName: 'job'
});

export default JobModel;
