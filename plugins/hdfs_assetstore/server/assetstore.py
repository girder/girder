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

import os
import posixpath
import pwd
import requests
from snakebite.client import Client as HdfsClient
import uuid

from girder import logger
from girder.api.rest import setResponseHeader
from girder.models.model_base import ValidationException
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter


class HdfsAssetstoreAdapter(AbstractAssetstoreAdapter):
    def __init__(self, assetstore):
        super(HdfsAssetstoreAdapter, self).__init__(assetstore)
        self.client = self._getClient(self.assetstore)

    @staticmethod
    def _getHdfsUser(assetstore):
        """
        If the given assetstore has an effective user specified, this returns
        it. Otherwise returns the current user.
        """
        return assetstore['hdfs'].get('user') or pwd.getpwuid(os.getuid())[0]

    @staticmethod
    def _getClient(assetstore):
        return HdfsClient(
            host=assetstore['hdfs']['host'], port=assetstore['hdfs']['port'],
            use_trash=False,
            effective_user=HdfsAssetstoreAdapter._getHdfsUser(assetstore)
        )

    def _absPath(self, doc):
        """
        Return the absolute path in HDFS for a given file or upload.

        :param doc: The file or upload document.
        """
        return posixpath.join(
            self.assetstore['hdfs']['path'], doc['hdfs']['path'])

    @staticmethod
    def validateInfo(doc):
        """
        Ensures we have the necessary information to connect to HDFS instance,
        and uses snakebite to actually connect to it.
        """
        info = doc.get('hdfs', {})
        for field in ('host', 'port', 'path', 'webHdfsPort', 'user'):
            if field not in info:
                raise ValidationException('Missing %s field.' % field)

        if not info['webHdfsPort']:
            info['webHdfsPort'] = 50070

        try:
            info['webHdfsPort'] = int(info['webHdfsPort'])
            info['port'] = int(info['port'])
        except ValueError:
            raise ValidationException('Port values must be numeric.',
                                      field='port')

        try:
            client = HdfsAssetstoreAdapter._getClient(doc)
            client.serverdefaults()
        except Exception:
            raise ValidationException('Could not connect to HDFS at %s:%d.' %
                                      (info['host'], info['port']))

        # TODO test connection to webHDFS? Not now since it's not required

        if not posixpath.isabs(info['path']):
            raise ValidationException('Path must be absolute.', field='path')

        if not client.test(info['path'], exists=True, directory=True):
            res = client.mkdir([info['path']], create_parent=True).next()
            if not res['result']:
                raise ValidationException(res['error'], field='path')

        return doc

    def capacityInfo(self):
        try:
            info = self.client.df()
            return {
                'free': info['capacity'] - info['used'],
                'total': info['capacity']
            }
        except Exception:
            return {
                'free': None,
                'total': None
            }

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):
        if endByte is None or endByte > file['size']:
            endByte = file['size']

        if headers:
            setResponseHeader('Accept-Ranges', 'bytes')
            self.setContentHeaders(file, offset, endByte, contentDisposition)

        if file['hdfs'].get('imported'):
            path = file['hdfs']['path']
        else:
            path = self._absPath(file)

        def stream():
            position = 0
            fileStream = self.client.cat([path]).next()
            shouldBreak = False
            for chunk in fileStream:
                chunkLen = len(chunk)

                if position < offset:
                    if position + chunkLen > offset:
                        if position + chunkLen > endByte:
                            chunkLen = endByte - position
                            shouldBreak = True
                        yield chunk[offset - position:chunkLen]
                else:
                    if position + chunkLen > endByte:
                        chunkLen = endByte - position
                        shouldBreak = True
                    yield chunk[:chunkLen]

                position += chunkLen

                if shouldBreak:
                    break
        return stream

    def deleteFile(self, file):
        """
        Only deletes the file if it is managed (i.e. not an imported file).
        """
        if not file['hdfs'].get('imported'):
            res = self.client.delete([self._absPath(file)]).next()
            if not res['result']:
                raise Exception('Failed to delete HDFS file %s: %s' % (
                    res['path'], res.get('error')))

    def initUpload(self, upload):
        uid = uuid.uuid4().hex
        relPath = posixpath.join(uid[0:2], uid[2:4], uid)

        upload['hdfs'] = {
            'path': relPath
        }
        absPath = self._absPath(upload)
        parentDir = posixpath.dirname(absPath)

        if not self.client.test(parentDir, exists=True, directory=True):
            res = self.client.mkdir([posixpath.dirname(absPath)],
                                    create_parent=True).next()
            if not res['result']:
                raise Exception(res['error'])

        if self.client.test(absPath, exists=True):
            raise Exception('File already exists: %s.' % absPath)

        res = self.client.touchz([absPath]).next()
        if not res['result']:
            raise Exception(res['error'])

        return upload

    def uploadChunk(self, upload, chunk):
        # For now, we use webhdfs when writing files since the process of
        # implementing the append operation ourselves with protobuf is too
        # expensive. If snakebite adds support for append in future releases,
        # we should use that instead.
        url = ('http://%s:%d/webhdfs/v1%s?op=APPEND&namenoderpcaddress=%s:%d'
               '&user.name=%s')
        url %= (
            self.assetstore['hdfs']['host'],
            self.assetstore['hdfs']['webHdfsPort'],
            self._absPath(upload),
            self.assetstore['hdfs']['host'],
            self.assetstore['hdfs']['port'],
            self._getHdfsUser(self.assetstore)
        )

        resp = requests.post(url, allow_redirects=False)

        try:
            resp.raise_for_status()
        except Exception:
            logger.exception('HDFS response: ' + resp.text)
            raise Exception('Error appending to HDFS, see log for details.')

        if resp.status_code != 307:
            raise Exception('Expected 307 redirection to data node, instead '
                            'got %d: %s' % (resp.status_code, resp.text))

        resp = requests.post(resp.headers['Location'], data=chunk)
        chunk.close()
        try:
            resp.raise_for_status()
        except Exception:
            logger.exception('HDFS response: ' + resp.text)
            raise Exception('Error appending to HDFS, see log for details.')

        upload['received'] = self.requestOffset(upload)

        try:
            resp.raise_for_status()
        except Exception:
            logger.exception('HDFS response: ' + resp.text)
            raise Exception('Error appending to HDFS, see log for details.')

        return upload

    def finalizeUpload(self, upload, file):
        file['hdfs'] = upload['hdfs']
        return file

    def cancelUpload(self, upload):
        absPath = self._absPath(upload)
        if self.client.test(absPath, exists=True):
            res = self.client.delete([absPath]).next()
            if not res['result']:
                raise Exception('Failed to delete HDFS file %s: %s' % (
                    res['path'], res.get('error')))

    def requestOffset(self, upload):
        return self.client.stat([self._absPath(upload)])['length']
