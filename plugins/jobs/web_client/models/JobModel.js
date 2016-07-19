import AccessControlledModel from 'girder/models/AccessControlledModel';

var JobModel = AccessControlledModel.extend({
    resourceName: 'job'
});

export default JobModel;
