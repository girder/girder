from girder.utility.model_importer import ModelImporter


def scheduleThumbnailJob(file, attachToType, attachToId, user, width=0, height=0, crop=True):
    """
    Schedule a local thumbnail creation job and return it.
    """
    jm = ModelImporter.model('job', 'jobs')
    job = jm.createLocalJob(
        title='Generate thumbnail for %s' % file['name'], user=user, type='thumbnails.create',
        public=False, module='girder.plugins.thumbnails.worker', kwargs={
            'fileId': str(file['_id']),
            'width': width,
            'height': height,
            'crop': crop,
            'attachToType': attachToType,
            'attachToId': str(attachToId)
        })
    jm.scheduleJob(job)
    return job
