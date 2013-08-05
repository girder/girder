import cherrypy
import json
import sys
import traceback

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

    def requireParams(self, required, provided):
        """
        Pass a list of required parameters.
        """
        for param in required:
            if not provided.has_key(param):
                raise RestException("Parameter '%s' is required." % param)

    def getObjectById(self, model, id):
        """
        This convenience method should be used to load a single
        instance of a model that is indexed by the default ObjectId type.
        @param model The model object to load from.
        @param id The id of the object.
        """
        try:
            obj = model.load(id, type(id) is not ObjectId)
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
                cherrypy.response.status = e.code
                val = {'message' : e.message}
                if e.extra is not None:
                    val['extra'] = e.extra
            except:
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
