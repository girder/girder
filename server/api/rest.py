import cherrypy
import datetime
import importlib
import json
import sys
import traceback

from models import AccessException
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

class Resource():
    exposed = True

    def __init__(self):
        """
        If the subclass requests models to be set with getRequiredModels,
        this will instantiate them. The user model is always loaded, as it
        is needed by this base class.
        """
        modelList = self.getRequiredModels()
        assert type(modelList) is list
        modelList[:] = list(set(modelList + ['user']))

        for model in modelList:
            if type(model) is str:
                # Default transform is e.g. 'user' -> 'User()'
                modelName = model
                className = model[0].upper() + model[1:]
            elif type(model) is tuple:
                # Custom class name e.g. 'some_thing' -> 'SomeThing()'
                modelName = model[0]
                className = model[1]
            else:
                raise Exception('Required models should be strings or tuples.')

            try:
                imported = importlib.import_module('models.%s' % modelName)
            except ImportError:
                raise Exception('Could not load model module "%s"' % modelName)

            try:
                constructor = getattr(imported, className)
            except AttributeError:
                raise Exception('Incorrect model class name "%s" for model "%s"' %
                                (className, modelName))
            setattr(self, '%sModel' % modelName, constructor())

    def getRequiredModels(self):
        """
        Override this method in the subclass and have it return a list of models to
        instantiate on the class. For example, if the returned list contains 'user',
        it will setup self.userModel appropriately. The returned values in the list should
        either be strings (e.g. 'user') or if necessary due to naming conventions, a 2-tuple
        of the form ('model_module_name', 'ModelClassName').
        """
        return []

    def filterDocument(self, doc, allow=[]):
        """
        This method will filter the given document to make it suitable to output to the user.
        @param doc The document to filter
        @param allow The whitelist of fields to allow in the output document.
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
        Returns the current user from the session or long-term cookie token.
        Will return the user document from the database, or None if the user
        is not logged in.
        """
        # First attempt to use the session
        user = cherrypy.session.get('user', None)
        if user is not None:
            return user

        # Next try long-term token
        cookie = cherrypy.request.cookie
        if cookie.has_key('auth_token'):
            info = json.loads(cookie['auth_token'].value)
            cursor = self.userModel.find(query={
                'token' : info['token'].encode('ascii', 'ignore'),
                '_id' : ObjectId(info['_id']),
                'tokenExpires' : {'$gt' : datetime.datetime.now()}
                }, limit=1)
            if cursor.count() == 0: # bad or expired cookie
                return None
            else:
                return cursor.next()
        else: # user is not logged in
            return None

    def getObjectById(self, model, id):
        """
        This convenience method should be used to load a single
        instance of a model that is indexed by the default ObjectId type.
        @param model The model object to load from.
        @param id The id of the object.
        """
        print id
        try:
            obj = model.load(id=id, objectId=type(id) is not ObjectId)
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
