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
import glob
import hashlib
import json
import os
import re
import requests
import six


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
            raise  # pragma: no cover


class AuthenticationError(RuntimeError):
    pass


class IncorrectUploadLengthError(RuntimeError):
    def __init__(self, message, upload=None):
        RuntimeError.__init__(self, message)
        self.upload = upload


class HttpError(Exception):
    """
    Raised if the server returns an error status code from a request.
    """
    def __init__(self, status, text, url, method):
        Exception.__init__(self, 'HTTP error {}: {} {}'.format(
                           status, method, url))
        self.status = status
        self.responseText = text
        self.url = url
        self.method = method


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

    def __init__(self, host=None, port=None, apiRoot=None, scheme=None,
                 dryrun=False, blacklist=None):
        """
        Construct a new GirderClient object, given a host name and port number,
        as well as a username and password which will be used in all requests
        (HTTP Basic Auth).

        :param host: A string containing the host name where Girder is running,
            the default value is 'localhost'
        :param port: The port number on which to connect to Girder,
            the default value is 80 for http: and 443 for https:
        :param apiRoot: The path on the server corresponding to the root of the
            Girder REST API. If None is passed, assumes '/api/v1'.
        :param scheme: A string containing the scheme for the Girder host,
            the default value is 'http'; if you pass 'https' you likely want
            to pass 443 for the port
        """
        if apiRoot is None:
            apiRoot = '/api/v1'

        if port is None:
            if scheme == 'https':
                port = 443
            else:
                port = 80

        self.scheme = scheme or 'http'
        self.host = host or 'localhost'
        self.port = port

        self.urlBase = self.scheme + '://' + self.host + ':' + str(self.port) \
            + apiRoot

        if self.urlBase[-1] != '/':
            self.urlBase += '/'

        self.token = ''
        self.dryrun = dryrun
        self.blacklist = blacklist
        if self.blacklist is None:
            self.blacklist = []
        self.folder_upload_callbacks = []
        self.item_upload_callbacks = []

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
                username = six.moves.input('Login or email: ')
            password = getpass.getpass('Password for %s: ' % username)

        if username is None or password is None:
            raise Exception('A user name and password are required')

        url = self.urlBase + 'user/authentication'
        authResponse = requests.get(url, auth=(username, password))

        if authResponse.status_code == 404:
            raise HttpError(404, authResponse.text, url, "GET")

        resp = authResponse.json()
        if 'authToken' not in resp:
            raise AuthenticationError()

        self.token = resp['authToken']['token']

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
        # TODO handle 300-level status (follow redirect?)
        else:
            raise HttpError(
                status=result.status_code, url=result.url, method=method,
                text=result.text)

    def get(self, path, parameters=None):
        return self.sendRestRequest('GET', path, parameters)

    def post(self, path, parameters=None, files=None):
        return self.sendRestRequest('POST', path, parameters, files=files)

    def put(self, path, parameters=None, data=None):
        return self.sendRestRequest('PUT', path, parameters, data=data)

    def delete(self, path, parameters=None):
        return self.sendRestRequest('DELETE', path, parameters)

    def createResource(self, path, params):
        """
        Creates and returns a resource.
        """
        return self.post(path, params)

    def getResource(self, path, id=None, property=None):
        """
        Loads a resource or resource property of property is not None
        by id or None if no resource is returned.
        """
        route = path
        if id is not None:
            route += '/%s' % id
        if property is not None:
            route += '/%s' % property

        return self.get(route)

    def listResource(self, path, params):
        """
        search for a list of resources based on params.
        """
        return self.get(path, params)

    def createItem(self, parentFolderId, name, description):
        """
        Creates and returns an item.
        """
        params = {
            'folderId': parentFolderId,
            'name': name,
            'description': description
        }
        return self.createResource('item', params)

    def getItem(self, itemId):
        """
        Retrieves a item by its ID.

        :param itemId: A string containing the ID of the item to retrieve from
            Girder.
        """
        return self.getResource('item', itemId)

    def listItem(self, folderId, text=None, name=None):
        """
        Retrieves a item set from this folder ID.

        :param folderId: the parent folder's ID.
        :param text: query for full text search of items.
        :param name: query for exact name match of items.
        """
        params = {
            'folderId': folderId,
        }
        if text:
            params['text'] = text
        if name:
            params['name'] = name

        return self.listResource('item', params)

    def createFolder(self, parentId, name, description='', parentType='folder'):
        """
        Creates and returns a folder

        :param parentType: One of ('folder', 'user', 'collection')
        """
        params = {
            'parentId': parentId,
            'parentType': parentType,
            'name': name,
            'description': description
        }
        return self.createResource('folder', params)

    def getFolder(self, folderId):
        """
        Retrieves a folder by its ID.

        :param folderId: A string containing the ID of the folder to retrieve
            from Girder.
        """
        return self.getResource('folder', folderId)

    def listFolder(self, parentId, parentFolderType='folder', name=None):
        """
        Retrieves a folder set from this parent ID.

        :param parentId: The parent's ID.
        :param parentFolderType: One of ('folder', 'user', 'collection').
        """
        params = {
            'parentId': parentId,
            'parentType': parentFolderType
        }

        if name:
            params['name'] = name

        return self.listResource('folder', params)

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
            print('File %s already exists in parent Item' % filename)
            return

        if file_id is not None and not current:
            print('File %s exists in Item, but with stale contents' % filename)
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

    def uploadFile(self, parentId, stream, name, size, parentType='item',
                   progressCallback=None):
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
        :returns: The file that was created on the server.
        """
        obj = self.post('file', {
            'parentType': parentType,
            'parentId': parentId,
            'name': name,
            'size': size
        })
        if '_id' in obj:
            uploadId = obj['_id']
        else:
            raise Exception(
                'After creating an upload token for a new file, expected '
                'an object with an id. Got instead: ' + json.dumps(obj))

        offset = 0
        while True:
            data = stream.read(self.MAX_CHUNK_SIZE)

            if not data:
                break

            params = {
                'offset': offset,
                'uploadId': uploadId
            }
            files = {
                'chunk': data
            }
            obj = self.post('file/chunk', parameters=params, files=files)
            offset += len(data)

            if '_id' not in obj:
                raise Exception('After uploading a file chunk, did'
                                ' not receive object with _id. Got instead: ' +
                                json.dumps(obj))

            if callable(progressCallback):
                progressCallback({
                    'current': offset,
                    'total': size
                })

        if offset != size:
            self.delete('file/upload/' + uploadId)
            raise IncorrectUploadLengthError(
                'Expected upload to be %d bytes, but received %d.' % (
                    size, offset), upload=obj)

        return obj

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
        _safeMakedirs(os.path.dirname(path))

        with open(path, 'wb') as fd:
            req = requests.get('%sfile/%s/download' % (self.urlBase, fileId),
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

    def add_folder_upload_callback(self, callback):
        """Saves a passed in callback function that will be called after each
        folder has completed.  Multiple callback functions can be added, they
        will be called in the order they were added by calling this function.
        Callback functions will be called after a folder in Girder is created
        and all subfolders and items for that folder have completed uploading.
        Callback functions should take two parameters:
        - the folder in girder
        - the full path to the local folder

        :param callback: callback function to be called.

        """
        self.folder_upload_callbacks.append(callback)

    def add_item_upload_callback(self, callback):
        """Saves a passed in callback function that will be called after each
        item has completed.  Multiple callback functions can be added, they
        will be called in the order they were added by calling this function.
        Callback functions will be called after an item in Girder is created
        and all files for that item have been uploaded.  Callback functions
        should take two parameters:
        - the item in girder
        - the full path to the local folder or file comprising the item

        :param callback: callback function to be called.

        """
        self.item_upload_callbacks.append(callback)

    def load_or_create_folder(self, folder_name, parent_id, parent_type):
        """Returns a folder in Girder with the given name under the given
        parent. If none exists yet, it will create it and return it.

        :param folder_name: the name of the folder to look up.
        :param parent_id: id of parent in Girder
        :param parent_type: one of (collection, folder, user)
        :returns: The folder that was found or created.
        """
        children = self.listFolder(parent_id, parent_type, name=folder_name)

        if len(children):
            return children[0]
        else:
            return self.createFolder(
                parent_id, folder_name, parentType=parent_type)

    def _has_only_files(self, local_folder):
        """Returns whether a folder has only files. This will be false if the
        folder contains any subdirectories.
        :param local_folder: full path to the local folder
        """
        return not any(os.path.isdir(os.path.join(local_folder, entry))
                       for entry in os.listdir(local_folder))

    def load_or_create_item(self, name, parent_folder_id, reuse_existing=True):
        """Create an item with the given name in the given parent folder.

        :param name: The name of the item to load or create.
        :param parent_folder_id: id of parent folder in Girder
        :param reuse_existing: boolean indicating whether to load an existing
            item of the same name in the same location, or create a new one.
        """
        item = None
        if reuse_existing:
            children = self.listItem(parent_folder_id, name=name)
            if len(children):
                item = children[0]

        if item is None:
            item = self.createItem(parent_folder_id, name, description='')

        return item

    def _upload_file_to_item(self, local_file, parent_item_id, file_path):
        """Helper function to upload a file to an item
        :param local_file: name of local file to upload
        :param parent_item_id: id of parent item in Girder to add file to
        :param file_path: full path to the file
        """
        self.uploadFileToItem(parent_item_id, file_path)

    def _upload_as_item(self, local_file, parent_folder_id, file_path,
                        reuse_existing=False):
        """Function for doing an upload of a file as an item.
        :param local_file: name of local file to upload
        :param parent_folder_id: id of parent folder in Girder
        :param file_path: full path to the file
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        print('Uploading Item from %s' % local_file)
        if not self.dryrun:
            current_item = self.load_or_create_item(
                os.path.basename(local_file), parent_folder_id, reuse_existing)
            self._upload_file_to_item(
                local_file, current_item['_id'], file_path)

            for callback in self.item_upload_callbacks:
                callback(current_item, file_path)

    def _upload_folder_as_item(self, local_folder, parent_folder_id,
                               reuse_existing=False):
        """Take a folder and use its base name as the name of a new item. Then,
        upload its containing files into the new item as bitstreams.
        :param local_folder: The path to the folder to be uploaded.
        :param parent_folder_id: Id of the destination folder for the new item.
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        print('Creating Item from folder %s' % local_folder)
        if not self.dryrun:
            item = self.load_or_create_item(
                os.path.basename(local_folder), parent_folder_id,
                reuse_existing)

        subdircontents = sorted(os.listdir(local_folder))
        # for each file in the subdir, add it to the item
        filecount = len(subdircontents)
        for (ind, current_file) in enumerate(subdircontents):
            filepath = os.path.join(local_folder, current_file)
            if current_file in self.blacklist:
                if self.dryrun:
                    print("Ignoring file %s as blacklisted" % current_file)
                continue
            print('Adding file %s, (%d of %d) to Item' % (current_file,
                                                          ind + 1, filecount))

            if not self.dryrun:
                self._upload_file_to_item(current_file, item['_id'], filepath)

        if not self.dryrun:
            for callback in self.item_upload_callbacks:
                callback(item, local_folder)

    def _upload_folder_recursive(self, local_folder, parent_id, parent_type,
                                 leaf_folders_as_items=False,
                                 reuse_existing=False):
        """Function to recursively upload a folder and all of its descendants.
        :param local_folder: full path to local folder to be uploaded
        :param parent_id: id of parent in Girder,
            where new folder will be added
        :param parent_type: one of (collection, folder, user)
        :param leaf_folders_as_items: whether leaf folders should have all
        files uploaded as single items
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        if leaf_folders_as_items and self._has_only_files(local_folder):
            if parent_type != 'folder':
                raise Exception(
                    ('Attempting to upload a folder as an item under a %s. '
                        % parent_type) + 'Items can only be added to folders.')
            else:
                self._upload_folder_as_item(local_folder, parent_id,
                                            reuse_existing)
        else:
            filename = os.path.basename(local_folder)
            if filename in self.blacklist:
                if self.dryrun:
                    print("Ignoring file %s as it is blacklisted" % filename)
                return

            print('Creating Folder from %s' % local_folder)
            if self.dryrun:
                # create a dryrun placeholder
                folder = {'_id': 'dryrun'}
            else:
                folder = self.load_or_create_folder(
                    os.path.basename(local_folder), parent_id, parent_type)

            for entry in sorted(os.listdir(local_folder)):
                if entry in self.blacklist:
                    if self.dryrun:
                        print("Ignoring file %s as it is blacklisted" % entry)
                    continue
                full_entry = os.path.join(local_folder, entry)
                if os.path.islink(full_entry):
                    # os.walk skips symlinks by default
                    print("Skipping file %s as it is a symlink" % entry)
                    continue
                elif os.path.isdir(full_entry):
                    # At this point we should have an actual folder, so can
                    # pass that as the parent_type
                    self._upload_folder_recursive(
                        full_entry, folder['_id'], 'folder',
                        leaf_folders_as_items, reuse_existing)
                else:
                    self._upload_as_item(
                        entry, folder['_id'], full_entry, reuse_existing)

            if not self.dryrun:
                for callback in self.folder_upload_callbacks:
                    callback(folder, local_folder)

    def upload(self, file_pattern, parent_id, parent_type='folder',
               leaf_folders_as_items=False, reuse_existing=False):
        """Upload a pattern of files.

        This will recursively walk down every tree in the file pattern to
        create a hierarchy on the server under the parent_id.

        :param file_pattern: a glob pattern for files that will be uploaded,
            recursively copying any file folder structures.
        :param parent_id: id of the parent in girder.
        :param parent_type: one of (collection,folder,user), default of folder.
        :param leaf_folders_as_items: bool whether leaf folders should have all
            files uploaded as single items.
        :param reuse_existing: bool whether to accept an existing item of
            the same name in the same location, or create a new one instead.
        """
        empty = True
        for current_file in glob.iglob(file_pattern):
            empty = False
            current_file = os.path.normpath(current_file)
            filename = os.path.basename(current_file)
            if filename in self.blacklist:
                if self.dryrun:
                    print("Ignoring file %s as it is blacklisted" % filename)
                continue
            if os.path.isfile(current_file):
                if parent_type != 'folder':
                    raise Exception(('Attempting to upload an item under a %s.'
                                    % parent_type) +
                                    ' Items can only be added to folders.')
                else:
                    self._upload_as_item(
                        os.path.basename(current_file), parent_id,
                        current_file, reuse_existing)
            else:
                self._upload_folder_recursive(
                    current_file, parent_id, parent_type,
                    leaf_folders_as_items, reuse_existing)
        if empty:
            print('No matching files: ' + file_pattern)
