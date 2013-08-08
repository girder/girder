import cherrypy
import datetime
import json
import sys
import traceback

from constants import AccessType
from models.model_base import AccessException
from utility.model_importer import ModelImporter
from bson.objectid import ObjectId, InvalidId

class RestException(Exception):
    """
    Throw a RestException in the case of any sort of
    incorrect request (i.e. user/client error). Permission failures
    should set a 403 code; almost all other validation errors
    should use status 400, which is the default.
    """
    def __init__(self, message, code=400, extra=None):
        self.code = code
        self.extra = extra

        Exception.__init__(self, message)

class Resource(ModelImporter):
    exposed = True

    def __init__(self):
        self._currentUser = None
        self._setupCurrentUser = False

        self.initialize()
        self.requireModels(['user', 'token'])

    def initialize(self):
        """
        Subclasses should implement this method.
        """
        pass

    def filterDocument(self, doc, allow=[]):
        """
        This method will filter the given document to make it suitable to output to the user.
        :param doc: The document to filter.
        :type doc: dict
        :param allow: The whitelist of fields to allow in the output document.
        :type allow: List of strings
        """
        out = {}
        for field in allow:
            if doc.has_key(field):
                out[field] = doc[field]

        return out

    def requireParams(self, required, provided):
        """
        Pass a list of required parameters.
        """
        for param in required:
            if not provided.has_key(param):
                raise RestException("Parameter '%s' is required." % param)

    def getCurrentUser(self):
        """
        Returns the current user from the long-term cookie token. This is a
        lazy getter that will only attempt to load from the cookie once per
        request, so subsequent calls this this function are inexpensive.
        :returns: The user document from the database, or None if the user
                  is not logged in or the cookie token is invalid or expired.
        """
        if self._setupCurrentUser:
            return self._currentUser

        self._setupCurrentUser = True
        cookie = cherrypy.request.cookie
        if cookie.has_key('authToken'):
            info = json.loads(cookie['authToken'].value)
            try:
                userId = ObjectId(info['userId'])
                tokenId = info['token']
            except:
                return None

            user = self.userModel.load(userId, force=True)
            token = self.tokenModel.load(info['token'], AccessType.ADMIN,
                                         objectId=False, user=user)

            if token is None or token['expires'] < datetime.datetime.now():
                return None
            else:
                self._currentUser = user
                return user
        else: # user is not logged in
            return None

    def getObjectById(self, model, id, checkAccess=False, user=None, level=AccessType.READ,
                      objectId=True):
        """
        This convenience method should be used to load a single
        instance of a model that is indexed by the default ObjectId type.
        :param model: The model to load from.
        :type model: Model
        :param id: The id of the object.
        :type id: string or ObjectId
        :param checkAccess: If this is an AccessControlledObject, set this to True.
        :type checkAccess: bool
        :param user: If checkAccess=True, set this to the current user.
        :type user: dict or None
        :param level: If the model is an AccessControlledModel, you must
                     pass the user requesting access
        """
        try:
            if checkAccess is True:
                obj = model.load(id=id, objectId=objectId, user=user, level=level)
            else:
                obj = model.load(id=id, objectId=objectId)
        except InvalidId:
            raise RestException('Invalid object ID format.')
        if obj is None:
            raise RestException('Resource not found.')
        return obj

    @classmethod
    def endpoint(cls, fun):
        """
        All REST endpoints should use this decorator. It converts the return value
        of the underlying method to the appropriate output format and sets the relevant
        response headers. It also handles RestExceptions, which are 400-level
        exceptions in the REST endpoints, AccessExceptions resulting from access denial,
        and also handles any unexpected exceptions using 500 status and including a useful
        traceback in those cases.
        """
        def wrapper(self, *args, **kwargs):
            try:
                # First, we should encode any unicode form data down into
                # UTF-8 so the actual REST classes are always dealing with
                # str types.
                params = {}
                for k, v in kwargs.iteritems():
                    if type(v) is unicode:
                        try:
                            params[k] = v.encode('utf-8')
                        except UnicodeEncodeError:
                            raise RestException('Unicode encoding failure.')
                    else:
                        params[k] = v

                val = fun(self, args, params)
            except RestException as e:
                # Handle all user-error exceptions from the rest layer
                cherrypy.response.status = e.code
                val = {'message' : e.message}
                if e.extra is not None:
                    val['extra'] = e.extra
            except AccessException as e:
                # Handle any permission exceptions
                cherrypy.response.status = 403
                val = {'message': e.message}
            except:
                # These are unexpected failures; send a 500 status and traceback
                (t, value, tb) = sys.exc_info()
                cherrypy.response.status = 500
                val = {'message' : '%s: %s' % (t.__name__, str(value)),
                       'trace' : traceback.extract_tb(tb)[1:]}

            accepts = cherrypy.request.headers.elements('Accept')
            for accept in accepts:
                if accept.value == 'application/json':
                    break
                elif accept.value == 'text/html':
                    # Pretty-print and HTMLify the response for display in browser
                    cherrypy.response.headers['Content-Type'] = 'text/html'
                    resp = json.dumps(val, indent=4, sort_keys=True,
                                      separators=(',', ': '), default=str)
                    resp = resp.replace(' ', '&nbsp;').replace('\n', '<br />')
                    resp = '<div style="font-family: monospace">' + resp + '</div>'
                    return resp

            # Default behavior will just be normal JSON output. Keep this
            # outside of the loop body in case no Accept header is passed.
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(val, default=str)
        return wrapper
