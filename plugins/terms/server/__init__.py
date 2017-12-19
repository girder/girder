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

import datetime
import hashlib

from girder import events
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import boundHandler
from girder.api.v1.collection import Collection
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.models.collection import Collection as CollectionModel
from girder.models.user import User


@access.user(scope=TokenScope.DATA_READ)
@boundHandler
@autoDescribeRoute(
    Description('Accept a collection\'s Terms of Use for the current user.')
    .modelParam('id', model=CollectionModel, level=AccessType.READ)
    .param('termsHash', 'The SHA-256 hash of this collection\'s terms, encoded in hexadecimal.')
)
def acceptCollectionTerms(self, collection, termsHash):
    if not collection.get('terms'):
        raise RestException('This collection currently has no terms.')

    # termsHash should be encoded to a bytes object, but storing bytes into MongoDB behaves
    # differently in Python 2 vs 3. Additionally, serializing a bytes to JSON behaves differently
    # in Python 2 vs 3. So, just keep it as a unicode (or ordinary Python 2 str).
    realTermsHash = hashlib.sha256(collection['terms'].encode('utf-8')).hexdigest()
    if termsHash != realTermsHash:
        # This "proves" that the client has at least accessed the terms
        raise RestException(
            'The submitted "termsHash" does not correspond to the collection\'s current terms.')

    User().update(
        {'_id': self.getCurrentUser()['_id']},
        {'$set': {
            'terms.collection.%s' % collection['_id']: {
                'hash': termsHash,
                'accepted': datetime.datetime.now()
            }
        }}
    )


def afterPostPutCollection(event):
    # This will only trigger if no exceptions (for access, invalid id, etc.) are thrown
    extraParams = event.info['params']
    if 'terms' in extraParams:
        collectionResponse = event.info['returnVal']
        collectionId = collectionResponse['_id']
        terms = extraParams['terms']

        CollectionModel().update(
            {'_id': collectionId},
            {'$set': {'terms': terms}}
        )

        collectionResponse['terms'] = terms
        event.addResponse(collectionResponse)


def load(info):
    # Augment the collection creation and edit routes to accept a terms field
    events.bind('rest.post.collection.after', 'terms', afterPostPutCollection)
    events.bind('rest.put.collection/:id.after', 'terms', afterPostPutCollection)
    for handler in [
        Collection.createCollection,
        Collection.updateCollection
    ]:
        handler.description.param('terms', 'The Terms of Use for the collection.', required=False)

    # Expose the terms field on all collections
    CollectionModel().exposeFields(level=AccessType.READ, fields={'terms'})

    # Add endpoint for registered users to accept terms
    info['apiRoot'].collection.route('POST', (':id', 'acceptTerms'), acceptCollectionTerms)

    # Expose the terms field on all users
    User().exposeFields(level=AccessType.ADMIN, fields={'terms'})
