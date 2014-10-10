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


class Resource(BaseResource):
    """
    API Endpoints that deal with operations across multiple resource types.
    """
    def __init__(self):
        self.resourceName = 'resource'
        self.route('GET', ('search',), self.search)
        self.route('GET', ('download',), self.download)

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

    def _download(self, resources, user, metadata=False):
        """
        Returns a generator function that will be used to stream out a zip
        file containing the listed resource's contents, filtered by
        permissions.  This assumes that the parameters have been validated.
        """
        cherrypy.response.headers['Content-Type'] = 'application/zip'
        cherrypy.response.headers['Content-Disposition'] = \
            'attachment; filename="Resources.zip"'

        def stream():
            zip = ziputil.ZipGenerator('Resources')
            for kind in resources:
                model = self.model(kind)
                if not model or not hasattr(model, 'fileList'):
                    continue
                for id in resources[kind]:
                    doc = model.load(id=id, user=user, level=AccessType.READ)
                    for (path, file) in model.fileList(
                            doc=doc, user=user, includeMetadata=metadata,
                            subpath=True):
                        for data in zip.addFile(file, path):
                            yield data
            yield zip.footer()
        return stream

    @access.public
    def download(self, params):
        """
        Returns a generator function that will be used to stream out a zip
        file containing the listed resource's contents, filtered by
        permissions.
        """
        self.requireParams(('resources', ), params)
        user = self.getCurrentUser()
        try:
            resources = json.loads(params['resources'])
        except ValueError:
            raise RestException('The resources parameter must be JSON.')
        if type(resources) is not dict:
            raise RestException('Invalid resources format.')
        # Check that all of the specified resources are valid and have access
        # before we begin the download
        count = 0
        for kind in resources:
            model = self.model(kind)
            if not model or not hasattr(model, 'fileList'):
                raise RestException('Invalid resources format.')
            for id in resources[kind]:
                if model.load(id=id, user=user, level=AccessType.READ):
                    count += 1
                else:
                    raise RestException('Resource %s %s not found.' % (kind,
                                                                       id))
        if not count:
            raise RestException('No resources specified.')
        metadata = self.boolParam('includeMetadata', params, default=False)
        # Have a helper function do the work now that we have validated
        return self._download(resources, user, metadata)
    download.description = (
        Description('Download a set of items and folders as a zip archive.')
        .param('resources', 'A JSON-encoded list of types to download.  Each '
               'type is a list of ids.  For example: {"item": [(item id 1), '
               '(item id2)], "folder": [(folder id 1)]}.')
        .param('includeMetadata', 'Include any metadata in json files in the '
               'archive.', required=False, dataType='boolean')
        .errorResponse('An ID was invalid.')
        .errorResponse('Unsupport or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('Read access was denied for an item.', 403))
