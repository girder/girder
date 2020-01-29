# -*- coding: utf-8 -*-
import hashlib
import six

import girder
from girder import events
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import (
    filtermodel, setRawResponse, setResponseHeader, setContentDisposition)
from girder.api.v1.file import File
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.models.file import File as FileModel
from girder.models.setting import Setting
from girder.plugin import GirderPlugin
from girder.utility.progress import ProgressContext, noProgress

from .settings import PluginSettings


SUPPORTED_ALGORITHMS = {'sha512'}
_CHUNK_LEN = 65536


class HashedFile(File):
    @property
    def supportedAlgorithms(self):
        girder.logger.warning(
            'HashedFile.supportedAlgorithms is deprecated, use the module-level '
            'SUPPORTED_ALGORITHMS instead.')
        return SUPPORTED_ALGORITHMS

    def __init__(self, node):
        super(HashedFile, self).__init__()

        node.route('GET', ('hashsum', ':algo', ':hash'), self.getByHash)
        node.route('GET', ('hashsum', ':algo', ':hash', 'download'), self.downloadWithHash)
        node.route('GET', (':id', 'hashsum_file', ':algo'), self.downloadKeyFile)
        node.route('POST', (':id', 'hashsum'), self.computeHashes)

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @autoDescribeRoute(
        Description('Download the hashsum key file for a given file.')
        .modelParam('id', 'The ID of the file.', model=FileModel, level=AccessType.READ)
        .param('algo', 'The hashsum algorithm.', paramType='path', lower=True,
               enum=SUPPORTED_ALGORITHMS)
        .notes("This is meant to be used in conjunction with CMake's ExternalData module.")
        .produces('text/plain')
        .errorResponse()
        .errorResponse('Read access was denied on the file.', 403)
    )
    def downloadKeyFile(self, file, algo):
        self._validateAlgo(algo)

        if algo not in file:
            raise RestException('This file does not have the %s hash computed.' % algo)
        keyFileBody = '%s\n' % file[algo]
        name = '.'.join((file['name'], algo))

        setResponseHeader('Content-Length', len(keyFileBody))
        setResponseHeader('Content-Type', 'text/plain')
        setContentDisposition(name)
        setRawResponse()

        return keyFileBody

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @autoDescribeRoute(
        Description('Download a file by its hashsum.')
        .param('algo', 'The type of the given hashsum (case insensitive).',
               paramType='path', lower=True, enum=SUPPORTED_ALGORITHMS)
        .param('hash', 'The hexadecimal hashsum of the file to download (case insensitive).',
               paramType='path', lower=True)
        .errorResponse('No file with the given hash exists.')
    )
    def downloadWithHash(self, algo, hash, params):
        file = self._getFirstFileByHash(algo, hash)
        if not file:
            raise RestException('File not found.', code=404)

        return self.download(id=file['_id'], params=params)

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @filtermodel(FileModel)
    @autoDescribeRoute(
        Description('Return a list of files matching a hashsum.')
        .param('algo', 'The type of the given hashsum (case insensitive).',
               paramType='path', lower=True, enum=SUPPORTED_ALGORITHMS)
        .param('hash', 'The hexadecimal hashsum of the file to download (case insensitive).',
               paramType='path', lower=True)
    )
    def getByHash(self, algo, hash):
        self._validateAlgo(algo)

        model = FileModel()
        user = self.getCurrentUser()
        cursor = model.find({algo: hash})
        return [file for file in cursor if model.hasAccess(file, user, AccessType.READ)]

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Manually compute the checksum values for a given file.')
        .modelParam('id', 'The ID of the file.', model=FileModel, level=AccessType.WRITE)
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
        associated hashsum algorithm name.

        :param algo: Algorithm the given hash is encoded with.
        :param hash: Hash of the file to find.
        :param user: User to test access against.
         Default (none) is the current user.
        :return: A file document.
        """
        self._validateAlgo(algo)

        query = {algo: hash}
        fileModel = FileModel()
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
    if Setting().get(PluginSettings.AUTO_COMPUTE):
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

    fileModel = FileModel()
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


class HashsumDownloadPlugin(GirderPlugin):
    DISPLAY_NAME = 'Hashsum Download'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        HashedFile(info['apiRoot'].file)
        FileModel().exposeFields(level=AccessType.READ, fields=SUPPORTED_ALGORITHMS)

        events.bind('data.process', 'hashsum_download', _computeHashHook)
