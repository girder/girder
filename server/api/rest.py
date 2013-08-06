import cherrypy
import datetime
import json
import sys
import traceback

from constants import AccessType
from models.model_base import AccessException, ModelImporter
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
        self.initialize()
        self.requireModels(['user', 'token'])

    def initialize(self):
        """
        Pure virtual method.
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
        Returns the current user from the long-term cookie token.
        :returns: The user document from the database, or None if the user
                  is not logged in or the cookie token is invalid or expired.
        """
        cookie = cherrypy.request.cookie
        if cookie.has_key('authToken'):
            info = json.loads(cookie['authToken'].value)
            try:
                userId = ObjectId(info['userId'])
                tokenId = info['token']
            except:
                return None

            user = self.userModel.load(userId)
            token = self.tokenModel.load(info['token'], AccessType.ADMIN,
                                         objectId=False, user=user)

            if token is None or token['expires'] < datetime.datetime.now():
                return None
            else:
                return user
        else: # user is not logged in
            return None

    def getObjectById(self, model, id, checkAccess=False, user=None, level=AccessType.READ):
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
        coerceId = type(id) is not ObjectId
        try:
            if checkAccess is True:
                obj = model.load(id=id, objectId=coerceId, user=user, level=level)
            else:
                obj = model.load(id=id, objectId=coerceId)
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
        exceptions in the REST endpoints, and also handles any unexpected exceptions
        using 500 status and including a useful traceback in those cases.
        """
        def wrapper(self, *args, **kwargs):
            try:
                val = fun(self, *args, **kwargs)
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
                cherrypy.response.headers['Content-Type'] = accept.value
                if accept.value == 'application/json':
                    break
                elif accept.value == 'text/html':
                    # Pretty-print and HTMLify the response for display in browser
                    resp = json.dumps(val, indent=4, sort_keys=True,
                                      separators=(',', ': '), default=str)
                    resp = resp.replace(' ', '&nbsp;').replace('\n', '<br />')
                    resp = '<div style="font-family: monospace">' + resp + '</div>'
                    return resp

            #Default behavior will just be normal JSON output
            return json.dumps(val, default=str)
        return wrapper
