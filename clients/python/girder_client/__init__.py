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

import errno
import getpass
import hashlib
import json
import os
import re
import requests


_safeNameRegex = re.compile(r'^[/\\]+')


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
            raise


class AuthenticationError(RuntimeError):
    pass


class GirderClient(object):
    """
    A class for interacting with the girder restful api.
    Some simple examples of how to use this class follow:

    .. code-block:: python

        client = GirderClient('myhost', 8080)
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
        'DELETE': requests.delete
    }

    # The current maximum chunk size for uploading file chunks
    MAX_CHUNK_SIZE = 1024 * 1024 * 64

    def __init__(self, host="localhost", port=8080, apiRoot=None,
                 scheme="http"):
        """
        Construct a new GirderClient object, given a host name and port number,
        as well as a username and password which will be used in all requests
        (HTTP Basic Auth).

        :param host: A string containing the host name where Girder is running,
            the default value is 'localhost'
        :param port: The port number on which to connect to Girder,
            the default value is 8080
        :param apiRoot: The path on the server corresponding to the root of the
            Girder REST API. If None is passed, assumes '/api/v1'.
        :param scheme: A string containing the scheme for the Girder host,
            the default value is 'http'; if you pass 'https' you likely want
            to pass 443 for the port
        """
        if apiRoot is None:
            apiRoot = '/api/v1'

        self.scheme = scheme
        self.host = host
        self.port = port

        self.urlBase = self.scheme + '://' + self.host + ':' + str(self.port) \
            + apiRoot

        if self.urlBase[-1] != '/':
            self.urlBase += '/'

        self.token = ''

    def authenticate(self, username=None, password=None, interactive=False):
        """
        Authenticate to Girder, storing the token that comes back to be used in
        future requests.

        :param username: A string containing the username to use in basic
            authentication.
        :param password: A string containing the password to use in basic
            authentication.
        :param interactive: If you want the user to type their username or
            password in the shell rather than passing it in as an argument,
            set this to True. If you pass a username in interactive mode, the
            user will only be prompted for a password.
        """
        if interactive:
            if username is None:
                username = raw_input('Login or email: ')
            password = getpass.getpass('Password for %s: ' % username)

        if username is None or password is None:
            raise Exception('A user name and password are required')

        authResponse = requests.get(self.urlBase + 'user/authentication',
                                    auth=(username, password)).json()

        if 'authToken' not in authResponse:
            raise AuthenticationError()

        self.token = authResponse['authToken']['token']

    def sendRestRequest(self, method, path, parameters=None, data=None,
                        files=None):
        """
        This method looks up the appropriate method, constructs a request URL
        from the base URL, path, and parameters, and then sends the request. If
        the method is unknown or if the path is not found, an exception is
        raised, otherwise a JSON object is returned with the Girder response.

        This is a convenience method to use when making basic requests that do
        not involve multipart file data that might need to be specially encoded
        or handled differently.

        :param method: One of 'GET', 'POST', 'PUT', or 'DELETE'
        :param path: A string containing the path elements for this request.
            Note that the path string should not begin or end with the path
            separator, '/'.
        :param parameters: A dictionary mapping strings to strings, to be used
            as the key/value pairs in the request parameters
        """
        if not parameters:
            parameters = {}

        # Make sure we got a valid method
        assert method in self.METHODS

        # Look up the HTTP method we need
        f = self.METHODS[method]

        # Construct the url
        url = self.urlBase + path

        # Make the request, passing parameters and authentication info
        result = f(url, params=parameters, data=data, files=files, headers={
            'Girder-Token': self.token
        })

        # If success, return the json object. Otherwise throw an exception.
        if result.status_code == 200:
            return result.json()
        else:
            print 'Showing result before raising exception:'
            print result.text
            raise Exception('Request: ' + result.url + ', return code: ' +
                            str(result.status_code))

    def get(self, path, parameters=None):
        return self.sendRestRequest('GET', path, parameters)

    def post(self, path, parameters=None, files=None):
        return self.sendRestRequest('POST', path, parameters, files=files)

    def put(self, path, parameters=None, data=None):
        return self.sendRestRequest('PUT', path, parameters, data=data)

    def delete(self, path, parameters=None):
        return self.sendRestRequest('DELETE', path, parameters)

    def createResource(self, path,  params):
        """
        Creates and returns a resource.
        """
        obj = self.post(path, params)
        if '_id' in obj:
            return obj
        else:
            raise Exception('Error, expected the returned '+path+' object to'
                            'have an "_id" field')

    def getResource(self, path, id, property=None):
        """
        Loads a resource or resource property of property is not None
        by id or None if no resource is returned.
        """
        if property is not None:
            return self.get(path + '/' + id + '/' + property)
        else:
            return self.get(path + '/' + id)

    def listResource(self, path, params):
        """
        search for a list of resources based on params.
        """
        return self.get(path, params)

    def createItem(self, parentFolderId, name, description):
        """
        Creates and returns an item.
        """
        path = 'item'
        params = {
            'folderId': parentFolderId,
            'name': name,
            'description': description
        }
        return self.createResource(path, params)

    def getItem(self, itemId):
        """
        Retrieves a item by its ID.

        :param itemId: A string containing the ID of the item to retrieve from
            Girder.
        """
        path = 'item'
        return self.getResource(path, itemId)

    def listItem(self, folderId, text=None):
        """
        Retrieves a item set from this folder ID.

        :param folderId: the parent folder's ID.
        :param text: query for full text search of items, optional.
        """
        path = 'item'
        params = {
            'folderId': folderId,
        }
        if text is not None:
            params['text'] = text
        return self.listResource(path, params)

    def createFolder(self, parentId, parentType, name, description):
        """
        Creates and returns an folder

        :param parentType: One of ('folder', 'user', 'collection')
        """
        path = 'folder'
        params = {
            'parentId': parentId,
            'parentType': parentType,
            'name': name,
            'description': description
        }
        return self.createResource(path, params)

    def getFolder(self, folderId):
        """
        Retrieves a folder by its ID.

        :param folderId: A string containing the ID of the folder to retrieve
            from Girder.
        """
        path = 'folder'
        return self.getResource(path, folderId)

    def listFolder(self, parentId, parentFolderType='folder'):
        """
        Retrieves a folder set from this parent ID.

        :param parentId: The parent's ID.
        :param parentFolderType: One of ('folder', 'user', 'collection').
        """
        path = 'folder'
        params = {
            'parentId': parentId,
            'parentType': parentFolderType
        }
        return self.listResource(path, params)

    def getFolderAccess(self, folderId):
        """
        Retrieves a folder's access by its ID.

        :param folderId: A string containing the ID of the folder to retrieve
            access for from Girder.
        """
        path = 'folder'
        property = 'access'
        return self.getResource(path, folderId, property)

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

    def _file_chunker(self, filepath, filesize=None):
        """
        Generator returning chunks of a file in MAX_CHUNK_SIZE increments.

        :param filepath: path to file on disk.
        :param filesize: size of file on disk if known.
        """
        if filesize is None:
            filesize = os.path.getsize(filepath)
        startbyte = 0
        next_chunk_size = min(self.MAX_CHUNK_SIZE, filesize - startbyte)
        with open(filepath, 'rb') as fd:
            while next_chunk_size > 0:
                chunk = fd.read(next_chunk_size)
                yield (chunk, startbyte)
                startbyte = startbyte + next_chunk_size
                next_chunk_size = min(self.MAX_CHUNK_SIZE,
                                      filesize - startbyte)

    def _sha512_hasher(self, filepath):
        """
        Returns sha512 hash of passed in file.

        :param filepath: path to file on disk.
        """
        hasher = hashlib.sha512()
        for chunk, _ in self._file_chunker(filepath):
            hasher.update(chunk)
        return hasher.hexdigest()

    def isFileCurrent(self, itemId, filename, filepath):
        """
        Tests whether the passed in filepath exists in the item with itemId,
        with a name of filename, and with the same contents as the file at
        filepath.  Returns a tuple (file_id, current) where
        file_id = id of the file with that filename under the item, or
        None if no such file exists under the item.
        current = boolean if the file with that filename under the item
        has the same contents as the file at filepath.

        :param itemId: ID of parent item for file.
        :param filename: name of file to look for under the parent item.
        :param filepath: path to file on disk.
        """
        path = 'item/' + itemId + '/files'
        item_files = self.get(path)
        for item_file in item_files:
            if filename == item_file['name']:
                file_id = item_file['_id']
                if 'sha512' in item_file:
                    if item_file['sha512'] == self._sha512_hasher(filepath):
                        return (file_id, True)
                    else:
                        return (file_id, False)
                else:
                    # Some assetstores don't support sha512
                    # so we'll need to upload anyway
                    return (file_id, False)
        # Some files may already be stored under a different name, we'll need
        # to upload anyway in this case also.
        return (None, False)

    def uploadFileToItem(self, itemId, filepath):
        """
        Uploads a file to an item, in chunks.
        If ((the file already exists in the item with the same name and sha512)
        or (if the file has 0 bytes), no uploading will be performed.

        :param itemId: ID of parent item for file.
        :param filepath: path to file on disk.
        """
        filename = os.path.basename(filepath)
        filepath = os.path.abspath(filepath)
        filesize = os.path.getsize(filepath)

        if filesize == 0:
            return

        # Check if the file already exists by name and sha512 in the file.
        file_id, current = self.isFileCurrent(itemId, filename, filepath)
        if file_id is not None and current:
            print 'File %s already exists in parent Item' % filename
            return

        if file_id is not None and not current:
            print 'File %s exists in Item, but with stale contents' % filename
            path = 'file/' + file_id + '/contents'
            params = {
                'size': filesize
            }
            obj = self.put(path, params)
            if '_id' in obj:
                uploadId = obj['_id']
            else:
                raise Exception(
                    'After creating an upload token for replacing file '
                    'contents, expected an object with an id. Got instead: ' +
                    json.dumps(obj))
        else:
            params = {
                'parentType': 'item',
                'parentId': itemId,
                'name': filename,
                'size': filesize
            }
            obj = self.post('file', params)
            if '_id' in obj:
                uploadId = obj['_id']
            else:
                raise Exception(
                    'After creating an upload token for a new file, expected '
                    'an object with an id. Got instead: ' + json.dumps(obj))

        for chunk, startbyte in self._file_chunker(filepath, filesize):
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
                raise Exception('After uploading a file chunk, did'
                                ' not receive object with _id. Got instead: ' +
                                json.dumps(obj))

    def addMetadataToItem(self, itemId, metadata):
        """
        Takes an item ID and a dictionary containing the metadata

        :param itemId: ID of the item to set metadata on.
        :param metadata: dictionary of metadata to set on item.
        """
        path = 'item/' + itemId + '/metadata'
        obj = self.put(path, data=json.dumps(metadata))
        return obj

    def addMetadataToFolder(self, folderId, metadata):
        """
        Takes an folder ID and a dictionary containing the metadata

        :param folderId: ID of the folder to set metadata on.
        :param metadata: dictionary of metadata to set on folder.
        """
        path = 'folder/' + folderId + '/metadata'
        obj = self.put(path, data=json.dumps(metadata))
        return obj

    def _transformFilename(self, name):
        """
        Sanitize the filename a bit.
        """
        if name in ('.', '..'):
            name = '_' + name
        name = name.replace(os.path.sep, '_')
        if os.path.altsep:
            name = name.replace(os.path.altsep, '_')
        return _safeNameRegex.sub('_', name)

    def downloadFile(self, fileId, path):
        """
        Download a file to the given local path.

        :param fileId: The ID of the Girder file to download.
        :param path: The local path to write the file to.
        """
        with open(path, 'wb') as fd:
            req = requests.get('%s/file/%s/download' % (self.urlBase, fileId),
                               headers={'Girder-Token': self.token})
            for chunk in req.iter_content(chunk_size=65536):
                fd.write(chunk)

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
                'limit': 50,
                'offset': offset
            })

            if first:
                if len(files) == 1 and files[0]['name'] == name:
                    self.downloadFile(
                        files[0]['_id'],
                        os.path.join(dest, self._transformFilename(name)))
                    break
                else:
                    dest = os.path.join(dest, self._transformFilename(name))
                    _safeMakedirs(dest)

            for file in files:
                self.downloadFile(
                    file['_id'],
                    os.path.join(dest, self._transformFilename(file['name'])))

            first = False
            offset += len(files)
            if len(files) < 50:
                break

    def downloadFolderRecursive(self, folderId, dest):
        """
        Download a folder recursively from Girder into a local directory.

        :param folderId: Id of the Girder folder to download.
        :param dest: The local download destination.
        """
        offset = 0

        while True:
            folders = self.get('folder', parameters={
                'limit': 50,
                'offset': offset,
                'parentType': 'folder',
                'parentId': folderId
            })

            for folder in folders:
                local = os.path.join(
                    dest, self._transformFilename(folder['name']))
                _safeMakedirs(local)

                self.downloadFolderRecursive(folder['_id'], local)

            offset += len(folders)
            if len(folders) < 50:
                break

        offset = 0

        while True:
            items = self.get('item', parameters={
                'folderId': folderId,
                'limit': 50,
                'offset': offset
            })

            for item in items:
                self.downloadItem(item['_id'], dest, name=item['name'])

            offset += len(items)
            if len(items) < 50:
                break

    def inheritAccessControlRecursive(self, ancestorFolderId, access=None,
                                      public=None):
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
                'limit': 50,
                'offset': offset,
                'parentType': 'folder',
                'parentId': ancestorFolderId
            })

            for folder in folders:
                self.inheritAccessControlRecursive(folder['_id'], access,
                                                   public)

            offset += len(folders)
            if len(folders) < 50:
                break
