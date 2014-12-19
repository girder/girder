import json
import requests
import os
import os.path
import hashlib


class AuthenticationError(RuntimeError):
    pass


class GirderClient(object):
    """
    A class for interacting with the Girder RESTful API. Some simple examples of
    how to use this class follow:

    .. code-block:: python

        client = GirderClient('myhost', 9000)
        client.authenticate('myname', 'mypass')

        itemId = client.createitem(folderId, 'an item name', 'a description')
        client.addMetadataToItem(itemId, {'metadatakey': 'metadatavalue'})
        client.uploadFileToItem(itemId, 'path/to/your/file.txt')

        r1 = client.getItem('52e935037bee0436e29a7130')
        r2 = client.sendRestRequest('GET', 'item',
            {'folderId': '52e97b2b7bee0436e29a7142', 'sortdir': '-1' })
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

    def __init__(self, host="localhost", port=8080):
        """
        Construct a new GirderClient object, given a host name and port number,
        as well as a username and password which will be used in all requests
        (HTTP Basic Auth).

        :param host: A string containing the host name where Girder is running,
            the default value is 'localhost'

        :param port: A number containing the port on which to connect to Girder,
            the default value is 8080
        """
        self.host = host
        self.port = port

        self.urlBase = 'http://' + self.host + ':' + str(self.port) + '/api/v1/'

        self.token = None

    def authenticate(self, username, password):
        """
        Authenticate to Girder, storing the token that comes back to be used in
        future requests.

        :param username: A string containing the username to use in basic
            authentication
        :param password: A string containing the password to use in basic
            authentication
        """
        if username is None or password is None:
            raise Exception('A user name and password are required')

        authResponse = requests.get(self.urlBase + 'user/authentication',
                                    auth=(username, password)).json()

        if 'authToken' not in authResponse:
            raise AuthenticationError()

        self.token = authResponse['authToken']['token']

    def sendRestRequest(self, method, path, parameters=None, data=None, files=None):
        """
        This method looks up the appropriate method, constructs a request URL
        from the base URL, path, and parameters, and then sends the request. If
        the method is unknown or if the path is not found, an exception is
        raised, otherwise a JSON object is returned with the Girder response.

        This is a convenience method to use when making basic requests that do
        not involve multipart file data which might need to be specially encoded
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

        # Add the authentication token to any parameters we got
        parameters.update({'token': self.token})

        # Make the request, passing parameters and authentication info
        result = f(url, params=parameters, data=data, files=files)

        # If success, return the json object.  Otherwise throw an exception.
        if result.status_code == 200 or result.status_code == 403:
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

    def getResource(self, path, id):
        """
        Loads a resource by id or None if no resource is returned.
        """
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

    def uploadFileToItem(self, itemId, filepath):
        """
        Uploads a file to an item, in chunks.
        If ((the file already exists in the item with the same name and sha512)
        or (if the file has 0 bytes), no uploading will be performed.
        """
        filename = os.path.basename(filepath)
        filepath = os.path.abspath(filepath)
        filesize = os.path.getsize(filepath)

        if filesize == 0:
            return

        def file_chunker(filepath):
            startbyte = 0
            next_chunk_size = min(self.MAX_CHUNK_SIZE, filesize - startbyte)
            with open(filepath, 'rb') as fd:
                while next_chunk_size > 0:
                    chunk = fd.read(next_chunk_size)
                    yield (chunk, startbyte)
                    startbyte = startbyte + next_chunk_size
                    next_chunk_size = min(self.MAX_CHUNK_SIZE, filesize - startbyte)

        def sha512_hasher(filepath):
            hasher = hashlib.sha512()
            for chunk, _ in file_chunker(filepath):
                hasher.update(chunk)
            return hasher.hexdigest()

        # Check if the file already exists by name and sha512 in the file.
        # Some assetstores don't support sha512, so we'll need to upload anyway
        # Some files may already be stored under a different name, we'll need
        # to upload anyway in this case also.
        file_id = None
        path = 'item/' + itemId + '/files'
        item_files = self.get(path)
        for item_file in item_files:
            if filename == item_file['name']:
                file_id = item_file['_id']
                if 'sha512' in item_file:
                    if item_file['sha512'] == sha512_hasher(filepath):
                        print 'File %s already exists in parent Item' % filename
                        return

        if file_id is not None:
            path = 'file/' + file_id + '/contents'
            params = {
                'size': filesize
            }
            obj = self.put(path, params)
            if '_id' in obj:
                uploadId = obj['_id']
            else:
                raise Exception('After creating an upload token for replacing file contents, expected an object'
                                'with an id. Got instead: ' + json.dumps(obj))
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
                raise Exception('After creating an upload token for a new file, expected an object'
                                'with an id. Got instead: ' + json.dumps(obj))

        for chunk, startbyte in file_chunker(filepath):
            parameters = {
                'token': self.token,
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
        """
        path = 'item/' + itemId + '/metadata'
        params = {
            'token': self.token,
        }
        obj = self.put(path, params, data=json.dumps(metadata))
        return obj

    def addMetadataToFolder(self, folderId, metadata):
        """
        Takes an folder ID and a dictionary containing the metadata
        """
        path = 'folder/' + folderId + '/metadata'
        params = {
            'token': self.token,
        }
        obj = self.put(path, params, data=json.dumps(metadata))
        return obj
