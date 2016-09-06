import AssetstoreModel from 'girder/models/AssetstoreModel';
import router from 'girder/router';
import events from 'girder/events';

import HdfsAssetstoreImportView from './views/HdfsAssetstoreImportView';
router.route('hdfs_assetstore/:id/import', 'hdfsImport', function (id) {
    // Fetch the folder by id, then render the view.
    var assetstore = new AssetstoreModel({
        _id: id
    }).once('g:fetched', function () {
        events.trigger('g:navigateTo', HdfsAssetstoreImportView, {
            model: assetstore
        });
    }).once('g:error', function () {
        router.navigate('assetstores', {trigger: true});
    }).fetch();
});
