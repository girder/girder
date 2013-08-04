import cherrypy
import json

class RestException(Exception):
    def __init__(self, message, code=400):
        self.code = code
        Exception.__init__(self, message)

class Resource():
    exposed = True

    def requireParams(self, required, provided):
        """
        Pass a list of required parameters.
        """
        for param in required:
            if not provided.has_key(param):
                raise RestException('Parameter %s is required.' % param)

    @classmethod
    def endpoint(cls, fun):
        def wrapper(self, *args, **kwargs):
            try:
                val = fun(self, *args, **kwargs)
            except RestException as e:
                cherrypy.response.status = e.code
                val = {'message' : e.message}

            accepts = cherrypy.request.headers.elements('Accept')
            for accept in accepts:
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
