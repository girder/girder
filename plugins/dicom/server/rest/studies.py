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

from error_descriptions import describe_wadors_errors, describe_qidors_errors, describe_stowrs_errors
from param_descriptions import *


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
    getStudy.description = describe_wadors_errors(getStudy)

    @access.user
    def getStudyMetadata(self, StudyInstanceUID, params):
        return self._reroute()

    getStudyMetadata.description = (
        Description(RetrieveMetadataDescription % 'study')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path'))
    getStudyMetadata.description = describe_wadors_errors(getStudyMetadata)

    @access.user
    def getSerie(self, StudyInstanceUID, SeriesInstanceUID, params):
        return self._reroute()

    getSerie.description = (
        Description('Retrieve the set of DICOM instances associated with a given study and series UID.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path'))
    getSerie.description = describe_wadors_errors(getSerie)

    @access.user
    def getSerieMetadata(self, StudyInstanceUID, SeriesInstanceUID, params):
        return self._reroute()

    getSerieMetadata.description = (
        Description(RetrieveMetadataDescription % 'series')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path'))
    getSerieMetadata.description = describe_wadors_errors(getSerieMetadata)

    @access.user
    def getInstance(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, params):
        return self._reroute()

    getInstance.description = (
        Description('Retrieve the DICOM instance associated with the given study, series, and SOP Instance UID.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path'))
    getInstance.description = describe_wadors_errors(getInstance)

    @access.user
    def getInstanceMetadata(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, params):
        return self._reroute()

    getInstanceMetadata.description = (
        Description(RetrieveMetadataDescription % 'instance')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path'))
    getInstanceMetadata.description = describe_wadors_errors(getInstanceMetadata)

    @access.user
    def getFrameList(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, FrameList, params):
        return self._reroute()

    getFrameList.description = (
        Description('Retrieve the DICOM frames for a given study, series, SOP Instance UID, and frame numbers.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription, paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path')
        .param('FrameList', FrameListDescription, paramType='path'))
    getFrameList.description = describe_wadors_errors(getFrameList)

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
    searchForStudies.description = describe_qidors_errors(searchForStudies)

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
    searchForSeries.description = describe_qidors_errors(searchForSeries)

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
    searchForInstances.description = describe_qidors_errors(searchForInstances)

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
    searchForInstancesByStudyInstanceUID.description = describe_qidors_errors(searchForInstancesByStudyInstanceUID)

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
    storeInstances.description = describe_stowrs_errors(storeInstances)


    @access.user
    def storeInstancesInStudy(self, StudyInstanceUID, parans):
        # Content-Type - See above
        pass

    storeInstancesInStudy.description = (
        Description(StoreInstancesDescription)
        .param('StudyInstanceUID', StudyInstanceUIDDescription, paramType='path'))
    storeInstancesInStudy.description = describe_stowrs_errors(storeInstancesInStudy)
