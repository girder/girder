# -*- coding: utf-8 -*-
import re
import cherrypy
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import AccessType, TokenScope
from girder.models.file import File as FileModel
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel


@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Get the README for a folder, if it exists.')
    .modelParam('id', model=FolderModel, level=AccessType.READ)
    .errorResponse()
    .errorResponse('Read access was denied on the folder.', 403)
)
def _getFolderReadme(folder):
    query = {
        'folderId': folder['_id'],
        'name': {'$regex': re.compile(r'^README(\..+)?$')},
    }
    item = ItemModel().findOne(query)
    if item:
        files = list(ItemModel().childFiles(item=item, limit=1))
        if len(files) >= 1:
            return FileModel().download(files[0])
    cherrypy.response.status = 204
    return ''
