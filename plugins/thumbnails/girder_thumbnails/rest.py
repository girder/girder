from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import filtermodel, Resource
from girder.constants import AccessType
from girder.exceptions import RestException
from girder.models.file import File
from girder.utility.model_importer import ModelImporter
from girder_jobs.models.job import Job
from . import utils


class Thumbnail(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'thumbnail'
        self.route('POST', (), self.createThumbnail)

    @access.user
    @filtermodel(model=Job)
    @autoDescribeRoute(
        Description('Create a new thumbnail from an existing image file.')
        .notes('Setting a width or height parameter of 0 will preserve the '
               'original aspect ratio.')
        .modelParam('fileId', 'The ID of the source file.', model=File, paramType='formData',
                    level=AccessType.READ)
        .param('width', 'The desired width.', required=False, dataType='integer', default=0)
        .param('height', 'The desired height.', required=False, dataType='integer', default=0)
        .param('crop', 'Whether to crop the image to preserve aspect ratio. '
               'Only used if both width and height parameters are nonzero.',
               dataType='boolean', required=False, default=True)
        .param('attachToId', 'The lifecycle of this thumbnail is bound to the '
               'resource specified by this ID.')
        .param('attachToType', 'The type of resource to which this thumbnail is attached.',
               enum=['folder', 'user', 'collection', 'item'])
        .errorResponse()
        .errorResponse(('Write access was denied on the attach destination.',
                        'Read access was denied on the file.'), 403)
    )
    def createThumbnail(self, file, width, height, crop, attachToId, attachToType):
        user = self.getCurrentUser()

        ModelImporter.model(attachToType).load(
            attachToId, user=user, level=AccessType.WRITE, exc=True)

        width = max(width, 0)
        height = max(height, 0)

        if not width and not height:
            raise RestException('You must specify a valid width, height, or both.')

        return utils.scheduleThumbnailJob(file, attachToType, attachToId, user, width, height, crop)
