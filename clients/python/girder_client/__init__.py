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

import diskcache
import errno
import getpass
import glob
import json
import mimetypes
import os
import re
import requests
import shutil
import six
import tempfile

__version__ = '2.0.0'
__license__ = 'Apache 2.0'

DEFAULT_PAGE_LIMIT = 50  # Number of results to fetch per request
REQ_BUFFER_SIZE = 65536  # Chunk size when iterating a download body

_safeNameRegex = re.compile(r'^[/\\]+')


def _compareDicts(x, y):
    """
    Compare two dictionaries with metadata.

    :param x: First metadata item.
    :param y: Second metadata item.
    """
    return len(x) == len(y) == len(set(x.items()) & set(y.items()))


def _safeMakedirs(path):
    """
    Wraps os.makedirs in such a way that it will not raise exceptions if the
    directory already exists.

    :param path: The directory to create.
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise  # pragma: no cover


class AuthenticationError(RuntimeError):
    pass


class IncorrectUploadLengthError(RuntimeError):
    def __init__(self, message, upload=None):
        super(IncorrectUploadLengthError, self).__init__(message)
        self.upload = upload


class HttpError(Exception):
    """
    Raised if the server returns an error status code from a request.
    """
    def __init__(self, status, text, url, method):
        super(HttpError, self).__init__('HTTP error %s: %s %s' % (status, method, url))
        self.status = status
        self.responseText = text
        self.url = url
        self.method = method

    def __str__(self):
        return super(HttpError, self).__str__() + '\nResponse text: ' + self.responseText


class GirderClient(object):
    """
    A class for interacting with the Girder RESTful API.
    Some simple examples of how to use this class follow:

    .. code-block:: python

        client = GirderClient(apiUrl='http://myhost:8080')
        client.authenticate('myname', 'mypass')

        folder_id = '53b714308926486402ac5aba'
        item = client.createItem(folder_id, 'an item name', 'a description')
        client.addMetadataToItem(item['_id'], {'metadatakey': 'metadatavalue'})
        client.uploadFileToItem(item['_id'], 'path/to/your/file.txt')

        r1 = client.getItem(item['_id'])
        r2 = client.sendRestRequest('GET', 'item',
            {'folderId': folder_id, 'sortdir': '-1' })
        r3 = client.sendRestRequest('GET', 'resource/search',
            {'q': 'aggregated','types': '["folder", "item"]'})
    """

    # A convenience dictionary mapping HTTP method names to functions in the
    # requests module
    METHODS = {
        'GET': requests.get,
        'POST': requests.post,
        'PUT': requests.put,
        'DELETE': requests.delete,
        'PATCH': requests.patch
    }

    # The current maximum chunk size for uploading file chunks
    MAX_CHUNK_SIZE = 1024 * 1024 * 64

    def __init__(self, host=None, port=None, apiRoot=None, scheme=None, apiUrl=None,
                 cacheSettings=None):
        """
        Construct a new GirderClient object, given a host name and port number,
        as well as a username and password which will be used in all requests
        (HTTP Basic Auth). You can pass the URL in parts with the `host`,
        `port`, `scheme`, and `apiRoot` kwargs, or simply pass it in all as
        one URL with the `apiUrl` kwarg instead. If you pass `apiUrl`, the
        individual part kwargs will be ignored.

        :param apiUrl: The full path to the REST API of a Girder instance, e.g.
            `http://my.girder.com/api/v1`.
        :param host: A string containing the host name where Girder is running,
            the default value is 'localhost'
        :param port: The port number on which to connect to Girder,
            the default value is 80 for http: and 443 for https:
        :param apiRoot: The path on the server corresponding to the root of the
            Girder REST API. If None is passed, assumes '/api/v1'.
        :param scheme: A string containing the scheme for the Girder host,
            the default value is 'http'; if you pass 'https' you likely want
            to pass 443 for the port
        :param cacheSettings: Settings to use with the diskcache library, or
            None to disable caching.
        """
        if apiUrl is None:
            if apiRoot is None:
                apiRoot = '/api/v1'

            self.scheme = scheme or 'http'
            self.host = host or 'localhost'
            self.port = port or (443 if scheme == 'https' else 80)

            self.urlBase = '%s://%s:%s%s' % (
                self.scheme, self.host, str(self.port), apiRoot)
        else:
            self.urlBase = apiUrl

        if self.urlBase[-1] != '/':
            self.urlBase += '/'

        self.token = ''
        self._folderUploadCallbacks = []
        self._itemUploadCallbacks = []
        self.incomingMetadata = {}
        self.localMetadata = {}

        if cacheSettings is None:
            self.cache = None
        else:
            self.cache = diskcache.Cache(**cacheSettings)

    def authenticate(self, username=None, password=None, interactive=False, apiKey=None):
        """
        Authenticate to Girder, storing the token that comes back to be used in
        future requests. This method can be used in two modes, either username
        and password authentication, or using an API key. Username example:

        .. code-block:: python

            gc.authenticate(username='myname', password='mypass')

        Note that you may also pass ``interactive=True`` and omit either the
        username or password argument to be prompted for them in the shell. The
        second mode is using an API key:

        .. code-block::python

            gc.authenticate(apiKey='J77R3rsLYYqFXXwQ4YquQtek1N26VEJ7IAVz9IpU')

        API keys can be created and managed on your user account page in the
        Girder web client, and can be used to provide limited access to the Girder web API.

        :param username: A string containing the username to use in basic authentication.
        :param password: A string containing the password to use in basic authentication.
        :param interactive: If you want the user to type their username or
            password in the shell rather than passing it in as an argument,
            set this to True. If you pass a username in interactive mode, the
            user will only be prompted for a password. This option only works
            in username/password mode, not API key mode.
        :param apiKey: Pass this to use an API key instead of username/password authentication.
        :type apiKey: str
        """
        if apiKey:
            resp = self.post('api_key/token', parameters={
                'key': apiKey
            })
            self.token = resp['authToken']['token']
        else:
            if interactive:
                if username is None:
                    username = six.moves.input('Login or email: ')
                password = getpass.getpass('Password for %s: ' % username)

            if username is None or password is None:
                raise Exception('A user name and password are required')

            url = self.urlBase + 'user/authentication'
            authResponse = requests.get(url, auth=(username, password))

            if authResponse.status_code == 404:
                raise HttpError(404, authResponse.text, url, 'GET')

            resp = authResponse.json()
            if 'authToken' not in resp:
                raise AuthenticationError()

            self.token = resp['authToken']['token']

    def sendRestRequest(self, method, path, parameters=None, data=None, files=None, json=None):
        """
        This method looks up the appropriate method, constructs a request URL
        from the base URL, path, and parameters, and then sends the request. If
        the method is unknown or if the path is not found, an exception is
        raised, otherwise a JSON object is returned with the Girder response.

        This is a convenience method to use when making basic requests that do
        not involve multipart file data that might need to be specially encoded
        or handled differently.

        :param method: The HTTP method to use in the request (GET, POST, etc.)
        :type method: str
        :param path: A string containing the path elements for this request.
            Note that the path string should not begin or end with the path  separator, '/'.
        :type path: str
        :param parameters: A dictionary mapping strings to strings, to be used
            as the key/value pairs in the request parameters.
        :type parameters: dict
        :param data: A dictionary, bytes or file-like object to send in the body.
        :param files: A dictonary of 'name' => file-like-objects for multipart encoding upload.
        :type files: dict
        :param json: A JSON object to send in the request body.
        :type json: dict
        """
        if not parameters:
            parameters = {}

        # Look up the HTTP method we need
        f = self.METHODS[method]

        # Construct the url
        url = self.urlBase + path

        # Make the request, passing parameters and authentication info
        result = f(
            url, params=parameters, data=data, files=files, json=json,
            headers={'Girder-Token': self.token})

        # If success, return the json object. Otherwise throw an exception.
        if result.status_code in (200, 201):
            return result.json()
        # TODO handle 300-level status (follow redirect?)
        else:
            raise HttpError(
                status=result.status_code, url=result.url, method=method, text=result.text)

    def get(self, path, parameters=None):
        """
        Convenience method to call :py:func:`sendRestRequest` with the 'GET' HTTP method.
        """
        return self.sendRestRequest('GET', path, parameters)

    def post(self, path, parameters=None, files=None, data=None, json=None):
        """
        Convenience method to call :py:func:`sendRestRequest` with the 'POST' HTTP method.
        """
        return self.sendRestRequest('POST', path, parameters, files=files,
                                    data=data, json=json)

    def put(self, path, parameters=None, data=None, json=None):
        """
        Convenience method to call :py:func:`sendRestRequest` with the 'PUT'
        HTTP method.
        """
        return self.sendRestRequest('PUT', path, parameters, data=data,
                                    json=json)

    def delete(self, path, parameters=None):
        """
        Convenience method to call :py:func:`sendRestRequest` with the 'DELETE' HTTP method.
        """
        return self.sendRestRequest('DELETE', path, parameters)

    def patch(self, path, parameters=None, data=None, json=None):
        """
        Convenience method to call :py:func:`sendRestRequest` with the 'PATCH' HTTP method.
        """
        return self.sendRestRequest('PATCH', path, parameters, data=data,
                                    json=json)

    def createResource(self, path, params):
        """
        Creates and returns a resource.
        """
        return self.post(path, params)

    def getResource(self, path, id=None, property=None):
        """
        Returns a resource based on ``id`` or None if no resource is found; if
        ``property`` is passed, returns that property value from the found resource.
        """
        route = path
        if id is not None:
            route += '/%s' % id
        if property is not None:
            route += '/%s' % property

        return self.get(route)

    def resourceLookup(self, path, test=False):
        """
        Look up and retrieve resource in the data hierarchy by path.

        :param path: The path of the resource. The path must be an absolute
            Unix path starting with either "/user/[user name]" or
            "/collection/[collection name]".
        :param test: Whether or not to return None, if the path does not
            exist, rather than throwing an exception.
        """
        return self.get('resource/lookup', parameters={'path': path, 'test': test})

    def listResource(self, path, params=None, limit=None, offset=None):
        """
        This is a generator that will yield records using the given path and
        params until exhausted. Paging of the records is done internally, but
        can be overriden by manually passing a ``limit`` value to select only
        a single page. Passing an ``offset`` will work in both single-page and
        exhaustive modes.
        """
        params = dict(params or {})
        params['offset'] = offset or 0
        params['limit'] = limit or DEFAULT_PAGE_LIMIT

        while True:
            records = self.get(path, params)
            for record in records:
                yield record

            n = len(records)
            if limit or n < params['limit']:
                # Either a single slice was requested, or this is the last page
                break

            params['offset'] += n

    def setResourceTimestamp(self, id, type, created=None, updated=None):
        """
        Set the created or updated timestamps for a resource.
        """
        url = 'resource/%s/timestamp' % id
        params = {
            'type': type,
        }
        if created:
            params['created'] = str(created)
        if updated:
            params['updated'] = str(updated)
        return self.put(url, parameters=params)

    def getFile(self, fileId):
        """
        Retrieves a file by its ID.

        :param fileId: A string containing the ID of the file to retrieve from Girder.
        """
        return self.getResource('file', fileId)

    def listFile(self, itemId, limit=None, offset=None):
        """
        This is a generator that will yield files under the given itemId.

        :param itemId: the item's ID
        :param limit: the result set size limit.
        :param offset: the result offset.
        """
        return self.listResource('item/%s/files' % itemId, params={
            'id': itemId,
        }, limit=limit, offset=offset)

    def createItem(self, parentFolderId, name, description='', reuseExisting=False):
        """
        Creates and returns an item.
        """
        params = {
            'folderId': parentFolderId,
            'name': name,
            'description': description,
            'reuseExisting': reuseExisting
        }
        return self.createResource('item', params)

    def getItem(self, itemId):
        """
        Retrieves a item by its ID.

        :param itemId: A string containing the ID of the item to retrieve from Girder.
        """
        return self.getResource('item', itemId)

    def listItem(self, folderId, text=None, name=None, limit=None, offset=None):
        """
        This is a generator that will yield all items under a given folder.

        :param folderId: the parent folder's ID.
        :param text: query for full text search of items.
        :param name: query for exact name match of items.
        :param limit: If requesting a specific slice, the length of the slice.
        :param offset: Starting offset into the list.
        """
        params = {
            'folderId': folderId
        }
        if text:
            params['text'] = text
        if name:
            params['name'] = name

        return self.listResource('item', params, limit=limit, offset=offset)

    def listUser(self, limit=None, offset=None):
        """
        This is a generator that will yield all users in the system.

        :param limit: If requesting a specific slice, the length of the slice.
        :param offset: Starting offset into the list.
        """
        return self.listResource('user', limit=limit, offset=offset)

    def getUser(self, userId):
        """
        Retrieves a user by its ID.

        :param userId: A string containing the ID of the user to
            retrieve from Girder.
        """
        return self.getResource('user', userId)

    def createUser(self, login, email, firstName, lastName, password, admin=None):
        """
        Creates and returns a user.
        """
        params = {
            'login': login,
            'email': email,
            'firstName': firstName,
            'lastName': lastName,
            'password': password
        }
        if admin is not None:
            params['admin'] = admin
        return self.createResource('user', params)

    def listCollection(self, limit=None, offset=None):
        """
        This is a generator that will yield all collections in the system.

        :param limit: If requesting a specific slice, the length of the slice.
        :param offset: Starting offset into the list.
        """
        return self.listResource('collection', limit=limit, offset=offset)

    def getCollection(self, collectionId):
        """
        Retrieves a collection by its ID.

        :param collectionId: A string containing the ID of the collection to
            retrieve from Girder.
        """
        return self.getResource('collection', collectionId)

    def createCollection(self, name, description='', public=False):
        """
        Creates and returns a collection.
        """
        params = {
            'name': name,
            'description': description,
            'public': public
        }
        return self.createResource('collection', params)

    def createFolder(self, parentId, name, description='', parentType='folder', public=None):
        """
        Creates and returns a folder.

        :param parentType: One of ('folder', 'user', 'collection')
        """
        params = {
            'parentId': parentId,
            'parentType': parentType,
            'name': name,
            'description': description
        }
        if public is not None:
            params['public'] = public
        return self.createResource('folder', params)

    def getFolder(self, folderId):
        """
        Retrieves a folder by its ID.

        :param folderId: A string containing the ID of the folder to retrieve from Girder.
        """
        return self.getResource('folder', folderId)

    def listFolder(self, parentId, parentFolderType='folder', name=None,
                   limit=None, offset=None):
        """
        This is a generator that will yield a list of folders based on the filter parameters.

        :param parentId: The parent's ID.
        :param parentFolderType: One of ('folder', 'user', 'collection').
        :param name: query for exact name match of items.
        :param limit: If requesting a specific slice, the length of the slice.
        :param offset: Starting offset into the list.
        """
        params = {
            'parentId': parentId,
            'parentType': parentFolderType
        }

        if name:
            params['name'] = name

        return self.listResource('folder', params, limit=limit, offset=offset)

    def getFolderAccess(self, folderId):
        """
        Retrieves a folder's access by its ID.

        :param folderId: A string containing the ID of the folder to retrieve
            access for from Girder.
        """
        return self.getResource('folder', folderId, 'access')

    def setFolderAccess(self, folderId, access, public):
        """
        Sets the passed in access control document along with the public value
        to the target folder.

        :param folderId: Id of the target folder.
        :param access: JSON document specifying access control.
        :param public: Boolean specificying the public value.
        """
        path = 'folder/' + folderId + '/access'
        params = {
            'access': access,
            'public': public
        }
        return self.put(path, params)

    def _fileChunker(self, filepath, filesize=None):
        """
        Generator returning chunks of a file in MAX_CHUNK_SIZE increments.

        :param filepath: path to file on disk.
        :param filesize: size of file on disk if known.
        """
        if filesize is None:
            filesize = os.path.getsize(filepath)
        startbyte = 0
        nextChunkSize = min(self.MAX_CHUNK_SIZE, filesize - startbyte)
        with open(filepath, 'rb') as fd:
            while nextChunkSize > 0:
                chunk = fd.read(nextChunkSize)
                yield (chunk, startbyte)
                startbyte = startbyte + nextChunkSize
                nextChunkSize = min(self.MAX_CHUNK_SIZE, filesize - startbyte)

    def isFileCurrent(self, itemId, filename, filepath):
        """
        Tests whether the passed in filepath exists in the item with itemId,
        with a name of filename, and with the same length.  Returns a tuple
        (file_id, current) where file_id = id of the file with that filename
        under the item, or None if no such file exists under the item.
        current = boolean if the file with that filename under the item
        has the same size as the file at filepath.

        :param itemId: ID of parent item for file.
        :param filename: name of file to look for under the parent item.
        :param filepath: path to file on disk.
        """
        path = 'item/' + itemId + '/files'
        itemFiles = self.get(path)
        for itemFile in itemFiles:
            if filename == itemFile['name']:
                file_id = itemFile['_id']
                size = os.path.getsize(filepath)
                return (file_id, size == itemFile['size'])
        # Some files may already be stored under a different name, we'll need
        # to upload anyway in this case also.
        return (None, False)

    def uploadFileToItem(self, itemId, filepath, reference=None, mimeType=None):
        """
        Uploads a file to an item, in chunks.
        If ((the file already exists in the item with the same name and size)
        or (if the file has 0 bytes), no uploading will be performed.

        :param itemId: ID of parent item for file.
        :param filepath: path to file on disk.
        :param reference: optional reference to send along with the upload.
        :type reference: str
        :param mimeType: MIME type for the file. Will be guessed if not passed.
        :type mimeType: str or None
        :returns: the file that was created.
        """
        filename = os.path.basename(filepath)
        filepath = os.path.abspath(filepath)
        filesize = os.path.getsize(filepath)

        if filesize == 0:
            return

        # Check if the file already exists by name and size in the file.
        fileId, current = self.isFileCurrent(itemId, filename, filepath)
        if fileId is not None and current:
            print('File %s already exists in parent Item' % filename)
            return

        if fileId is not None and not current:
            print('File %s exists in item, but with stale contents' % filename)
            path = 'file/%s/contents' % fileId
            params = {
                'size': filesize
            }
            if reference:
                params['reference'] = reference
            obj = self.put(path, params)
            if '_id' in obj:
                uploadId = obj['_id']
            else:
                raise Exception(
                    'After creating an upload token for replacing file '
                    'contents, expected an object with an id. Got instead: ' +
                    json.dumps(obj))
        else:
            if mimeType is None:
                # Attempt to guess MIME type if not passed explicitly
                mimeType, _ = mimetypes.guess_type(filepath)

            params = {
                'parentType': 'item',
                'parentId': itemId,
                'name': filename,
                'size': filesize,
                'mimeType': mimeType
            }
            if reference:
                params['reference'] = reference
            obj = self.post('file', params)
            if '_id' in obj:
                uploadId = obj['_id']
            else:
                raise Exception(
                    'After creating an upload token for a new file, expected '
                    'an object with an id. Got instead: ' + json.dumps(obj))

        for chunk, startbyte in self._fileChunker(filepath, filesize):
            parameters = {
                'offset': startbyte,
                'uploadId': uploadId
            }
            filedata = {
                'chunk': chunk
            }
            path = 'file/chunk'
            obj = self.post(path, parameters=parameters, files=filedata)

            if '_id' not in obj:
                raise Exception(
                    'After uploading a file chunk, did not receive object with _id. Got instead: ' +
                    json.dumps(obj))
        return obj

    def _uploadContents(self, uploadObj, stream, size, progressCallback=None):
        """
        Uploads contents of a file.

        :param uploadObj: The upload object contain the upload id.
        :type uploadObj: dict
        :param stream: Readable stream object.
        :type stream: file-like
        :param size: The length of the file. This must be exactly equal to the
            total number of bytes that will be read from ``stream``, otherwise
            the upload will fail.
        :type size: str
        :param progressCallback: If passed, will be called after each chunk
            with progress information. It passes a single positional argument
            to the callable which is a dict of information about progress.
        :type progressCallback: callable
        """
        offset = 0
        uploadId = uploadObj['_id']
        while True:
            data = stream.read(min(self.MAX_CHUNK_SIZE, (size - offset)))

            if not data:
                break

            params = {
                'offset': offset,
                'uploadId': uploadId
            }
            files = {
                'chunk': data
            }
            uploadObj = self.post('file/chunk', parameters=params, files=files)
            offset += len(data)

            if '_id' not in uploadObj:
                raise Exception(
                    'After uploading a file chunk, did not receive object with _id. Got instead: ' +
                    json.dumps(uploadObj))

            if callable(progressCallback):
                progressCallback({
                    'current': offset,
                    'total': size
                })

        if offset != size:
            self.delete('file/upload/' + uploadId)
            raise IncorrectUploadLengthError(
                'Expected upload to be %d bytes, but received %d.' % (size, offset),
                upload=uploadObj)

        return uploadObj

    def uploadFile(self, parentId, stream, name, size, parentType='item',
                   progressCallback=None, reference=None, mimeType=None):
        """
        Uploads a file into an item or folder.

        :param parentId: The ID of the folder or item to upload into.
        :type parentId: str
        :param stream: Readable stream object.
        :type stream: file-like
        :param name: The name of the file to create.
        :type name: str
        :param size: The length of the file. This must be exactly equal to the
            total number of bytes that will be read from ``stream``, otherwise
            the upload will fail.
        :type size: str
        :param parentType: 'item' or 'folder'.
        :type parentType: str
        :param progressCallback: If passed, will be called after each chunk
            with progress information. It passes a single positional argument
            to the callable which is a dict of information about progress.
        :type progressCallback: callable
        :param reference: optional reference to send along with the upload.
        :type reference: str
        :param mimeType: MIME type to set on the file. Attempts to guess if not
            explicitly passed.
        :type mimeType: str or None
        :returns: The file that was created on the server.
        """
        params = {
            'parentType': parentType,
            'parentId': parentId,
            'name': name,
            'size': size,
            'mimeType': mimeType or mimetypes.guess_type(name)[0]
        }
        if reference is not None:
            params['reference'] = reference
        obj = self.post('file', params)
        if '_id' not in obj:
            raise Exception(
                'After creating an upload token for a new file, expected '
                'an object with an id. Got instead: ' + json.dumps(obj))

        return self._uploadContents(obj, stream, size, progressCallback=progressCallback)

    def uploadFileContents(self, fileId, stream, size, reference=None):
        """
        Uploads the contents of an existing file.

        :param fileId: ID of file to update
        :param stream: Readable stream object.
        :type stream: file-like
        :param size: The length of the file. This must be exactly equal to the
            total number of bytes that will be read from ``stream``, otherwise
            the upload will fail.
        :type size: str
        :param reference: optional reference to send along with the upload.
        :type reference: str
        """
        path = 'file/%s/contents' % fileId
        params = {
            'size': size
        }
        if reference:
            params['reference'] = reference

        obj = self.put(path, params)
        if '_id' not in obj:
            raise Exception(
                'After creating an upload token for replacing file '
                'contents, expected an object with an id. Got instead: ' +
                json.dumps(obj))

        return self._uploadContents(obj, stream, size)

    def addMetadataToItem(self, itemId, metadata):
        """
        Takes an item ID and a dictionary containing the metadata

        :param itemId: ID of the item to set metadata on.
        :param metadata: dictionary of metadata to set on item.
        """
        path = 'item/' + itemId + '/metadata'
        obj = self.put(path, json=metadata)
        return obj

    def addMetadataToFolder(self, folderId, metadata):
        """
        Takes an folder ID and a dictionary containing the metadata

        :param folderId: ID of the folder to set metadata on.
        :param metadata: dictionary of metadata to set on folder.
        """
        path = 'folder/' + folderId + '/metadata'
        obj = self.put(path, json=metadata)
        return obj

    def transformFilename(self, name):
        """
        Sanitize a resource name from Girder into a name that is safe to use
        as a filesystem path.

        :param name: The name to transform.
        :type name: str
        """
        if name in ('.', '..'):
            name = '_' + name
        name = name.replace(os.path.sep, '_')
        if os.path.altsep:
            name = name.replace(os.path.altsep, '_')
        return _safeNameRegex.sub('_', name)

    def _copyFile(self, fp, path):
        """
        Copy the `fp` file-like object to `path` which may be a filename string
        or another file-like object to write to.
        """
        if isinstance(path, six.string_types):
            _safeMakedirs(os.path.dirname(path))
            with open(path, 'wb') as dst:
                shutil.copyfileobj(fp, dst)
        else:
            # assume `path` is a file-like object
            shutil.copyfileobj(fp, path)

    def downloadFile(self, fileId, path, created=None):
        """
        Download a file to the given local path or file-like object.

        :param fileId: The ID of the Girder file to download.
        :param path: The path to write the file to, or a file-like object.
        """
        created = created or self.getFile(fileId)['created']
        cacheKey = '\n'.join([self.urlBase, fileId, created])

        # see if file is in local cache
        if self.cache is not None:
            fp = self.cache.get(cacheKey, read=True)
            if fp:
                with fp:
                    self._copyFile(fp, path)
                return

        # download to a tempfile
        req = requests.get(
            '%sfile/%s/download' % (self.urlBase, fileId),
            stream=True, headers={'Girder-Token': self.token})
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in req.iter_content(chunk_size=REQ_BUFFER_SIZE):
                tmp.write(chunk)

        # save file in cache
        if self.cache is not None:
            with open(tmp.name, 'rb') as fp:
                self.cache.set(cacheKey, fp, read=True)

        if isinstance(path, six.string_types):
            # we can just rename the tempfile
            _safeMakedirs(os.path.dirname(path))
            shutil.move(tmp.name, path)
        else:
            # write to file-like object
            with open(tmp.name, 'rb') as fp:
                shutil.copyfileobj(fp, path)
            # delete the temp file
            os.remove(tmp.name)

    def downloadItem(self, itemId, dest, name=None):
        """
        Download an item from Girder into a local folder. Each file in the
        item will be placed into the directory specified by the dest parameter.
        If the item contains multiple files or a single file with a different
        name than the item, the item will be created as a directory under dest
        and the files will become files within that directory.

        :param itemId: The Id of the Girder item to download.
        :param dest: The destination directory to write the item into.
        :param name: If the item name is known in advance, you may pass it here
            which will save a lookup to the server.
        """
        if name is None:
            item = self.get('item/' + itemId)
            name = item['name']

        offset = 0
        first = True
        while True:
            files = self.get('item/%s/files' % itemId, parameters={
                'limit': DEFAULT_PAGE_LIMIT,
                'offset': offset
            })

            if first:
                if len(files) == 1 and files[0]['name'] == name:
                    self.downloadFile(
                        files[0]['_id'],
                        os.path.join(dest, self.transformFilename(name)),
                        created=files[0]['created'])
                    break
                else:
                    dest = os.path.join(dest, self.transformFilename(name))
                    _safeMakedirs(dest)

            for file in files:
                self.downloadFile(
                    file['_id'],
                    os.path.join(dest, self.transformFilename(file['name'])),
                    created=file['created'])

            first = False
            offset += len(files)
            if len(files) < DEFAULT_PAGE_LIMIT:
                break

    def downloadFolderRecursive(self, folderId, dest, sync=False):
        """
        Download a folder recursively from Girder into a local directory.

        :param folderId: Id of the Girder folder or resource path to download.
        :type folderId: ObjectId or Unix-style path to the resource in Girder.
        :param dest: The local download destination.
        :type dest: str
        :param sync: If True, check if item exists in local metadata
            cache and skip download provided that metadata is identical.
        :type sync: bool
        """
        offset = 0
        folderId = self._checkResourcePath(folderId)
        while True:
            folders = self.get('folder', parameters={
                'limit': DEFAULT_PAGE_LIMIT,
                'offset': offset,
                'parentType': 'folder',
                'parentId': folderId
            })

            for folder in folders:
                local = os.path.join(dest, self.transformFilename(folder['name']))
                _safeMakedirs(local)

                self.downloadFolderRecursive(folder['_id'], local, sync=sync)

            offset += len(folders)
            if len(folders) < DEFAULT_PAGE_LIMIT:
                break

        offset = 0

        while True:
            items = self.get('item', parameters={
                'folderId': folderId,
                'limit': DEFAULT_PAGE_LIMIT,
                'offset': offset
            })

            for item in items:
                _id = item['_id']
                self.incomingMetadata[_id] = item
                if (sync and _id in self.localMetadata and
                        _compareDicts(item, self.localMetadata[_id])):
                    continue
                self.downloadItem(item['_id'], dest, name=item['name'])

            offset += len(items)
            if len(items) < DEFAULT_PAGE_LIMIT:
                break

    def downloadResource(self, resourceId, dest, resourceType='folder', sync=False):
        """
        Download a collection, user, or folder recursively from Girder into a local directory.

        :param resourceId: ID or path of the resource to download.
        :type resourceId: ObjectId or Unix-style path to the resource in Girder.
        :param dest: The local download destination. Can be an absolute path or relative to
            the current working directory.
        :type dest: str
        :param resourceType: The type of resource being downloaded: 'collection', 'user',
            or 'folder'.
        :type resourceType: str
        :param sync: If True, check if items exist in local metadata
            cache and skip download if the metadata is identical.
        :type sync: bool
        """
        if resourceType == 'folder':
            self.downloadFolderRecursive(resourceId, dest, sync)
        elif resourceType in ('collection', 'user'):
            offset = 0
            resourceId = self._checkResourcePath(resourceId)
            while True:
                folders = self.get('folder', parameters={
                    'limit': DEFAULT_PAGE_LIMIT,
                    'offset': offset,
                    'parentType': resourceType,
                    'parentId': resourceId
                })

                for folder in folders:
                    local = os.path.join(dest, self.transformFilename(folder['name']))
                    _safeMakedirs(local)

                    self.downloadFolderRecursive(folder['_id'], local, sync=sync)

                offset += len(folders)
                if len(folders) < DEFAULT_PAGE_LIMIT:
                    break
        else:
            raise Exception('Invalid resource type: %s' % resourceType)

    def saveLocalMetadata(self, dest):
        """
        Dumps item metadata collected during a folder download.

        :param dest: The local download destination.
        """
        with open(os.path.join(dest, '.girder_metadata'), 'w') as fh:
            fh.write(json.dumps(self.incomingMetadata))

    def loadLocalMetadata(self, dest):
        """
        Reads item metadata from a local folder.

        :param dest: The local download destination.
        """

        try:
            with open(os.path.join(dest, '.girder_metadata'), 'r') as fh:
                self.localMetadata = json.loads(fh.read())
        except (IOError, OSError):
            print('Local metadata does not exists. Falling back to download.')

    def inheritAccessControlRecursive(self, ancestorFolderId, access=None, public=None):
        """
        Take the access control and public value of a folder and recursively
        copy that access control and public value to all folder descendants,
        replacing any existing access control on the descendant folders with
        that of the ancestor folder.

        :param ancestorFolderId: Id of the Girder folder to copy access
            control from, to all of its descendant folders.
        :param access: Dictionary Access control target, if None, will take
            existing access control of ancestor folder
        :param public: Boolean public value target, if None, will take existing
            public value of ancestor folder
        """
        offset = 0

        if public is None:
            public = self.getFolder(ancestorFolderId)['public']

        if access is None:
            access = self.getFolderAccess(ancestorFolderId)

        while True:
            self.setFolderAccess(ancestorFolderId, json.dumps(access), public)

            folders = self.get('folder', parameters={
                'limit': DEFAULT_PAGE_LIMIT,
                'offset': offset,
                'parentType': 'folder',
                'parentId': ancestorFolderId
            })

            for folder in folders:
                self.inheritAccessControlRecursive(folder['_id'], access, public)

            offset += len(folders)
            if len(folders) < DEFAULT_PAGE_LIMIT:
                break

    def addFolderUploadCallback(self, callback):
        """Saves a passed in callback function that will be called after each
        folder has completed.  Multiple callback functions can be added, they
        will be called in the order they were added by calling this function.
        Callback functions will be called after a folder in Girder is created
        and all subfolders and items for that folder have completed uploading.
        Callback functions should take two parameters:
        - the folder in Girder
        - the full path to the local folder

        :param callback: callback function to be called.
        """
        self._folderUploadCallbacks.append(callback)

    def addItemUploadCallback(self, callback):
        """Saves a passed in callback function that will be called after each
        item has completed.  Multiple callback functions can be added, they
        will be called in the order they were added by calling this function.
        Callback functions will be called after an item in Girder is created
        and all files for that item have been uploaded.  Callback functions
        should take two parameters:
        - the item in Girder
        - the full path to the local folder or file comprising the item

        :param callback: callback function to be called.
        """
        self._itemUploadCallbacks.append(callback)

    def loadOrCreateFolder(self, folderName, parentId, parentType):
        """Returns a folder in Girder with the given name under the given
        parent. If none exists yet, it will create it and return it.

        :param folderName: the name of the folder to look up.
        :param parentId: id of parent in Girder
        :param parentType: one of (collection, folder, user)
        :returns: The folder that was found or created.
        """
        children = self.listFolder(parentId, parentType, name=folderName)

        try:
            return six.next(children)
        except StopIteration:
            return self.createFolder(parentId, folderName, parentType=parentType)

    def _hasOnlyFiles(self, localFolder):
        """Returns whether a folder has only files. This will be false if the
        folder contains any subdirectories.
        :param localFolder: full path to the local folder
        """
        return not any(os.path.isdir(os.path.join(localFolder, entry))
                       for entry in os.listdir(localFolder))

    def loadOrCreateItem(self, name, parentFolderId, reuseExisting=True):
        """Create an item with the given name in the given parent folder.

        :param name: The name of the item to load or create.
        :param parentFolderId: id of parent folder in Girder
        :param reuseExisting: boolean indicating whether to load an existing
            item of the same name in the same location, or create a new one.
        """
        item = None
        if reuseExisting:
            children = self.listItem(parentFolderId, name=name)
            try:
                item = six.next(children)
            except StopIteration:
                pass

        if item is None:
            item = self.createItem(parentFolderId, name, description='')

        return item

    def _uploadFileToItem(self, localFile, parentItemId, filePath):
        """Helper function to upload a file to an item
        :param localFile: name of local file to upload
        :param parentItemId: id of parent item in Girder to add file to
        :param filePath: full path to the file
        """
        self.uploadFileToItem(parentItemId, filePath)

    def _uploadAsItem(self, localFile, parentFolderId, filePath, reuseExisting=False, dryRun=False):
        """Function for doing an upload of a file as an item.
        :param localFile: name of local file to upload
        :param parentFolderId: id of parent folder in Girder
        :param filePath: full path to the file
        :param reuseExisting: boolean indicating whether to accept an existing item
            of the same name in the same location, or create a new one instead
        """
        print('Uploading Item from %s' % localFile)
        if not dryRun:
            currentItem = self.loadOrCreateItem(
                os.path.basename(localFile), parentFolderId, reuseExisting)
            self._uploadFileToItem(localFile, currentItem['_id'], filePath)

            for callback in self._itemUploadCallbacks:
                callback(currentItem, filePath)

    def _uploadFolderAsItem(self, localFolder, parentFolderId, reuseExisting=False, blacklist=None,
                            dryRun=False):
        """
        Take a folder and use its base name as the name of a new item. Then,
        upload its containing files into the new item as bitstreams.

        :param localFolder: The path to the folder to be uploaded.
        :param parentFolderId: Id of the destination folder for the new item.
        :param reuseExisting: boolean indicating whether to accept an existing item
            of the same name in the same location, or create a new one instead
        """
        blacklist = blacklist or []
        print('Creating Item from folder %s' % localFolder)
        if not dryRun:
            item = self.loadOrCreateItem(
                os.path.basename(localFolder), parentFolderId, reuseExisting)

        subdircontents = sorted(os.listdir(localFolder))
        # for each file in the subdir, add it to the item
        filecount = len(subdircontents)
        for (ind, currentFile) in enumerate(subdircontents):
            filepath = os.path.join(localFolder, currentFile)
            if currentFile in blacklist:
                if dryRun:
                    print('Ignoring file %s as blacklisted' % currentFile)
                continue
            print('Adding file %s, (%d of %d) to Item' % (currentFile, ind + 1, filecount))

            if not dryRun:
                self._uploadFileToItem(currentFile, item['_id'], filepath)

        if not dryRun:
            for callback in self._itemUploadCallbacks:
                callback(item, localFolder)

    def _uploadFolderRecursive(self, localFolder, parentId, parentType, leafFoldersAsItems=False,
                               reuseExisting=False, blacklist=None, dryRun=False):
        """
        Function to recursively upload a folder and all of its descendants.

        :param localFolder: full path to local folder to be uploaded
        :param parentId: id of parent in Girder, where new folder will be added
        :param parentType: one of (collection, folder, user)
        :param leafFoldersAsItems: whether leaf folders should have all
            files uploaded as single items
        :param reuseExisting: boolean indicating whether to accept an existing item
            of the same name in the same location, or create a new one instead
        """
        blacklist = blacklist or []
        if leafFoldersAsItems and self._hasOnlyFiles(localFolder):
            if parentType != 'folder':
                raise Exception(
                    ('Attempting to upload a folder as an item under a %s. '
                     % parentType) + 'Items can only be added to folders.')
            else:
                self._uploadFolderAsItem(localFolder, parentId, reuseExisting, dryRun=dryRun)
        else:
            filename = os.path.basename(localFolder)
            if filename in blacklist:
                if dryRun:
                    print('Ignoring file %s as it is blacklisted' % filename)
                return

            print('Creating Folder from %s' % localFolder)
            if dryRun:
                # create a dry run placeholder
                folder = {'_id': 'dryrun'}
            else:
                folder = self.loadOrCreateFolder(
                    os.path.basename(localFolder), parentId, parentType)

            for entry in sorted(os.listdir(localFolder)):
                if entry in blacklist:
                    if dryRun:
                        print('Ignoring file %s as it is blacklisted' % entry)
                    continue
                fullEntry = os.path.join(localFolder, entry)
                if os.path.islink(fullEntry):
                    # os.walk skips symlinks by default
                    print('Skipping file %s as it is a symlink' % entry)
                    continue
                elif os.path.isdir(fullEntry):
                    # At this point we should have an actual folder, so can
                    # pass that as the parent_type
                    self._uploadFolderRecursive(
                        fullEntry, folder['_id'], 'folder', leafFoldersAsItems, reuseExisting,
                        dryRun=dryRun)
                else:
                    self._uploadAsItem(
                        entry, folder['_id'], fullEntry, reuseExisting, dryRun=dryRun)

            if not dryRun:
                for callback in self._folderUploadCallbacks:
                    callback(folder, localFolder)

    def upload(self, filePattern, parentId, parentType='folder', leafFoldersAsItems=False,
               reuseExisting=False, blacklist=None, dryRun=False):
        """
        Upload a pattern of files.

        This will recursively walk down every tree in the file pattern to
        create a hierarchy on the server under the parentId.

        :param filePattern: a glob pattern for files that will be uploaded,
            recursively copying any file folder structures.
        :type filePattern: str
        :param parentId: Id of the parent in Girder or resource path.
        :type parentId: ObjectId or Unix-style path to the resource in Girder.
        :param parentType: one of (collection,folder,user), default of folder.
        :type parentType: str
        :param leafFoldersAsItems: bool whether leaf folders should have all
            files uploaded as single items.
        :type leafFoldersAsItems: bool
        :param reuseExisting: bool whether to accept an existing item of
            the same name in the same location, or create a new one instead.
        :type reuseExisting: bool
        :param dryRun: Set this to True to print out what actions would be taken, but
            do not actually communicate with the server.
        :type dryRun: bool
        """
        blacklist = blacklist or []
        empty = True
        parentId = self._checkResourcePath(parentId)
        for currentFile in glob.iglob(filePattern):
            empty = False
            currentFile = os.path.normpath(currentFile)
            filename = os.path.basename(currentFile)
            if filename in blacklist:
                if dryRun:
                    print('Ignoring file %s as it is blacklisted' % filename)
                continue
            if os.path.isfile(currentFile):
                if parentType != 'folder':
                    raise Exception(
                        'Attempting to upload an item under a %s. Items can only be added to '
                        'folders.' % parentType)
                else:
                    self._uploadAsItem(
                        os.path.basename(currentFile), parentId, currentFile, reuseExisting,
                        dryRun=dryRun)
            else:
                self._uploadFolderRecursive(
                    currentFile, parentId, parentType, leafFoldersAsItems, reuseExisting,
                    blacklist=blacklist, dryRun=dryRun)
        if empty:
            print('No matching files: ' + filePattern)

    def _checkResourcePath(self, objId):
        if isinstance(objId, six.string_types) and objId.startswith('/'):
            obj = self.resourceLookup(objId, test=True)
            if obj is not None:
                return obj['_id']
        return objId
