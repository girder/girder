# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

"""This module contains utility methods for parsing girder path strings."""

import re
from ..constants import AccessType
from ..exceptions import AccessException, GirderException, ValidationException
from ..exceptions import ResourcePathNotFound
from .model_importer import ModelImporter
from girder.models.collection import Collection
from girder.models.user import User


# Expose the ResourcePathNotFound exception as its original name
NotFoundException = ResourcePathNotFound


def encode(token):
    """Escape special characters in a token for path representation.

    :param str token: The token to encode
    :return: The encoded string
    :rtype: str
    """
    return token.replace('\\', '\\\\').replace('/', '\\/')


def decode(token):
    """Un-escape special characters in a token from a path representation.

    :param str token: The token to decode
    :return: The decoded string
    :rtype: str
    """
    return token.replace(r'\/', '/').replace('\\\\', '\\')


def split(path):
    """Split an encoded path string into decoded tokens.

    :param str path: An encoded path string
    :return: A list of decoded tokens
    :rtype: `list`
    """
    # It would be better to split by the regex `(?<!\\)(?>\\\\)*/`,
    # but python does't support atomic grouping. :(
    chunks = path.split('/')
    processed = [chunks[0]]

    # matches an odd number of backslashes at the end of the string
    escape = re.compile(r'(?<!\\)(?:\\\\)*\\$')

    # Loop through the chunks and check if any of the forward slashes was
    # escaped.
    for chunk in chunks[1:]:
        if escape.search(processed[-1]):
            # join the chunks
            processed[-1] = processed[-1] + '/' + chunk
        else:
            # append a new token
            processed.append(chunk)

    # now decode all of the tokens and return
    return [decode(token) for token in processed]


def join(tokens):
    """Join a list of tokens into an encoded path string.

    :param tokens: A list of tokens
    :return: The encoded path string
    :rtype: str
    """
    return '/'.join([encode(token) for token in tokens])


def lookUpToken(token, parentType, parent):
    """
    Find a particular child resource by name or throw an exception.

    :param token: the name of the child resource to find
    :param parentType: the type of the parent to search
    :param parent: the parent resource
    :returns: the child resource
    """
    # (model name, mask, search filter)
    searchTable = (
        ('folder', parentType in ('user', 'collection', 'folder'), {
            'name': token,
            'parentId': parent['_id'],
            'parentCollection': parentType
        }),
        ('item', parentType == 'folder', {'name': token, 'folderId': parent['_id']}),
        ('file', parentType == 'item', {'name': token, 'itemId': parent['_id']}),
    )

    for candidateModel, mask, filterObject in searchTable:
        if not mask:
            continue

        candidateChild = ModelImporter.model(candidateModel).findOne(filterObject)
        if candidateChild is not None:
            return candidateChild, candidateModel

    # if no folder, item, or file matches, give up
    raise ResourcePathNotFound('Child resource not found: %s(%s)->%s' % (
        parentType, parent.get('name', parent.get('_id')), token))


def lookUpPath(path, user=None, test=False, filter=True, force=False):
    """
    Look up a resource in the data hierarchy by path.

    :param path: path of the resource
    :param user: user with correct privileges to access path
    :param test: defaults to false, when set to true
        will return None instead of throwing exception when
        path doesn't exist
    :type test: bool
    :param filter: Whether the returned model should be filtered.
    :type filter: bool
    :param force: if True, don't validate the access.
    :type force: bool
    """
    path = path.lstrip('/')
    pathArray = split(path)
    model = pathArray[0]

    if model == 'user':
        username = pathArray[1]
        parent = User().findOne({'login': username})

        if parent is None:
            if test:
                return {
                    'model': None,
                    'document': None
                }
            else:
                raise ResourcePathNotFound('User not found: %s' % username)

    elif model == 'collection':
        collectionName = pathArray[1]
        parent = Collection().findOne({'name': collectionName})

        if parent is None:
            if test:
                return {
                    'model': None,
                    'document': None
                }
            else:
                raise ResourcePathNotFound('Collection not found: %s' % collectionName)

    else:
        raise ValidationException('Invalid path format')

    try:
        document = parent
        if not force:
            ModelImporter.model(model).requireAccess(document, user)
        for token in pathArray[2:]:
            document, model = lookUpToken(token, model, document)
            if not force:
                ModelImporter.model(model).requireAccess(document, user)
    except (ValidationException, AccessException):
        # We should not distinguish the response between access and validation errors so that
        # adversarial users cannot discover the existence of data they don't have access to by
        # looking up a path.
        if test:
            return {
                'model': None,
                'document': None
            }
        else:
            raise ResourcePathNotFound('Path not found: %s' % path)

    if filter:
        document = ModelImporter.model(model).filter(document, user)

    return {
        'model': model,
        'document': document
    }


def getResourceName(type, doc):
    """
    Get the name of a resource that can be put in a path,

    :param type: the resource model type.
    :type type: str
    :param doc: the resource document.
    :type doc: dict
    :return: the name of the resource.
    :rtype: str
    """
    if type == 'user':
        return doc['login']
    elif type in ('file', 'item', 'folder', 'user', 'collection'):
        return doc['name']
    else:
        raise GirderException('Invalid resource type.')


def getResourcePath(type, doc, user=None, force=False):
    """
    Get the path for a resource.

    :param type: the resource model type.
    :type type: str
    :param doc: the resource document.
    :type doc: dict
    :param user: user with correct privileges to access path
    :type user: dict or None
    :param force: if True, don't validate the access.
    :type force: bool
    :return: the path to the resource.
    :rtype: str
    """
    path = []
    while True:
        path.insert(0, getResourceName(type, doc))
        if type == 'file':
            parentModel = 'item'
            parentId = doc['itemId']
        elif type == 'item':
            parentModel = 'folder'
            parentId = doc['folderId']
        elif type == 'folder':
            parentModel = doc['parentCollection']
            parentId = doc['parentId']
        else:
            break
        doc = ModelImporter.model(parentModel).load(
            id=parentId, user=user, level=AccessType.READ, force=force)
        type = parentModel
    path.insert(0, type)
    return '/' + join(path)
