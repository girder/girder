import cherrypy
import six

from girder.api.rest import Resource


def _walk_tree(node, path=[]):
    route_map = {}
    for k, v in six.iteritems(vars(node)):
        if isinstance(v, Resource):
            full_path = list(path)
            full_path.append(k)
            route_map[v] = full_path
            path = []

        if hasattr(v, 'exposed'):
            new_path = list(path)
            new_path.append(k)
            route_map.update(_walk_tree(v, new_path))

    return route_map


def _api_route_map():
    '''
    Returns a map of girder.api.rest.Resource to paths.

    The function walks the tree starting at /api and follows any branch attribute
    that has an 'exposed' attribute. Then a Resource is found the path to the
    resource is added to the map.

    This map can be used to lookup where a resource has been mounted.
    '''
    api = cherrypy.tree.apps['/api']

    return _walk_tree(api.root.v1)
