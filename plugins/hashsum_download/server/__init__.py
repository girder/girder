#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import RestException
from girder.api.v1.file import File
from girder.constants import AccessType


class HashedFile(File):

    supportedAlgorithms = [
        'sha512',
    ]

    def __init__(self, apiRoot):
        super(File, self).__init__()

        self.resourceName = 'file'
        apiRoot.file.route('GET', ('hashsum', ':algo', ':hash', 'download'),
                           self.downloadWithHash)

    @access.public
    @describeRoute(
        Description('Download a file by its hash sum.')
        .param('algo', 'The type of the given hash sum. '
                       'This parameter is case insensitive.',
               paramType='path', enum=supportedAlgorithms)
        .param('hash', 'The hexadecimal hash sum of the file to download. '
                       'This parameter is case insensitive.',
               paramType='path')
        .errorResponse()
        .errorResponse('Read access was denied on the file.', 403)
    )
    def downloadWithHash(self, algo, hash, params):
        file = self._getFirstFileByHash(algo, hash)
        if not file:
            raise RestException('File not found.', code=404)

        return self.download(id=file['_id'], params=params)

    def _getFirstFileByHash(self, algo, hash, user=None):
        """
        Return the first file that the user has access to given its hash and its
        associated hash sum algorithm name.

        :param algo: Algorithm the given hash is encoded with.
        :param hash: Hash of the file to find.
        :param user: User to test access against.
         Default (none) is the current user.
        :return: A file document.
        """
        algo = algo.lower()
        if algo not in self.supportedAlgorithms:
            msg = 'Invalid algorithm ("%s"). Supported algorithm are: %s.'\
                  % (algo, self.supportedAlgorithms)
            raise RestException(msg, code=400)

        query = {algo: hash.lower()}  # Always convert to lower case
        fileModel = self.model('file')
        cursor = fileModel.find(query)

        if not user:
            user = self.getCurrentUser()

        for file in cursor:
            if fileModel.hasAccess(file, user, AccessType.READ):
                return file

        return None


def load(info):
    HashedFile(info['apiRoot'])
