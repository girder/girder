import cherrypy
import six

from girder.api.rest import Resource


def _walkTree(node, path=()):
    routeMap = {}
    for k, v in six.iteritems(vars(node)):
        if isinstance(v, Resource):
            full_path = list(path)
            full_path.append(k)
            routeMap[v] = full_path

        if hasattr(v, 'exposed'):
            new_path = list(path)
            new_path.append(k)
            routeMap.update(_walkTree(v, new_path))

    return routeMap


def _apiRouteMap():
    """
    Returns a map of girder.api.rest.Resource to paths.

    The function walks the tree starting at /api and follows any branch attribute
    that has an 'exposed' attribute. Then a Resource is found the path to the
    resource is added to the map.

    This map can be used to lookup where a resource has been mounted.
    """
    api = cherrypy.tree.apps['/api']

    return _walkTree(api.root.v1)
