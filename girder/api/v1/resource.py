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
from girder.utility import ziputil
from girder.utility.progress import ProgressContext


class Resource(BaseResource):
    """
    API Endpoints that deal with operations across multiple resource types.
    """
    def __init__(self):
        self.resourceName = 'resource'
        self.route('GET', ('search',), self.search)
        self.route('GET', ('download',), self.download)
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

    def _validateResourceSet(self, params):
        """
        Validate a JSON string listing resources.  The resources parameter is a
        JSON encoded dictionary with each key a model name and each value a
        list of ids that must be present in that model.
        :param params: a dictionary of parameters that must include 'resources'
        :returns: the json decoded resource dictionary.
        """
        self.requireParams(('resources', ), params)
        try:
            resources = json.loads(params['resources'])
        except ValueError:
            raise RestException('The resources parameter must be JSON.')
        if type(resources) is not dict:
            raise RestException('Invalid resources format.')
        count = sum([len(resources[key]) for key in resources])
        if not count:
            raise RestException('No resources specified.')
        return resources

    def _getResourceModel(self, kind, funcName):
        """
        Load and return a model with a specific function or throw an exception.
        :param kind: the name of the model to load
        :param funcName: a function name to ensure that each model contains.
        :returns: the loaded model.
        """
        try:
            model = self.model(kind)
        except Exception as exc:
            if exc.message.startswith('Could not load model '):
                model = None
            else:
                raise
        if not model or (funcName and not hasattr(model, funcName)):
            raise RestException('Invalid resources format.')
        return model

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
    download.description = (
        Description('Download a set of items, folders, collections, and users '
                    'as a zip archive.')
        .param('resources', 'A JSON-encoded list of types to download.  Each '
               'type is a list of ids.  For example: {"item": [(item id 1), '
               '(item id2)], "folder": [(folder id 1)]}.')
        .param('includeMetadata', 'Include any metadata in json files in the '
               'archive.', required=False, dataType='boolean')
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
            if progress:
                ctx.update(total=total)
                current = 0
            for kind in resources:
                model = self._getResourceModel(kind, 'remove')
                for id in resources[kind]:
                    doc = model.load(id=id, user=user, level=AccessType.ADMIN)
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
        Description('Delete a set of items and folders.')
        .param('resources', 'A JSON-encoded list of types to delete.  Each '
               'type is a list of ids.  For example: {"item": [(item id 1), '
               '(item id2)], "folder": [(folder id 1)]}.')
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean')
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('Admin access was denied for a resource.', 403))
