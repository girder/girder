from girder_jobs.models.job import Job


def scheduleThumbnailJob(file, attachToType, attachToId, user, width=0, height=0, crop=True):
    """
    Schedule a local thumbnail creation job and return it.
    """
    job = Job().createLocalJob(
        title='Generate thumbnail for %s' % file['name'], user=user, type='thumbnails.create',
        public=False, module='girder_thumbnails.worker', kwargs={
            'fileId': str(file['_id']),
            'width': width,
            'height': height,
            'crop': crop,
            'attachToType': attachToType,
            'attachToId': str(attachToId)
        })
    Job().scheduleJob(job)
    return job
