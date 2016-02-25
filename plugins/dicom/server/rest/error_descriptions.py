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

# from girder.api.describe import Description
# from girder.api.rest import Resource
# from girder.api import access


def _describe_wadors_errors(func):
    return (func.description
        .errorResponse('Partial Content: Accept type, Transfer Syntax or decompression method '
                       'supported for some but not all requested content.', 206)
        .errorResponse('Bad Request: Malformed resource.', 400)
        .errorResponse('Not Found: Specified resource does not exist.', 404)
        .errorResponse('Not Acceptable: Accept type, Transfer Syntax or decompression method not supported.', 406)
        .errorResponse('Gone: Specified resource was deleted.', 410)
        .errorResponse('Busy: Service is unavailable.', 503))

def _describe_qidors_errors(func):
    return (func.description
        .errorResponse('Bad Request: The QIDO-RS Provider was unable to perform the query '
                       'because the Service Provider cannot understand the query component.', 400)
        .errorResponse('Unauthorized: The QIDO-RS Provider refused to perform the query because '
                       'the client is not authenticated.', 401)
        .errorResponse('Forbidden: The QIDO-RS Provider understood the request, but is refusing to '
                       'perform the query (e.g., an authenticated user with insufficient privileges).', 403)
        .errorResponse('Request entity too large: The query was too broad and a narrower query or '
                       'paging should be requested. The use of this status code should be documented '
                       'in the conformance statement.', 413)
        .errorResponse('Busy: Service is unavailable.', 503))

def _describe_stowrs_errors(func):
    return (func.description
        .errorResponse('Bad Request: This indicates that the STOW-RS Service was unable to store '
                       'any instances due to bad syntax.', 400)
        .errorResponse('Unauthorized: This indicates that the STOW-RS Service refused to create or '
                       'append any instances because the client is not authorized.', 401)
        .errorResponse('Forbidden: This indicates that the STOW-RS Service understood the request, '
                       'but is refusing to fulfill it (e.g., an authorized user with insufficient '
                       'privileges).', 403)
        .errorResponse('Conflict: This indicates that the STOW-RS Service request was formed correctly '
                       'but the service was unable to store any instances due to a conflict in the request '
                       '(e.g., unsupported SOP Class or StudyInstanceUID mismatch). This may also be used to '
                       'indicate that a STOW-RS Service was unable to store any instances for a mixture of '
                       'reasons. Additional information regarding the instance errors can be found in the '
                       'XML response message body.', 409)
        .errorResponse('Unsupported Media Type: This indicates that the STOW-RS Service does not support '
                       'the Content-Type specified in the storage request (e.g., the service does not '
                       'support JSON metadata).)', 415))
