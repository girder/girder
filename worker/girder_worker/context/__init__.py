from . import girder_context, nongirder_context


def get_context():
    try:
        import cherrypy
        if cherrypy.request.app is None:
            return nongirder_context
        else:
            return girder_context
    except ImportError:
        return nongirder_context
