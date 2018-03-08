#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import collections
import functools
import six
from girder import logprint

models = collections.defaultdict(dict)
# routes is dict of dicts of dicts
# e.g. routes[resource][path][method]
routes = collections.defaultdict(
    functools.partial(collections.defaultdict, dict))


def _toRoutePath(resource, route):
    """
    Convert a base resource type and list of route components into a
    Swagger-compatible route path.
    """
    # Convert wildcard tokens from :foo form to {foo} form
    convRoute = [
        '{%s}' % token[1:] if token[0] == ':' else token
        for token in route
    ]

    prefix = ['']
    # If resource is a string then use this as the prefix to the route.
    if isinstance(resource, str):
        prefix.append(resource)

    path = '/'.join(prefix + convRoute)
    return path


def _toOperation(info, resource, handler):
    """
    Augment route info, returning a Swagger-compatible operation description.
    """
    operation = dict(info)
    operation['tags'] = [resource]

    # Operation Object spec:
    # Unique string used to identify the operation. The id MUST be unique among
    # all operations described in the API.
    if 'operationId' not in operation:
        operation['operationId'] = str(resource) + '_' + handler.__name__
    return operation


def addRouteDocs(resource, route, method, info, handler):
    """
    This is called for route handlers that have a description attr on them. It
    gathers the necessary information to build the swagger documentation, which
    is consumed by the docs.Describe endpoint.

    :param resource: The name of the resource, e.g. "item"
    :type resource: str
    :param route: The route to describe.
    :type route: tuple[str]
    :param method: The HTTP method for this route, e.g. "POST"
    :type method: str
    :param info: The information representing the API documentation, typically
                 from ``girder.api.describe.Description.asDict``.
    :type info: dict
    :param handler: The actual handler method for this route.
    :type handler: function
    """
    path = _toRoutePath(resource, route)

    operation = _toOperation(info, resource, handler)

    # Add the operation to the given route
    if method not in routes[resource][path]:
        routes[resource][path][method] = operation


def removeRouteDocs(resource, route, method, info, handler):
    """
    Remove documentation for a route handler.

    :param resource: The name of the resource, e.g. "item"
    :type resource: str
    :param route: The route to describe.
    :type route: tuple[str]
    :param method: The HTTP method for this route, e.g. "POST"
    :type method: str
    :param info: The information representing the API documentation.
    :type info: dict
    :param handler: The actual handler method for this route.
    :type handler: function
    """
    if resource not in routes:
        return

    path = _toRoutePath(resource, route)

    if path not in routes[resource]:
        return

    if method in routes[resource][path]:
        del routes[resource][path][method]
        # Clean up any empty route paths
        if not routes[resource][path]:
            del routes[resource][path]
            if not routes[resource]:
                del routes[resource]


def addModel(name, model, resources=None, silent=False):
    """
    Add a model to the Swagger documentation.

    :param resources: The type(s) of resource(s) to add the model to. New
        resource types may be implicitly defined, with the expectation that
        routes will be added for them at some point. If no resources are
        passed, the model will be exposed for every resource type
    :param resources: str or tuple/list[str]
    :param name: The name of the model.
    :type name: str
    :param model: The model to add.
    :type model: dict
    :param silent: Set this to True to suppress warnings.
    :type silent: bool

    .. warning:: This is a low-level API which does not validate the format of
       ``model``. See the `Swagger Model documentation`_ for a complete
       specification of the correct format for ``model``.

    .. versionchanged:: The syntax and behavior of this function was modified
        after v1.3.2. The previous implementation did not include a resources
        parameter.

    .. _Swagger Model documentation: https://github.com/OAI/
        OpenAPI-Specification/blob/0122c22e7fb93b571740dd3c6e141c65563a18be/
        versions/2.0.md#definitionsObject
    """
    if resources:
        if isinstance(resources, six.string_types):
            resources = (resources,)
        for resource in resources:
            models[resource][name] = model
    else:
        if not silent:
            logprint.warning(
                'WARNING: adding swagger models without specifying resources '
                'to bind to is discouraged (%s).' % name)
        models[None][name] = model
