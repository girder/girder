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

import six

from girder.api.rest import RestException

# Common DICOMWeb service error codes and descriptions
error_descriptions = {
    'WADO-RS': {

        206: 'Partial Content: Accept type, Transfer Syntax or decompression '
             'method supported for some but not all requested content.',
        400: 'Bad Request: Malformed resource.',
        404: 'Not Found: Specified resource does not exist.',
        406: 'Not Acceptable: Accept type, Transfer Syntax or decompression '
             'method not supported.',
        410: 'Gone: Specified resource was deleted.',
        503: 'Busy: Service is unavailable.'
    },
    'QIDO-RS': {
        400: 'Bad Request: The QIDO-RS Provider was unable to perform the '
             'query because the Service Provider cannot understand the query '
             'component.',
        401: 'Unauthorized: The QIDO-RS Provider refused to perform the query '
             'because the client is not authenticated.',
        403: 'Forbidden: The QIDO-RS Provider understood the request, but is '
             'refusing to perform the query (e.g., an authenticated user with '
             'insufficient privileges).',
        413: 'Request entity too large: The query was too broad and a narrower '
             'query or paging should be requested. The use of this status code '
             'should be documented in the conformance statement.',
        503: 'Busy: Service is unavailable.'
    },
    'STOW-RS': {
        400: 'Bad Request: This indicates that the STOW-RS Service was unable '
             'to store any instances due to bad syntax.',
        401: 'Unauthorized: This indicates that the STOW-RS Service refused to '
             'create or append any instances because the client is not '
             'authorized.',
        403: 'Forbidden: This indicates that the STOW-RS Service understood '
             'the request, but is refusing to fulfill it (e.g., an authorized '
             'user with insufficient privileges).',
        409: 'Conflict: This indicates that the STOW-RS Service request was '
             'formed correctly but the service was unable to store any '
             'instances due to a conflict in the request (e.g., unsupported '
             'SOP Class or StudyInstanceUID mismatch). This may also be used '
             'to indicate that a STOW-RS Service was unable to store any '
             'instances for a mixture of reasons. Additional information '
             'regarding the instance errors can be found in the XML response '
             'message body.',
        415: 'Unsupported Media Type: This indicates that the STOW-RS Service '
             'does not support the Content-Type specified in the storage '
             'request (e.g., the service does not support JSON metadata).'
    }
}


def describeErrors(service):
    """
    Function that can be applied as a decorator following @describeRoute to
    add common error responses for a given service to the route description.

    :param service: The service name.
    :type service: str
    """
    def wrapped(func):
        if not hasattr(func, 'description'):
            raise RestException('Description not found on %s' % str(func))
        if service not in error_descriptions:
            raise RestException('Invalid service: %s' % service)
        for code, reason in sorted(six.viewitems(error_descriptions[service])):
            func.description.errorResponse(reason, code)
        return func
    return wrapped
