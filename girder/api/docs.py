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


discovery = set()
routes = collections.defaultdict(dict)
models = {}


def addRouteDocs(resource, route, method, info, handler):
    """
    This is called for route handlers that have a description attr on them. It
    gathers the necessary information to build the swagger documentation, which
    is consumed by the docs.Describe endpoint.

    :param resource: The name of the resource, e.g. "item"
    :type resource: str
    :param route: The route to describe.
    :type route: list
    :param method: The HTTP method for this route, e.g. "POST"
    :type method: str
    :param info: The information representing the API documentation.
    :type info: dict
    """
    # Convert wildcard tokens from :foo form to {foo} form.
    convRoute = []
    for token in route:
        if token[0] == ':':
            convRoute.append('{{{}}}'.format(token[1:]))
        else:
            convRoute.append(token)

    path = '/'.join(['', resource] + convRoute)

    info = info.copy()
    info['httpMethod'] = method.upper()

    if 'nickname' not in info:
        info['nickname'] = handler.__name__

    # Add the operation to the given route
    if path not in routes[resource]:
        routes[resource][path] = []

    routes[resource][path].append(info)
    discovery.add(resource)


def removeRouteDocs(resource, route, method, info, handler):
    """
    Remove documentation for a route handler.

    :param resource: The name of the resource, e.g. "item"
    :type resource: str
    :param route: The route to describe.
    :type route: list
    :param method: The HTTP method for this route, e.g. "POST"
    :type method: str
    :param info: The information representing the API documentation.
    :type info: dict
    """
    # Convert wildcard tokens from :foo form to {foo} form.
    convRoute = []
    for token in route:
        if token[0] == ':':
            convRoute.append('{{{}}}'.format(token[1:]))
        else:
            convRoute.append(token)

    path = '/'.join(['', resource] + convRoute)

    if path not in routes[resource]:
        return

    info = info.copy()
    info['httpMethod'] = method.upper()

    if 'nickname' not in info:
        info['nickname'] = handler.__name__
    if info in routes[resource][path]:
        routes[resource][path].remove(info)
        if not len(routes[resource][path]):
            del routes[resource][path]
            if not len(routes[resource]):
                discovery.remove(resource)


def addModel(name, model):
    """
    This is called to add a model to the swagger documentation.

    :param name: The name of the model.
    :type name: str
    :param model: The model to add.
    :type model: dict
    """
    models[name] = model
