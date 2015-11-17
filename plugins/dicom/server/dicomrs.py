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

import cherrypy
import urlparse
import requests

from girder.api.describe import Description
from girder.api.rest import Resource, getUrlParts
from girder.api import access

__all__ = ['dicomStudies', 'dicomSeries', 'dicomInstances']

# QIDO-RS
SearchForDescription = "Searches for DICOM %s that match specified search parameters and returns a" \
                       "list of matching %s and the requested attributes for each %s."

QueryParamDescription = "{attributeID}={value}"
FuzzyMatchingParamDescription = "Set to 'true' to perform additional fuzzy semantic matching of person names."
LimitParamDescription = "If the limit query key is not specified or its value exceeds the total number" \
                        " of matching results then {maximumResults} is the lesser of the number of matching" \
                        "results and the maximum number of results supported by the Server."
OffsetParamDescription = "If the offset query key is not specified or its value is less than zero then it defaults to zero."

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

class dicomStudies(Resource):

    # WADO-RS
    StudyInstanceUIDDescription = "Unique Study instance UID for a single study"
    SeriesInstanceUIDDescription = "Unique Series Instance UID for a single series"
    SOPInstanceUIDDescription = "SOP Instance UID for a single SOP Instance"
    FrameListDescription = "A comma or %2C separated list of one or more non duplicate frame numbers." \
                           "These may be in any order (e.g., ../frames/1,2,4,3)."
    RetrieveMetadataDescription = "Retrieves the DICOM %s metadata with the bulk data removed."

    # STOW-RS
    StoreInstancesDescription = "Stores one or more DICOM instances associated with one or more study instance " \
                                "unique identifiers (SUID). The request message can be DICOM or metadata and bulk " \
                                "data depending on the \"Content-Type\", and is encapsulated in a multipart request body."


    def __init__(self):
        self.resourceName = 'studies'

        ###########
        # WADO-RS #
        ###########

        # {SERVICE}/studies/{StudyInstanceUID}
        self.route('GET', (':StudyInstanceUID',), self.getStudy)

        # {SERVICE}/studies/{StudyInstanceUID}/metadata
        self.route('GET', (':StudyInstanceUID', 'metadata',), self.getStudyMetadata)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}
        self.route('GET', (':StudyInstanceUID', 'series', ':SeriesInstanceUID',), self.getSerie)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/metadata
        self.route('GET', (':StudyInstanceUID', 'series', ':SeriesInstanceUID', 'metadata',), self.getSerieMetadata)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances/{SOPInstanceUID}
        self.route('GET', (':StudyInstanceUID', 'series', ':SeriesInstanceUID', 'instances', ':SOPInstanceUID',), self.getInstance)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances/{SOPInstanceUID}/metadata
        self.route('GET', (':StudyInstanceUID', 'series', ':SeriesInstanceUID', 'instances', ':SOPInstanceUID', 'metadata',), self.getInstanceMetadata)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances/{SOPInstanceUID}/frames/{FrameList}
        self.route('GET', (':StudyInstanceUID', 'series', ':SeriesInstanceUID', 'instances', ':SOPInstanceUID', 'frames', ':FrameList',), self.getFrameList)


        ###########
        # QIDO-RS #
        ###########

        # {+SERVICE}/studies{?query*,fuzzymatching,limit,offset}
        self.route('GET', (), self.searchForStudies)

        # {+SERVICE}/studies/{StudyInstanceUID}/series{?query*,fuzzymatching,limit,offset}
        self.route('GET', (':StudyInstanceUID', 'series'), self.searchForSeries)

        #{+SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances{?query*,fuzzymatching,limit,offset}
        self.route('GET', (':StudyInstanceUID', 'series', ':SeriesInstanceUID', 'instances'), self.searchForInstances)

        #{+SERVICE}/studies/{StudyInstanceUID}/instances{?query*,fuzzymatching,limit,offset}
        self.route('GET', (':StudyInstanceUID', 'instances'), self.searchForInstancesByStudyInstanceUID)

        ###########
        # STOW-RS #
        ###########

        # {SERVICE}/studies[/{StudyInstanceUID}]
        self.route('POST', (), self.storeInstances)
        self.route('POST', (':StudyInstanceUID',), self.storeInstancesInStudy)

    def _reroute(self):
        """This function was written as an experiment to re-route wado-rs query
        made to girder to a service implementing wado-rs.
        """
        incoming_url = getUrlParts()

        incoming_url = urlparse.ParseResult(
            scheme='https',
            netloc='vna.hackathon.siim.org',
            path= 'dcm4chee-arc/wado/DCM4CHEE' + incoming_url.path[7:],
            params=incoming_url.params,
            query=incoming_url.query,
            fragment=incoming_url.fragment
        )
        outgoing_url_str = urlparse.urlunparse(incoming_url)
        print(outgoing_url_str)
        response = requests.get(outgoing_url_str)

        cherrypy.response.headers['Content-Type'] = 'application/dicom'
        return lambda: response.content

    ###########
    # WADO-RS #
    ###########

    @access.user
    def getStudy(self, StudyInstanceUID, params):
        # response can be DICOM or bulk data depending on the "Accept" type
        return self._reroute()

    getStudy.description = (
        Description('Retrieve the set of DICOM instances associated with a given study unique identifier (UID).')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path'))
    getStudy.description = _describe_wadors_errors(getStudy)

    @access.user
    def getStudyMetadata(self, StudyInstanceUID, params):
        return self._reroute()

    getStudyMetadata.description = (
        Description(RetrieveMetadataDescription % 'study')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path'))
    getStudyMetadata.description = _describe_wadors_errors(getStudyMetadata)

    @access.user
    def getSerie(self, StudyInstanceUID, SeriesInstanceUID, params):
        return self._reroute()

    getSerie.description = (
        Description('Retrieve the set of DICOM instances associated with a given study and series UID.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path'))
    getSerie.description = _describe_wadors_errors(getSerie)

    @access.user
    def getSerieMetadata(self, StudyInstanceUID, SeriesInstanceUID, params):
        return self._reroute()

    getSerieMetadata.description = (
        Description(RetrieveMetadataDescription % 'series')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path'))
    getSerieMetadata.description = _describe_wadors_errors(getSerieMetadata)

    @access.user
    def getInstance(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, params):
        return self._reroute()

    getInstance.description = (
        Description('Retrieve the DICOM instance associated with the given study, series, and SOP Instance UID.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path'))
    getInstance.description = _describe_wadors_errors(getInstance)

    @access.user
    def getInstanceMetadata(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, params):
        return self._reroute()

    getInstanceMetadata.description = (
        Description(RetrieveMetadataDescription % 'instance')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path'))
    getInstanceMetadata.description = _describe_wadors_errors(getInstanceMetadata)

    @access.user
    def getFrameList(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, FrameList, params):
        return self._reroute()

    getFrameList.description = (
        Description('Retrieve the DICOM frames for a given study, series, SOP Instance UID, and frame numbers.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path')
        .param('FrameList', FrameListDescription, paramType='path'))
    getFrameList.description = _describe_wadors_errors(getFrameList)

    ###########
    # QIDO-RS #
    ###########

    @access.user
    def searchForStudies(self, params):
        pass

    searchForStudies.description = (
        Description(SearchForDescription % ('Studies', 'studies', 'study'))
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForStudies.description = _describe_qidors_errors(searchForStudies)

    @access.user
    def searchForSeries(self, StudyInstanceUID, params):
        pass

    searchForSeries.description = (
        Description(SearchForDescription % ('Series', 'series', 'series'))
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForSeries.description = _describe_qidors_errors(searchForSeries)

    @access.user
    def searchForInstances(self, StudyInstanceUID, SeriesInstanceUID, params):
        pass

    searchForInstances.description = (
        Description(SearchForDescription % ('Instances', 'instances', 'instance'))
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForInstances.description = _describe_qidors_errors(searchForInstances)

    @access.user
    def searchForInstancesByStudyInstanceUID(self, StudyInstanceUID, params):
        pass

    searchForInstancesByStudyInstanceUID.description = (
        Description(SearchForDescription % ('Instances', 'instances', 'instance'))
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForInstancesByStudyInstanceUID.description = _describe_qidors_errors(searchForInstancesByStudyInstanceUID)

    ###########
    # STOW-RS #
    ###########

    @access.user
    def storeInstances(self, parans):
        # Content-Type - The representation scheme being posted to the RESTful service. The types allowed for this request header are
        # as follows:
        #  • multipart/related; type=application/dicom; boundary={messageBoundary}
        #  Specifies that the post is PS3.10 binary instances. All STOW-RS providers must accept this Content-Type.
        #  • multipart/related; type=application/dicom+xml; boundary={messageBoundary}
        #  Specifies that the post is PS3.19 XML metadata and bulk data. All STOW-RS providers must accept this Content-Type.
        #  • multipart/related; type=application/json; boundary={messageBoundary}
        #  Specifies that the post is DICOM JSON metadata and bulk data. A STOW-RS provider may optionally accept this Content-Type.
        pass

    storeInstances.description = (
        Description(StoreInstancesDescription))
    storeInstances.description = _describe_stowrs_errors(storeInstances)


    @access.user
    def storeInstancesInStudy(self, StudyInstanceUID, parans):
        # Content-Type - See above
        pass

    storeInstancesInStudy.description = (
        Description(StoreInstancesDescription)
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path'))
    storeInstancesInStudy.description = _describe_stowrs_errors(storeInstancesInStudy)


class dicomSeries(Resource):
    def __init__(self):
        self.resourceName = 'series'

        ###########
        # QIDO-RS #
        ###########

        # {+SERVICE}/series{?query*,fuzzymatching,limit,offset}
        self.route('GET', (), self.searchForSeries)

    ###########
    # QIDO-RS #
    ###########

    @access.user
    def searchForSeries(self, params):
        pass

    searchForSeries.description = (
        Description(SearchForDescription % ('Series', 'series', 'series'))
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForSeries.description = _describe_qidors_errors(searchForSeries)


class dicomInstances(Resource):
    def __init__(self):
        self.resourceName = 'instances'

        ###########
        # QIDO-RS #
        ###########

        # {+SERVICE}/instances{?query*,fuzzymatching,limit,offset}
        self.route('GET', (), self.searchForInstances)

    ###########
    # QIDO-RS #
    ###########

    @access.user
    def searchForInstances(self, params):
        pass

    searchForInstances.description = (
        Description(SearchForDescription % ('Instances', 'instances', 'instance'))
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForInstances.description = _describe_qidors_errors(searchForInstances)
