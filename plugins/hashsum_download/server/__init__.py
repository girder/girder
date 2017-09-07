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

import hashlib
import six
import warnings

from girder import events
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import RestException, setRawResponse, setResponseHeader, setContentDisposition
from girder.api.v1.file import File
from girder.constants import AccessType, TokenScope
from girder.models.model_base import ValidationException
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext, noProgress

SUPPORTED_ALGORITHMS = {'sha512'}
_CHUNK_LEN = 65536


class PluginSettings(object):
    AUTO_COMPUTE = 'hashsum_download.auto_compute'


class HashedFile(File):
    @property
    def supportedAlgorithms(self):  # pragma: no cover
        warnings.warn(
            'HashedFile.supportedAlgorithms is deprecated, use the module-level '
            'SUPPORTED_ALGORITHMS instead.', DeprecationWarning)
        return SUPPORTED_ALGORITHMS

    def __init__(self, node):
        super(File, self).__init__()

        node.route('GET', ('hashsum', ':algo', ':hash', 'download'), self.downloadWithHash)
        node.route('GET', (':id', 'hashsum_file', ':algo'), self.downloadKeyFile)
        node.route('POST', (':id', 'hashsum'), self.computeHashes)

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Download the hashsum key file for a given file.')
        .modelParam('id', 'The ID of the file.', model='file', level=AccessType.READ)
        .param('algo', 'The hashsum algorithm.', paramType='path', lower=True,
               enum=SUPPORTED_ALGORITHMS)
        .notes('This is meant to be used in conjunction with CMake\'s ExternalData module.')
        .produces('text/plain')
        .errorResponse()
        .errorResponse('Read access was denied on the file.', 403)
    )
    def downloadKeyFile(self, file, algo):
        self._validateAlgo(algo)

        if algo not in file:
            raise RestException('This file does not have the %s hash computed.' % algo)
        hash = file[algo]
        name = '.'.join((file['name'], algo))

        setResponseHeader('Content-Length', len(hash))
        setResponseHeader('Content-Type', 'text/plain')
        setContentDisposition(name)
        setRawResponse()

        return hash

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Download a file by its hash sum.')
        .param('algo', 'The type of the given hash sum (case insensitive).',
               paramType='path', lower=True, enum=SUPPORTED_ALGORITHMS)
        .param('hash', 'The hexadecimal hash sum of the file to download (case insensitive).',
               paramType='path', lower=True)
        .errorResponse('No file with the given hash exists.')
    )
    def downloadWithHash(self, algo, hash, params):
        file = self._getFirstFileByHash(algo, hash)
        if not file:
            raise RestException('File not found.', code=404)

        return self.download(id=file['_id'], params=params)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Manually compute the checksum values for a given file.')
        .modelParam('id', 'The ID of the file.', model='file', level=AccessType.WRITE)
        .param('progress', 'Whether to track progress of the operation', dataType='boolean',
               default=False, required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the file.', 403)
    )
    def computeHashes(self, file, progress):
        with ProgressContext(
                progress, title='Computing hash: %s' % file['name'], total=file['size'],
                user=self.getCurrentUser()) as pc:
            return _computeHash(file, progress=pc)

    def _validateAlgo(self, algo):
        """
        Print an exception if a user requests an invalid checksum algorithm.
        """
        if algo not in SUPPORTED_ALGORITHMS:
            msg = 'Invalid algorithm "%s". Supported algorithms: %s.' % (
                algo, ', '.join(SUPPORTED_ALGORITHMS))
            raise RestException(msg, code=400)

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
        self._validateAlgo(algo)

        query = {algo: hash}  # Always convert to lower case
        fileModel = self.model('file')
        cursor = fileModel.find(query)

        if not user:
            user = self.getCurrentUser()

        for file in cursor:
            if fileModel.hasAccess(file, user, AccessType.READ):
                return file

        return None


def _computeHashHook(event):
    """
    Event hook that computes the file hashes in the background after
    a completed upload. Only done if the AUTO_COMPUTE setting enabled.
    """
    if ModelImporter.model('setting').get(PluginSettings.AUTO_COMPUTE, default=False):
        _computeHash(event.info['file'])


def _computeHash(file, progress=noProgress):
    """
    Computes all supported checksums on a given file. Downloads the
    file data and stream-computes all required hashes on it, saving
    the results in the file document.

    In the case of assetstore impls that already compute the sha512,
    and when sha512 is the only supported algorithm, we will not download
    the file to the server.
    """
    toCompute = SUPPORTED_ALGORITHMS - set(file)
    toCompute = {alg: getattr(hashlib, alg)() for alg in toCompute}

    if not toCompute:
        return

    fileModel = ModelImporter.model('file')
    with fileModel.open(file) as fh:
        while True:
            chunk = fh.read(_CHUNK_LEN)
            if not chunk:
                break
            for digest in six.viewvalues(toCompute):
                digest.update(chunk)
            progress.update(increment=len(chunk))

    digests = {alg: digest.hexdigest() for alg, digest in six.viewitems(toCompute)}
    fileModel.update({'_id': file['_id']}, update={
        '$set': digests
    }, multi=False)

    return digests


@setting_utilities.validator(PluginSettings.AUTO_COMPUTE)
def _validateAutoCompute(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('Auto-compute hash setting must be true or false.')


def load(info):
    HashedFile(info['apiRoot'].file)
    ModelImporter.model('file').exposeFields(
        level=AccessType.READ, fields=SUPPORTED_ALGORITHMS)

    events.bind('data.process', info['name'], _computeHashHook)
