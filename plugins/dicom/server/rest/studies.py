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
import itertools
import requests
import six
from six.moves import urllib

from dicom.datadict import dictionary_has_tag, tag_for_name
from dicom.dataelem import DataElement
from dicom.tag import Tag

from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException, getApiUrl, getUrlParts
from girder.api import access
from girder.constants import AccessType

from ..dicom_json_conversion import dataElementToJSON

from .error_descriptions import describeErrors
from .param_descriptions import (SearchForDescription, QueryParamDescription,
                                 FuzzyMatchingParamDescription,
                                 LimitParamDescription, OffsetParamDescription)


def tagToString(tag):
    """
    Return eight character uppercase hexadecimal string representation of
    dicom.tag.Tag.
    """
    return "{:04X}{:04X}".format(tag.group, tag.element)


def stringToTag(val):
    """
    Convert eight character hexadecimal string to dicom.tag.Tag.
    """
    if not val or len(val) != 8:
        raise ValueError('Invalid eight character hexadecimal string')
    group = val[0:4]
    element = val[4:8]
    return Tag(group, element)


def parseIncludeFields(includeFields):
    """
    Parse and validate 'includefield' query parameters.

    Return list of string representations of tags of requested fields.
    """
    stringTags = []
    for field in includeFields:
        field = field.strip()
        if not field:
            raise RestException(
                'Invalid includefield value: "%s"' % field)
        tag = tag_for_name(field)
        stringTag = None
        if tag:
            stringTag = tagToString(Tag(tag))
        else:
            try:
                tag = stringToTag(field)
                if not dictionary_has_tag(tag):
                    raise RestException(
                        'Invalid includefield value: "%s"' % field)
            except ValueError:
                raise RestException(
                    'Invalid includefield value: "%s"' % field)

            stringTag = field

        if stringTag:
            stringTags.append(stringTag)

    return stringTags


def parseQueryKeys(params):
    """
    Parse and validate {query} keys from query parameters.

    Return list of (tag string, value) tuples of requested query keys.

    See: Table 6.7.1-1. QIDO-RS STUDY Search Query Keys
    """
    supportedQueryKeys = (
        '00080020',  # StudyDate
        '00080030',  # StudyTime
        '00080050',  # AccessionNumber
        '00080061',  # ModalitiesInStudy
        '00080090',  # ReferringPhysicianName
        '00100010',  # PatientName
        '00100020',  # PatientID
        '0020000D',  # StudyInstanceUID
        '00200010'   # StudyID
    )
    items = []
    usedKeys = set()
    for key, value in six.viewitems(params):
        # Get string hexadecimal representation of tag as-is or from keyword
        tagString = key
        tag = tag_for_name(key)
        if tag:
            tagString = tagToString(Tag(tag))

        # Verify that tag is supported
        if tagString not in supportedQueryKeys:
            raise RestException('Unsupported query key: %s' % key)

        # Verify that key is specified only once
        if not isinstance(value, six.string_types):
            raise RestException('Duplicate query key: %s' % key)
        if tagString in usedKeys:
            raise RestException('Duplicate query key: %s' % key)
        usedKeys.add(tagString)

        # Add item
        items.append((tagString, value))

    return items


def getUniqueStudies(cursor):
    """
    Return one document per study in cursor.
    Identify unique studies by the following tag:
      0020000D: StudyInstanceUID
    """
    studyInstanceUIDs = set(cursor.distinct('meta.0020000D.Value'))
    results = []
    for item in cursor:
        meta = item.get('meta', None)
        if not meta:
            continue
        if '0020000D' in meta and \
           'Value' in meta['0020000D'] and \
           len(meta['0020000D']['Value']):
            uid = meta['0020000D']['Value'][0]
            if uid in studyInstanceUIDs:
                results.append(meta)
                studyInstanceUIDs.remove(uid)
    return results


class DicomStudies(Resource):

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
        super(DicomStudies, self).__init__()

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

        incoming_url = urllib.parse.urlparse.ParseResult(
            scheme='https',
            netloc='vna.hackathon.siim.org',
            path='dcm4chee-arc/wado/DCM4CHEE' + incoming_url.path[7:],
            params=incoming_url.params,
            query=incoming_url.query,
            fragment=incoming_url.fragment
        )
        outgoing_url_str = urllib.parse.urlunparse(incoming_url)
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
    # XXX: there is no explicit parameter named 'query'
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
        user = self.getCurrentUser()

        # Parse query parameters. Remove parsed parameters so only {query}
        # parameters, as defined in "6.7.1 QIDO-RS - Search", remain.
        limit, offset, sort = self.getPagingParameters(params)
        params.pop('limit', None)
        params.pop('offset', None)
        params.pop('sort', None)

        # Parse 'fuzzymatching' parameter
        #
        # See: 6.7.1.2.1 Matching
        fuzzymatching = self.boolParam('fuzzymatching', params, default=False)
        if fuzzymatching:
            cherrypy.response.headers['Warning'] = '299 %s: ' \
                'The fuzzymatching parameter is not supported. ' \
                'Only literal matching has been performed.' % getApiUrl()
        params.pop('fuzzymatching', None)

        # Parse include fields
        includeFields = params.pop('includefield', None)
        if isinstance(includeFields, six.string_types):
            includeFields = (includeFields,)

        # Parse query keys
        queryItems = parseQueryKeys(params)

        # Build query dictionary
        query = {}
        for tagString, value in queryItems:
            if len(value):
                # Handle PN tags:
                #   00080090: ReferringPhysicianName
                #   00100010: PatientName
                if tagString == '00080090' or tagString == '00100010':
                    query['meta.' + tagString + '.Value.Alphabetic'] = value
                else:
                    query['meta.' + tagString + '.Value'] = value
            else:
                query['meta.' + tagString] = {'$exists': True}
                query['meta.' + tagString + '.Value'] = {'$exists': False}

        # Omit 'meta' field
        fields = {'meta': False}

        cursor = self.model('item').find(query, fields=fields)

        results = self.model('item').filterResultsByPermission(
            cursor, user, AccessType.READ, limit=0, offset=0)

        # Query filtered documents, include 'meta' field
        query = {
            '_id': {
                '$in': [item['_id'] for item in results]
            }
        }

        # See Table 6.7.1-2. QIDO-RS STUDY Returned Attributes
        attributesToReturn = [
            '00080005',  # Specific Character Set
            '00080020',  # Study Date
            '00080030',  # Study Time
            '00080050',  # Accession Number
            # '00080056',  # Instance Availability**
            '00080061',  # Modalities in Study**
            '00080090',  # Referring Physician's Name
            '00080201',  # Timezone Offset From UTC**
            # '00081190',  # Retrieve URL**
            '00100010',  # Patient's Name
            '00100020',  # Patient ID
            '00100030',  # Patient's Birth Date
            '00100040',  # Patient's Sex
            '0020000D',  # Study Instance UID
            '00200010',  # Study ID
            '00201206',  # Number of Study Related Series**
            '00201208'   # Number of Study Related Instances**
        ]

        # Validate include fields, add to list of attributes to return
        if includeFields:
            stringTags = parseIncludeFields(includeFields)
            if stringTags:
                attributesToReturn.extend(stringTags)

        # Build fields dictionary
        fields = {}
        for attribute in attributesToReturn:
            fields['meta.' + attribute] = True

        # Query documents, include requested fields
        cursor = self.model('item').find(query, fields=fields)

        # Return one document per study
        results = getUniqueStudies(cursor)

        # Apply limit and offset
        endIndex = offset + limit if limit else None
        results = list(itertools.islice(results, offset, endIndex))

        # Return 204 (No Content) response if there were no matches
        #
        # See: 6.7.1.2 Response
        if not results:
            cherrypy.response.status = 204

        # Add derived attributes:
        #  00080056: Instance Availability
        #    (See: C.4.23.1.1 Instance Availability)
        #  00081190: Retrieve URL
        #
        # See: C.3.4 Additional Query/Retrieve Attributes
        for result in results:
            result.update(dataElementToJSON(
                DataElement((0x0008, 0x0056), 'CS', 'ONLINE')))
            # XXX: add WADO-RS URL to retrieve resource
            result.update(dataElementToJSON(
                DataElement((0x0008, 0x1190), 'UR', '')))

        # XXX: sort tags
        # See: F.2.2 DICOM JSON Model Object Structure:
        #
        #    Attribute objects within a DICOM JSON Model object must be ordered
        #    by their property name in ascending order.

        return results

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
