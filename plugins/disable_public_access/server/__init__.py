#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types

from girder import logger
from girder.api import access
from girder.api.rest import Resource
from girder.constants import AccessType, TokenScope
from girder.models.user import User


def adjustExistingRoutes(apiRoot):
    """
    Modify exsiting public GET routes to require them to be user-access
    controlled.  This skips:
     GET describe
     GET user/authentication
     GET user/me

    :param apiRoot: the root object that contains resources to modify.
    """
    for attr in dir(apiRoot):
        if 'get' not in getattr(getattr(apiRoot, attr), '_routes', {}):
            continue
        if attr == 'describe':
            continue
        getRoutes = getattr(apiRoot, attr)._routes['get']
        for lenroute in getRoutes:
            for idx, (route, handler) in enumerate(getRoutes[lenroute]):
                if attr == 'user' and route in (('me',), ('authentication',)):
                    continue
                newHandler = adjustRouteHandler(attr, route, handler)
                if newHandler != handler:
                    getRoutes[lenroute][idx] = (route, handler)
                getRoutes[lenroute][idx] = (route, handler)


def adjustRouteHandler(name, route, handler):
    """
    If a handler is (a) not public, (b) does not have a scope or has a scope of
    DATA_READ or USER_INFO_READ, (c) does not use cookie auth, (d) does not
    have the alwaysPublic attribute set, THEN wrap the handler to require user
    access.

    :param name: name used for logging.
    :param route: route used for logging.
    :param handler: handler to check and possibly wrap.
    :return: the original or wrapped handler.
    """
    if getattr(handler, 'accessLevel', None) != 'public':
        return handler
    if getattr(handler, 'requiredScopes', None) not in (
            None,
            TokenScope.DATA_READ,
            TokenScope.USER_INFO_READ):
        return handler
    if getattr(handler, 'cookieAuth', None):
        return handler
    if getattr(handler, 'alwaysPublic', None):
        return handler
    logger.info('Disabling public route access: %s',
                '/'.join([name] + list(route)))
    return access.user(handler, scope=getattr(handler, 'requiredScopes', None))


def modifyResourceToAdjustFutureRoutes():
    """
    Modify the base resource so future routes will also have wrapped handlers.
    """
    Resource._origRoute = Resource.route

    def adjustRoute(self, method, route, handler, nodoc=False, resource=None):
        if getattr(self, 'resourceName', None):
            handler = adjustRouteHandler(self.resourceName, route, handler)
        return self._origRoute(method, route, handler, nodoc, resource)

    Resource.route = adjustRoute


def restrictUserListings():
    """
    Modify the user filter and find by permissions to always require at least
    write level access.
    """
    user = User()
    filterResultsByPermission = user.filterResultsByPermission
    findWithPermissions = user.findWithPermissions

    def restrictFilterResultsByPermission(self, cursor, user, level, limit=0, offset=0,
                                          removeKeys=(), flags=None):
        level = max(AccessType.WRITE, level)
        return filterResultsByPermission(
            cursor=cursor, user=user, level=level, limit=limit, offset=offset,
            removeKeys=removeKeys, flags=flags)

    def restrictFindWithPermissions(self, query=None, offset=0, limit=0, timeout=None, fields=None,
                                    sort=None, user=None, level=AccessType.READ, **kwargs):
        level = max(AccessType.WRITE, level)
        return findWithPermissions(
            query=query, offset=offset, limit=limit, timeout=timeout,
            fields=fields, sort=sort, user=user, level=level, **kwargs)

    user.filterResultsByPermission = types.MethodType(restrictFilterResultsByPermission, user)
    user.findWithPermissions = types.MethodType(restrictFindWithPermissions, user)


def load(info):
    """
    Modify most public GET routes to require them to be user-access controlled.
    Adjust the User model is adjusted so that finding or filtering results by
    permission always filter by at least write-level permissions.
    """
    # If we have already installed this, don't do it again.
    if hasattr(Resource, '_origRoute'):
        return
    adjustExistingRoutes(info['apiRoot'])
    modifyResourceToAdjustFutureRoutes()
    restrictUserListings()
