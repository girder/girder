import json
import requests
import os


class GirderClient(object):
    """
    A class for interacting with the Girder RESTful API. Some simple examples of
    how to use this class follow:

    client = GirderClient('myhost', 9000)
    client.authenticate('myname', 'mypass')

    itemId = client.createitem(folderId, 'some item name', 'and description')
    client.addMetadataToItem(itemId, {'metadatakey': 'metadatavalue'})
    client.uploadFileToItem(itemId, '/full/path/to/your/file.txt')

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

    #-------------------------------------------------------------------------
    # Constructor
    #-------------------------------------------------------------------------
    def __init__(self, host="localhost", port=8080):
        """
        Construct a new GirderClient object, given a host name and port number,
        as well as a username and password which will be used in all requests
        (HTTP Basic Auth).

            host: A string containing the host name where Girder is running, the
            default value is 'localhost'

            port: A number containing the port on which to connect to Girder,
            the default value is 8080
        """
        self.host = host
        self.port = port

        self.urlBase = 'http://' + self.host + ':' + str(self.port) + '/api/v1/'

        self.token = None

    #-------------------------------------------------------------------------
    # Construct URL and send request
    #-------------------------------------------------------------------------
    def authenticate(self, username, password):
        """
        Authenticate to Girder, storing the token that comes back to be used in
        future requests.

            username: A string containing the username to use in basic
            authentication

            password: A string containing the password to use in basic
            authentication
        """
        if username is None or password is None:
            raise Exception('A user name and password are required')

        authResponse = requests.get(self.urlBase + 'user/authentication',
                                    auth=(username, password))
        self.token = authResponse.json()['authToken']['token']

    #-------------------------------------------------------------------------
    # Construct URL and send request
    #-------------------------------------------------------------------------
    def sendRestRequest(self, method, path, parameters=None):
        """
        This method looks up the appropriate method, constructs a request URL
        from the base URL, path, and parameters, and then sends the request. If
        the method is unknown or if the path is not found, an exception is
        raised, otherwise a JSON object is returned with the Girder response.

        This is a convenience method to use when making basic requests that do
        not involve multipart file data which might need to be specially encoded
        or handled differently.

            method: One of 'GET', 'POST', 'PUT', or 'DELETE'

            path: A string containing the path elements for this request. Note
            that the path string should not begin or end with the path
            separator, '/'.

            parameters: A dictionary mapping strings to strings, to be used as
            the key/value pairs in the request parameters
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
        result = f(url, params=parameters)

        # If success, return the json object.  Otherwise throw an exception.
        if result.status_code == 200 or result.status_code == 403:
            return result.json()
        else:
            print 'Showing result before raising exception:'
            print result.text
            raise Exception('Request: ' + result.url + ', return code: ' +
                            str(result.status_code))

    #-------------------------------------------------------------------------
    # A convenience method for creating a new item
    #-------------------------------------------------------------------------
    def createItem(self, parentFolderId, name, description):
        """
        Creates an item and returns the new item ID
        """
        path = 'item'
        params = {
            'folderId': parentFolderId,
            'name': name,
            'description': description
        }
        obj = self.sendRestRequest('POST', path, params)
        if '_id' in obj:
            return obj['_id']
        else:
            raise Exception('Error, expected the returned item object to have'
                            ' an "_id" field')

    #-------------------------------------------------------------------------
    # A convenience method for creating a new folder
    #-------------------------------------------------------------------------
    def createFolder(self, parentId, parentType, name, description):
        path = 'folder'
        params = {
            'parentId': parentId,
            'parentType': parentType,
            'name': name,
            'description': description
        }
        obj = self.sendRestRequest('POST', path, params)
        if '_id' in obj:
            return obj['_id']
        else:
            raise Exception('Error, expected to get a folder back with an "_id"'
                            ' field')

    #-------------------------------------------------------------------------
    # A convenience method for adding metadata to an existing item
    #-------------------------------------------------------------------------
    def addMetadataToItem(self, itemId, metadata):
        """
        Takes an item ID and a JSON object containing the metadata
        """
        path = 'item/' + itemId + '/metadata'
        obj = requests.put(self.urlBase + path, params={'token': self.token},
                           data=json.dumps(metadata))
        return obj.json()

    #-------------------------------------------------------------------------
    # A convenience method for uploading a file to an existing item
    #-------------------------------------------------------------------------
    def uploadFileToItem(self, itemId, filepath):
        """
        Uploads a file to an item. Currently only supports uploading in a
        single chunk, so files larger than 64 MB will raise an exception.
        """
        with open(filepath, 'rb') as fd:
            data = fd.read()

        datalen = len(data)

        if datalen > self.MAX_CHUNK_SIZE:
            raise Exception('Currently sending file larger than ' +
                            str(self.MAX_CHUNK_SIZE) + ' bytes is not'
                            ' supported. Your file is ' + str(datalen) +
                            ' bytes.')

        filename = os.path.basename(filepath)
        params = {
            'parentType': 'item',
            'parentId': itemId,
            'name': filename,
            'size': datalen
        }

        obj = self.sendRestRequest('POST', 'file', params)

        if '_id' in obj:
            uploadId = obj['_id']
        else:
            raise Exception('After creating an upload token, expected an object'
                            'with an id. Got instead: ' + json.dumps(obj))

        parameters = {
            'token': self.token,
            'offset': '0',
            'uploadId': uploadId
        }

        filedata = {
            'chunk': data
        }

        upResult = requests.post(self.urlBase + 'file/chunk', params=parameters,
                                 files=filedata)
        obj = upResult.json()

        if '_id' in obj:
            return obj['_id']
        else:
            raise Exception('After uploading file as single chunk, did'
                            ' not receive object with _id. Got instead: ' +
                            json.dumps(obj))

    #-------------------------------------------------------------------------
    # A convenience method for getting an item by id
    #-------------------------------------------------------------------------
    def getItem(self, itemId):
        """
        Retrieves an item by its ID.

            itemId: A string containing the ID of the item to retrieve from
            Girder
        """
        path = 'item/' + itemId
        return self.sendRestRequest('GET', path)
