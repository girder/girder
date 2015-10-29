#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import cherrypy
import json

from ..describe import Description
from ..rest import Resource as BaseResource, RestException
from girder.constants import AccessType
from girder.api import access
from girder.models.model_base import AccessControlledModel
from girder.utility import acl_mixin
from girder.utility import ziputil
from girder.utility.progress import ProgressContext


class Resource(BaseResource):
    """
    API Endpoints that deal with operations across multiple resource types.
    """
    def __init__(self):
        self.resourceName = 'resource'
        self.route('GET', ('search',), self.search)
        self.route('GET', ('lookup',), self.lookup)
        self.route('GET', (':id',), self.getResource)
        self.route('GET', ('download',), self.download)
        self.route('POST', ('download',), self.download)
        self.route('PUT', ('move',), self.moveResources)
        self.route('POST', ('copy',), self.copyResources)
        self.route('DELETE', (), self.delete)

    @access.public
    def search(self, params):
        """
        This endpoint can be used to text search against multiple different
        model types at once.
        :param q: The search query string.
        :param types: A JSON list of types to search.
        :type types: str
        :param limit: The result limit per type. Defaults to 10.
        """
        self.requireParams(('q', 'types'), params)
        user = self.getCurrentUser()

        limit = int(params.get('limit', 10))
        offset = int(params.get('offset', 0))

        results = {}
        try:
            types = json.loads(params['types'])
        except ValueError:
            raise RestException('The types parameter must be JSON.')

        if 'item' in types:
            results['item'] = [
                self.model('item').filter(item) for item in
                self.model('item').textSearch(
                    params['q'], user=user, limit=limit, offset=offset)]
        if 'collection' in types:
            results['collection'] = [
                self.model('collection').filter(c, user) for c in
                self.model('collection').textSearch(
                    params['q'], user=user, limit=limit, offset=offset)]
        if 'folder' in types:
            results['folder'] = [
                self.model('folder').filter(f, user) for f in
                self.model('folder').textSearch(
                    params['q'], user=user, limit=limit, offset=offset)]
        if 'group' in types:
            results['group'] = [
                self.model('group').filter(g, user) for g in
                self.model('group').textSearch(
                    params['q'], user=user, limit=limit, offset=offset)]
        if 'user' in types:
            results['user'] = [
                self.model('user').filter(u, user) for u in
                self.model('user').textSearch(
                    params['q'], user=user, limit=limit, offset=offset)]
        return results
    search.description = (
        Description('Text search for resources in the system.')
        .param('q', 'The search query.')
        .param('types', """A JSON list of resource types to search for, e.g.
                'user', 'folder', 'item'.""")
        .errorResponse('Invalid type list format.'))

    def _validateResourceSet(self, params, allowedModels=None):
        """
        Validate a JSON string listing resources.  The resources parameter is a
        JSON encoded dictionary with each key a model name and each value a
        list of ids that must be present in that model.
        :param params: a dictionary of parameters that must include 'resources'
        :param allowedModels: if present, an iterable of models that may be
                              included in the resources.
        :returns: the json decoded resource dictionary.
        """
        self.requireParams(('resources', ), params)
        try:
            resources = json.loads(params['resources'])
        except ValueError:
            raise RestException('The resources parameter must be JSON.')
        if type(resources) is not dict:
            raise RestException('Invalid resources format.')
        if allowedModels:
            for key in resources:
                if key not in allowedModels:
                    raise RestException('Resource type not supported.')
        count = sum([len(resources[key]) for key in resources])
        if not count:
            raise RestException('No resources specified.')
        return resources

    def _getResourceModel(self, kind, funcName=None):
        """
        Load and return a model with a specific function or throw an exception.
        :param kind: the name of the model to load
        :param funcName: a function name to ensure that each model contains.
        :returns: the loaded model.
        """
        try:
            model = self.model(kind)
        except ImportError:
            model = None
        if not model or (funcName and not hasattr(model, funcName)):
            raise RestException('Invalid resources format.')
        return model

    def _lookUpToken(self, token, parentType, parent):
        """
        Find a particular child resource by name or throw an exception.
        :param token: the name of the child resource to find
        :param parentType: the type of the parent to search
        :param parent: the parent resource
        :returns: the child resource
        """

        seekFolder = (parentType in ('user', 'collection', 'folder'))
        seekItem = (parentType == 'folder')
        seekFile = (parentType == 'item')

        # (model name, mask, search filter)
        searchTable = (
            ('folder', seekFolder, {'name': token,
                                    'parentId': parent['_id'],
                                    'parentCollection': parentType}),
            ('item', seekItem, {'name': token, 'folderId': parent['_id']}),
            ('file', seekFile, {'name': token, 'itemId': parent['_id']}),
        )

        for candidateModel, mask, filterObject in searchTable:
            if not mask:
                continue

            candidateChild = self.model(candidateModel).findOne(filterObject)
            if candidateChild is not None:
                return candidateChild, candidateModel

        # if no folder, item, or file matches, give up
        raise RestException('Child resource not found: {}({})->{}'.format(
            parentType, parent.get('name', parent.get('_id')), token))

    def _lookUpPath(self, path, user):
        pathArray = [token for token in path.split('/') if token]
        model = pathArray[0]

        parent = None
        if model == 'user':
            username = pathArray[1]
            parent = self.model('user').findOne({'login': username})

            if parent is None:
                raise RestException('User not found: {}'.format(username))

        elif model == 'collection':
            collectionName = pathArray[1]
            parent = self.model('collection').findOne({'name': collectionName})

            if parent is None:
                raise RestException(
                    'Collection not found: {}'.format(collectionName))

        else:
            raise RestException('Invalid path format')

        try:
            document = parent
            self.model(model).requireAccess(document, user)
            for token in pathArray[2:]:
                document, model = self._lookUpToken(token, model, document)
                self.model(model).requireAccess(document, user)
        except RestException:
            raise RestException('Path not found: {}'.format(path))

        result = self.model(model).filter(document, user)
        return result

    @access.public
    def lookup(self, params):
        self.requireParams('path', params)
        return self._lookUpPath(params['path'], self.getCurrentUser())

    lookup.description = (
        Description('Look up a resource in the data hierarchy by path.')
        .param('path',
               'The path of the resource.  The path must be an absolute Unix '
               'path starting with either "/user/[user name]", for a user\'s '
               'resources or "/collection/[collection name]", for resources '
               'under a collection.')
        .errorResponse('Path is invalid.')
        .errorResponse('Path refers to a resource that does not exist.')
        .errorResponse('Read access was denied for the resource.', 403))

    @access.public
    def download(self, params):
        """
        Returns a generator function that will be used to stream out a zip
        file containing the listed resource's contents, filtered by
        permissions.
        """
        user = self.getCurrentUser()
        resources = self._validateResourceSet(params)
        # Check that all the resources are valid, so we don't download the zip
        # file if it would throw an error.
        for kind in resources:
            model = self._getResourceModel(kind, 'fileList')
            for id in resources[kind]:
                if not model.load(id=id, user=user, level=AccessType.READ):
                    raise RestException('Resource %s %s not found.' %
                                        (kind, id))
        metadata = self.boolParam('includeMetadata', params, default=False)
        cherrypy.response.headers['Content-Type'] = 'application/zip'
        cherrypy.response.headers['Content-Disposition'] = \
            'attachment; filename="Resources.zip"'

        def stream():
            zip = ziputil.ZipGenerator()
            for kind in resources:
                model = self.model(kind)
                for id in resources[kind]:
                    doc = model.load(id=id, user=user, level=AccessType.READ)
                    for (path, file) in model.fileList(
                            doc=doc, user=user, includeMetadata=metadata,
                            subpath=True):
                        for data in zip.addFile(file, path):
                            yield data
            yield zip.footer()
        return stream
    download.cookieAuth = True
    download.description = (
        Description('Download a set of items, folders, collections, and users '
                    'as a zip archive.')
        .notes('This route is also exposed via the POST method because the '
               'request parameters can be quite long, and encoding them in the '
               'URL (as is standard when using the GET method) can cause the '
               'URL to become too long, which causes errors.')
        .param('resources', 'A JSON-encoded list of types to download.  Each '
               'type is a list of ids.  For example: {"item": [(item id 1), '
               '(item id 2)], "folder": [(folder id 1)]}.')
        .param('includeMetadata', 'Include any metadata in json files in the '
               'archive.', required=False, dataType='boolean', default=False)
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('Read access was denied for a resource.', 403))

    @access.user
    def delete(self, params):
        """
        Delete a set of resources.
        """
        user = self.getCurrentUser()
        resources = self._validateResourceSet(params)
        total = sum([len(resources[key]) for key in resources])
        progress = self.boolParam('progress', params, default=False)
        with ProgressContext(progress, user=user,
                             title='Deleting resources',
                             message='Calculating size...') as ctx:
            ctx.update(total=total)
            current = 0
            for kind in resources:
                model = self._getResourceModel(kind, 'remove')
                for id in resources[kind]:
                    if (isinstance(model, (acl_mixin.AccessControlMixin,
                                           AccessControlledModel))):
                        doc = model.load(id=id, user=user,
                                         level=AccessType.ADMIN)
                    else:
                        doc = model.load(id=id)
                    if not doc:
                        raise RestException('Resource %s %s not found.' %
                                            (kind, id))
                    # Don't do a subtree count if we weren't asked for progress
                    if progress:
                        subtotal = model.subtreeCount(doc)
                        if subtotal != 1:
                            total += model.subtreeCount(doc)-1
                            ctx.update(total=total)
                    model.remove(doc, progress=ctx)
                    if progress:
                        current += subtotal
                        if ctx.progress['data']['current'] != current:
                            ctx.update(current=current,
                                       message='Deleted ' + kind)
    delete.description = (
        Description('Delete a set of items, folders, or other resources.')
        .param('resources', 'A JSON-encoded list of types to delete.  Each '
               'type is a list of ids.  For example: {"item": [(item id 1), '
               '(item id2)], "folder": [(folder id 1)]}.')
        .param('progress', 'Whether to record progress on this task.',
               default=False, required=False, dataType='boolean')
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('Admin access was denied for a resource.', 403))

    @access.admin
    def getResource(self, id, params):
        model = self._getResourceModel(params['type'])
        if (isinstance(model, (acl_mixin.AccessControlMixin,
                               AccessControlledModel))):
            user = self.getCurrentUser()
            return model.load(id=id, user=user, level=AccessType.READ)
        return model.load(id=id)
    getResource.description = (
        Description('Get any resource by ID.')
        .param('id', 'The ID of the resource.', paramType='path')
        .param('type', 'The type of the resource (item, file, etc.).')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the resource.', 403))

    def _prepareMoveOrCopy(self, params):
        user = self.getCurrentUser()
        resources = self._validateResourceSet(params, ('folder', 'item'))
        parentType = params['parentType'].lower()
        if parentType not in ('user', 'collection', 'folder'):
            raise RestException('Invalid parentType.')
        if ('item' in resources and len(resources['item']) > 0 and
                parentType != 'folder'):
            raise RestException('Invalid parentType.')
        parent = self.model(parentType).load(
            params['parentId'], level=AccessType.WRITE, user=user, exc=True)
        progress = self.boolParam('progress', params, default=False)
        return user, resources, parent, parentType, progress

    @access.user
    def moveResources(self, params):
        """
        Move the specified resources to a new parent folder, user, or
        collection.  Only folder and item resources can be moved with this
        function.
        """
        user, resources, parent, parentType, progress = \
            self._prepareMoveOrCopy(params)
        total = sum([len(resources[key]) for key in resources])
        with ProgressContext(progress, user=user, title='Moving resources',
                             message='Calculating requirements...',
                             total=total) as ctx:
            for kind in resources:
                model = self._getResourceModel(kind, 'move')
                for id in resources[kind]:
                    doc = model.load(id=id, user=user, level=AccessType.WRITE)
                    if not doc:
                        raise RestException('Resource %s %s not found.' %
                                            (kind, id))
                    ctx.update(message=u'Moving {} {}'.format(
                        kind, doc.get('name', '')))
                    if kind == 'item':
                        if parent['_id'] != doc['folderId']:
                            model.move(doc, parent)
                    elif kind == 'folder':
                        if ((parentType, parent['_id']) !=
                                (doc['parentCollection'], doc['parentId'])):
                            model.move(doc, parent, parentType)
                    ctx.update(increment=1)
    moveResources.description = (
        Description('Move a set of items and folders.')
        .param('resources', 'A JSON-encoded list of types to move.  Each type '
               'is a list of ids.  Only folders and items may be specified.  '
               'For example: {"item": [(item id 1), (item id2)], "folder": '
               '[(folder id 1)]}.')
        .param('parentType', 'Parent type for the new parent of these '
               'resources.')
        .param('parentId', 'Parent ID for the new parent of these resources.')
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean')
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('Resource type not supported.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('ID was invalid.'))

    @access.user
    def copyResources(self, params):
        """
        Copy the specified resources to a new parent folder, user, or
        collection.  Only folder and item resources can be copied with this
        function.
        """
        user, resources, parent, parentType, progress = \
            self._prepareMoveOrCopy(params)
        total = len(resources.get('item', []))
        if 'folder' in resources:
            model = self._getResourceModel('folder')
            for id in resources['folder']:
                folder = model.load(id=id, user=user,
                                    level=AccessType.READ)
                if folder:
                    total += model.subtreeCount(folder)
        with ProgressContext(progress, user=user, title='Copying resources',
                             message='Calculating requirements...',
                             total=total) as ctx:
            for kind in resources:
                model = self._getResourceModel(kind)
                for id in resources[kind]:
                    doc = model.load(id=id, user=user, level=AccessType.READ)
                    if not doc:
                        raise RestException('Resource not found.  No {} with '
                                            'id {}'.format(kind, id))
                    ctx.update(message=u'Copying {} {}'.format(
                        kind, doc.get('name', '')))
                    if kind == 'item':
                        model.copyItem(doc, folder=parent, creator=user)
                        ctx.update(increment=1)
                    elif kind == 'folder':
                        model.copyFolder(
                            doc, parent=parent, parentType=parentType,
                            creator=user, progress=ctx)
    copyResources.description = (
        Description('Copy a set of items and folders.')
        .param('resources', 'A JSON-encoded list of types to copy.  Each type '
               'is a list of ids.  Only folders and items may be specified.  '
               'For example: {"item": [(item id 1), (item id2)], "folder": '
               '[(folder id 1)]}.')
        .param('parentType', 'Parent type for the new parent of these '
               'resources.')
        .param('parentId', 'Parent ID for the new parent of these resources.')
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean')
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('Resource type not supported.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('ID was invalid.'))
