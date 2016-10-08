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

import json

from ..describe import Description, describeRoute
from ..rest import Resource as BaseResource, RestException, setResponseHeader
from girder.constants import AccessType, TokenScope
from girder.api import access
from girder.models.model_base import AccessControlledModel
from girder.utility import acl_mixin
from girder.utility import parseTimestamp
from girder.utility import ziputil
from girder.utility import path as path_util
from girder.utility.progress import ProgressContext

# Plugins can modify this set to allow other types to be searched
allowedSearchTypes = {'collection', 'folder', 'group', 'item', 'user'}


class Resource(BaseResource):
    """
    API Endpoints that deal with operations across multiple resource types.
    """
    def __init__(self):
        super(Resource, self).__init__()
        self.resourceName = 'resource'
        self.route('GET', ('search',), self.search)
        self.route('GET', ('lookup',), self.lookup)
        self.route('GET', (':id',), self.getResource)
        self.route('GET', (':id', 'path'), self.path)
        self.route('PUT', (':id', 'timestamp'), self.setTimestamp)
        self.route('GET', ('download',), self.download)
        self.route('POST', ('download',), self.download)
        self.route('PUT', ('move',), self.moveResources)
        self.route('POST', ('copy',), self.copyResources)
        self.route('DELETE', (), self.delete)

    @access.public
    @describeRoute(
        Description('Search for resources in the system.')
        .param('q', 'The search query.')
        .param('mode', 'The search mode. Can use either a text search or a '
               'prefix-based search.', enum=('text', 'prefix'), required=False,
               default='text')
        .param('types', 'A JSON list of resource types to search for, e.g. '
               "'user', 'folder', 'item'.")
        .param('level', 'Minimum required access level.', required=False,
               dataType='int', default=AccessType.READ)
        .pagingParams(defaultSort=None, defaultLimit=10)
        .errorResponse('Invalid type list format.')
    )
    def search(self, params):
        self.requireParams(('q', 'types'), params)

        mode = params.get('mode', 'text')
        level = AccessType.validate(params.get('level', AccessType.READ))
        user = self.getCurrentUser()

        limit = int(params.get('limit', 10))
        offset = int(params.get('offset', 0))

        if mode == 'text':
            method = 'textSearch'
        elif mode == 'prefix':
            method = 'prefixSearch'
        else:
            raise RestException(
                'The search mode must be either "text" or "prefix".')

        try:
            types = json.loads(params['types'])
        except ValueError:
            raise RestException('The types parameter must be JSON.')

        results = {}
        for modelName in types:
            if modelName not in allowedSearchTypes:
                continue

            if '.' in modelName:
                name, plugin = modelName.rsplit('.', 1)
                model = self.model(name, plugin)
            else:
                model = self.model(modelName)

            results[modelName] = [
                model.filter(d, user) for d in getattr(model, method)(
                    query=params['q'], user=user, limit=limit, offset=offset,
                    level=level)
            ]

        return results

    def _validateResourceSet(self, params, allowedModels=None):
        """
        Validate a JSON string listing resources.  The resources parameter is a
        JSON encoded dictionary with each key a model name and each value a
        list of ids that must be present in that model.

        :param params: a dictionary of parameters that must include 'resources'
        :param allowedModels: if present, an iterable of models that may be
                              included in the resources.
        :returns: the JSON decoded resource dictionary.
        """
        self.requireParams(('resources', ), params)
        try:
            resources = json.loads(params['resources'])
        except ValueError:
            raise RestException('The resources parameter must be JSON.')
        if not isinstance(resources, dict):
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

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Look up a resource in the data hierarchy by path.')
        .param('path',
               'The path of the resource.  The path must be an absolute Unix '
               'path starting with either "/user/[user name]", for a user\'s '
               'resources or "/collection/[collection name]", for resources '
               'under a collection.')
        .param('test',
               'Specify whether to return None instead of throwing an '
               'exception when path doesn\'t exist.',
               required=False, dataType='boolean', default=False)
        .errorResponse('Path is invalid.')
        .errorResponse('Path refers to a resource that does not exist.')
        .errorResponse('Read access was denied for the resource.', 403)
    )
    def lookup(self, params):
        self.requireParams('path', params)
        test = self.boolParam('test', params, default=False)
        return path_util.lookUpPath(params['path'], self.getCurrentUser(), test)['document']

    def _getResourceName(self, type, doc):
        if type == 'user':
            return doc['login']
        elif type in ('file', 'item', 'folder', 'user', 'collection'):
            return doc['name']
        else:
            raise RestException('Invalid resource type.')

    def _getResourceParent(self, type, doc):
        if type == 'file':
            return doc['itemId'], 'item'
        elif type == 'item':
            return doc['folderId'], 'folder'
        elif type == 'folder':
            return doc['parentId'], doc['parentCollection']
        else:
            raise RestException(
                'Invalid resource type.'
            )

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Get path of a resource.')
        .param('id', 'The ID of the resource.', paramType='path')
        .param('type', 'The type of the resource (item, file, etc.).')
        .errorResponse('ID was invalid.')
        .errorResponse('Invalid resource type.')
        .errorResponse('Read access was denied for the resource.', 403)
    )
    def path(self, id, params):
        path = []
        type = params['type']
        while True:
            doc = self._getResource(id, type)
            if doc is None:
                raise RestException('Invalid resource id.')
            name = self._getResourceName(type, doc)
            path.insert(0, name)

            if type in ('file', 'item', 'folder'):
                id, type = self._getResourceParent(type, doc)
            else:
                break

        path.insert(0, type)
        return '/' + path_util.join(path)

    @access.cookie(force=True)
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Download a set of items, folders, collections, and users '
                    'as a zip archive.')
        .notes('This route is also exposed via the POST method because the '
               'request parameters can be quite long, and encoding them in the '
               'URL (as is standard when using the GET method) can cause the '
               'URL to become too long, which causes errors.')
        .param('resources', 'A JSON-encoded list of types to download.  Each '
               'type is a list of ids.  For example: {"item": [(item id 1), '
               '(item id 2)], "folder": [(folder id 1)]}.')
        .param('includeMetadata', 'Include any metadata in JSON files in the '
               'archive.', required=False, dataType='boolean', default=False)
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('Read access was denied for a resource.', 403)
    )
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
        setResponseHeader('Content-Type', 'application/zip')
        setResponseHeader(
            'Content-Disposition',
            'attachment; filename="Resources.zip"')

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

    @access.user(scope=TokenScope.DATA_OWN)
    @describeRoute(
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
        .errorResponse('Admin access was denied for a resource.', 403)
    )
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

    def _getResource(self, id, type):
        model = self._getResourceModel(type)
        if (isinstance(model, (acl_mixin.AccessControlMixin,
                               AccessControlledModel))):
            user = self.getCurrentUser()
            return model.load(id=id, user=user, level=AccessType.READ)
        return model.load(id=id)

    @access.admin
    @describeRoute(
        Description('Get any resource by ID.')
        .param('id', 'The ID of the resource.', paramType='path')
        .param('type', 'The type of the resource (item, file, etc.).')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the resource.', 403)
    )
    def getResource(self, id, params):
        return self._getResource(id, params['type'])

    @access.admin
    @describeRoute(
        Description('Set the created or updated timestamp for a resource.')
        .param('id', 'The ID of the resource.', paramType='path')
        .param('type', 'The type of the resource (item, file, etc.).')
        .param('created', 'The new created timestamp.', required=False)
        .param('updated', 'The new updated timestamp.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the resource.', 403)
    )
    def setTimestamp(self, id, params):
        user = self.getCurrentUser()
        model = self._getResourceModel(params['type'])
        doc = model.load(id=id, user=user, level=AccessType.WRITE)
        if not doc:
            raise RestException('Resource not found.')
        if 'created' in params:
            if 'created' not in doc:
                raise RestException('Resource has no "created" field.')
            doc['created'] = parseTimestamp(params['created'])
        if 'updated' in params:
            if 'updated' not in doc:
                raise RestException('Resource has no "updated" field.')
            doc['updated'] = parseTimestamp(params['updated'])
        return model.save(doc)

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

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
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
        .errorResponse('ID was invalid.')
    )
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
                    ctx.update(message='Moving %s %s' % (
                        kind, doc.get('name', '')))
                    if kind == 'item':
                        if parent['_id'] != doc['folderId']:
                            model.move(doc, parent)
                    elif kind == 'folder':
                        if ((parentType, parent['_id']) !=
                                (doc['parentCollection'], doc['parentId'])):
                            model.move(doc, parent, parentType)
                    ctx.update(increment=1)

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Copy a set of items and folders.')
        .param('resources', 'A JSON-encoded list of types to copy. Each type '
               'is a list of ids. Only folders and items may be specified.  '
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
        .errorResponse('ID was invalid.')
    )
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
                        raise RestException('Resource not found. No %s with '
                                            'id %s' % (kind, id))
                    ctx.update(message='Copying %s %s' % (
                        kind, doc.get('name', '')))
                    if kind == 'item':
                        model.copyItem(doc, folder=parent, creator=user)
                        ctx.update(increment=1)
                    elif kind == 'folder':
                        model.copyFolder(
                            doc, parent=parent, parentType=parentType,
                            creator=user, progress=ctx)
