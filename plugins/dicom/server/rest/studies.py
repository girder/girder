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

from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, getUrlParts
from girder.api import access

from error_descriptions import describeErrors
from param_descriptions import (SearchForDescription, QueryParamDescription,
                                FuzzyMatchingParamDescription,
                                LimitParamDescription, OffsetParamDescription)


class dicomStudies(Resource):

    # WADO-RS
    StudyInstanceUIDDescription = "Unique Study instance UID for a single study"
    SeriesInstanceUIDDescription = "Unique Series Instance UID for a single " \
                                   "series"
    SOPInstanceUIDDescription = "SOP Instance UID for a single SOP Instance"
    FrameListDescription = "A comma or %2C separated list of one or more non-" \
                           "duplicate frame numbers. These may be in any " \
                           "order (e.g., ../frames/1,2,4,3)."
    RetrieveMetadataDescription = "Retrieves the DICOM %s metadata with the " \
                                  "bulk data removed."

    # STOW-RS
    StoreInstancesDescription = "Stores one or more DICOM instances " \
                                "associated with one or more study instance " \
                                "unique identifiers (SUID). The request " \
                                "message can be DICOM or metadata and bulk " \
                                "data depending on the \"Content-Type\", and " \
                                "is encapsulated in a multipart request body."

    def __init__(self):
        super(dicomStudies, self).__init__()

        self.resourceName = 'studies'

        ###########
        # WADO-RS #
        ###########

        # {SERVICE}/studies/{StudyInstanceUID}
        self.route('GET',
                   (':StudyInstanceUID',),
                   self.getStudy)

        # {SERVICE}/studies/{StudyInstanceUID}/metadata
        self.route('GET', (':StudyInstanceUID', 'metadata',),
                   self.getStudyMetadata)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}
        self.route('GET',
                   (':StudyInstanceUID', 'series', ':SeriesInstanceUID',),
                   self.getSeries)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/metadata
        self.route('GET',
                   (':StudyInstanceUID', 'series', ':SeriesInstanceUID',
                    'metadata',),
                   self.getSeriesMetadata)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances/{SOPInstanceUID}
        self.route('GET',
                   (':StudyInstanceUID', 'series', ':SeriesInstanceUID',
                    'instances', ':SOPInstanceUID',),
                   self.getInstance)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances/{SOPInstanceUID}/metadata
        self.route('GET',
                   (':StudyInstanceUID', 'series', ':SeriesInstanceUID',
                    'instances', ':SOPInstanceUID', 'metadata',),
                   self.getInstanceMetadata)

        # {SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances/{SOPInstanceUID}/frames/{FrameList}
        self.route('GET',
                   (':StudyInstanceUID', 'series', ':SeriesInstanceUID',
                    'instances', ':SOPInstanceUID', 'frames', ':FrameList',),
                   self.getFrameList)

        ###########
        # QIDO-RS #
        ###########

        # {+SERVICE}/studies{?query*,fuzzymatching,limit,offset}
        self.route('GET',
                   (),
                   self.searchForStudies)

        # {+SERVICE}/studies/{StudyInstanceUID}/series{?query*,fuzzymatching,limit,offset}
        self.route('GET',
                   (':StudyInstanceUID', 'series'),
                   self.searchForSeries)

        # {+SERVICE}/studies/{StudyInstanceUID}/series/{SeriesInstanceUID}/instances{?query*,fuzzymatching,limit,offset}
        self.route('GET',
                   (':StudyInstanceUID', 'series', ':SeriesInstanceUID',
                    'instances'),
                   self.searchForInstances)

        # {+SERVICE}/studies/{StudyInstanceUID}/instances{?query*,fuzzymatching,limit,offset}
        self.route('GET',
                   (':StudyInstanceUID', 'instances'),
                   self.searchForInstancesByStudyInstanceUID)

        ###########
        # STOW-RS #
        ###########

        # {SERVICE}/studies[/{StudyInstanceUID}]
        self.route('POST',
                   (),
                   self.storeInstances)
        self.route('POST',
                   (':StudyInstanceUID',),
                   self.storeInstancesInStudy)

    def _reroute(self):
        """This function was written as an experiment to re-route wado-rs query
        made to girder to a service implementing wado-rs.
        """
        incoming_url = getUrlParts()

        incoming_url = urlparse.ParseResult(
            scheme='https',
            netloc='vna.hackathon.siim.org',
            path='dcm4chee-arc/wado/DCM4CHEE' + incoming_url.path[7:],
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
    @describeErrors('WADO-RS')
    @describeRoute(
        Description('Retrieve the set of DICOM instances associated with a '
                    'given study unique identifier (UID).')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
    )
    def getStudy(self, StudyInstanceUID, params):
        # response can be DICOM or bulk data depending on the "Accept" type
        return self._reroute()

    @access.user
    @describeErrors('WADO-RS')
    @describeRoute(
        Description(RetrieveMetadataDescription % 'study')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
    )
    def getStudyMetadata(self, StudyInstanceUID, params):
        return self._reroute()

    @access.user
    @describeErrors('WADO-RS')
    @describeRoute(
        Description('Retrieve the set of DICOM instances associated with a '
                    'given study and series UID.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription,
               paramType='path')
    )
    def getSeries(self, StudyInstanceUID, SeriesInstanceUID, params):
        return self._reroute()

    @access.user
    @describeErrors('WADO-RS')
    @describeRoute(
        Description(RetrieveMetadataDescription % 'series')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription,
               paramType='path')
    )
    def getSeriesMetadata(self, StudyInstanceUID, SeriesInstanceUID, params):
        return self._reroute()

    @access.user
    @describeErrors('WADO-RS')
    @describeRoute(
        Description('Retrieve the DICOM instance associated with the given '
                    'study, series, and SOP Instance UID.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription,
               paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path')
    )
    def getInstance(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID,
                    params):
        return self._reroute()

    @access.user
    @describeErrors('WADO-RS')
    @describeRoute(
        Description(RetrieveMetadataDescription % 'instance')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription,
               paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path')
    )
    def getInstanceMetadata(self, StudyInstanceUID, SeriesInstanceUID,
                            SOPInstanceUID, params):
        return self._reroute()

    @access.user
    @describeErrors('WADO-RS')
    @describeRoute(
        Description('Retrieve the DICOM frames for a given study, series, SOP '
                    'Instance UID, and frame numbers.')
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription,
               paramType='path')
        .param('SOPInstanceUID', SOPInstanceUIDDescription, paramType='path')
        .param('FrameList', FrameListDescription, paramType='path')
    )
    def getFrameList(self, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID,
                     FrameList, params):
        return self._reroute()

    ###########
    # QIDO-RS #
    ###########

    @access.user
    @describeErrors('QIDO-RS')
    @describeRoute(
        Description(SearchForDescription % ('Studies', 'studies', 'study'))
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0)
    )
    def searchForStudies(self, params):
        pass

    @access.user
    @describeErrors('QIDO-RS')
    @describeRoute(
        Description(SearchForDescription % ('Series', 'series', 'series'))
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0)
    )
    def searchForSeries(self, StudyInstanceUID, params):
        pass

    @access.user
    @describeErrors('QIDO-RS')
    @describeRoute(
        Description(SearchForDescription %
                    ('Instances', 'instances', 'instance'))
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('SeriesInstanceUID', SeriesInstanceUIDDescription,
               paramType='path')
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0)
    )
    def searchForInstances(self, StudyInstanceUID, SeriesInstanceUID, params):
        pass

    @access.user
    @describeErrors('QIDO-RS')
    @describeRoute(
        Description(SearchForDescription %
                    ('Instances', 'instances', 'instance'))
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0)
    )
    def searchForInstancesByStudyInstanceUID(self, StudyInstanceUID, params):
        pass

    ###########
    # STOW-RS #
    ###########

    @access.user
    @describeErrors('STOW-RS')
    @describeRoute(
        Description(StoreInstancesDescription)
    )
    def storeInstances(self, params):
        # Content-Type - The representation scheme being posted to the RESTful
        # service. The types allowed for this request header are
        # as follows:
        #  • multipart/related; type=application/dicom; boundary={messageBoundary} # noqa
        #  Specifies that the post is PS3.10 binary instances. All STOW-RS
        #  providers must accept this Content-Type.
        #  • multipart/related; type=application/dicom+xml; boundary={messageBoundary} # noqa
        #  Specifies that the post is PS3.19 XML metadata and bulk data. All
        #  STOW-RS providers must accept this Content-Type.
        #  • multipart/related; type=application/json; boundary={messageBoundary} # noqa
        #  Specifies that the post is DICOM JSON metadata and bulk data. A
        #  STOW-RS provider may optionally accept this Content-Type.
        pass

    @access.user
    @describeErrors('STOW-RS')
    @describeRoute(
        Description(StoreInstancesDescription)
        .param('StudyInstanceUID', StudyInstanceUIDDescription,
               paramType='path')
    )
    def storeInstancesInStudy(self, StudyInstanceUID, params):
        # Content-Type - See above
        pass
