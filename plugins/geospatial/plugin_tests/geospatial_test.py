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

import os.path

import bson.json_util

from server.geospatial import GEOSPATIAL_FIELD
from tests import base
from girder.constants import ROOT_DIR


def setUpModule():
    """
    Enable the geospatial plugin and start the server.
    """
    base.enabledPlugins.append('geospatial')
    base.startServer()


def tearDownModule():
    """
    Stop the server.
    """
    base.stopServer()


class GeospatialItemTestCase(base.TestCase):
    """
    Tests of the geospatial methods added to the API endpoint for items.
    """

    def setUp(self):
        """
        Set up the test case with users and references to public and private
        folders to which to add items with geospatial data.
        """
        super(GeospatialItemTestCase, self).setUp()

        self._creator = self.model('user').createUser(
            'geospatialcreator', 'Nec8xanuguprezaB', 'Geospatial', 'Creator',
            'geospatialcreator@girder.org')
        self._user = self.model('user').createUser(
            'geospatialuser', 'swe2pEpHaheCH7P8', 'Geospatial', 'User',
            'geospatialuser@girder.org')

        folders = self.model('folder').childFolders(
            self._creator, 'user', user=self._creator)
        publicFolders = [folder for folder in folders if folder['public']]
        self.assertIsNotNone(publicFolders)
        self._publicFolder = publicFolders[0]

        folders = self.model('folder').childFolders(
            self._creator, 'user', user=self._creator)
        privateFolders = [folder for folder in folders if not folder['public']]
        self.assertIsNotNone(privateFolders)
        self._privateFolder = privateFolders[0]

    def testGeospatial(self):
        """
        Test the geospatial methods added to the API endpoint for items.
        """
        path = '/item/geospatial'
        self.ensureRequiredParams(path=path, method='POST',
                                  required=['folderId'],
                                  user=self._creator)

        filePath = os.path.join(ROOT_DIR, 'plugins', 'geospatial',
                                'plugin_tests', 'features.geojson')

        with open(filePath, 'r') as f:
            geoJSON = f.read()

        params = {
            'folderId': self._publicFolder['_id'],
            'geoJSON': geoJSON
        }
        features = bson.json_util.loads(geoJSON)['features']
        self.assertEqual(len(features), 3)

        response = self.request(path=path, method='POST', params=params)
        self.assertStatus(response, 401)  # unauthorized

        response = self.request(path=path, method='POST', params=params,
                                user=self._creator)
        self.assertStatusOk(response)
        self._assertHasNames(response.json, ['Chapel Hill', 'Durham',
                                             'Raleigh'])

        for (feature, item) in zip(features, response.json):
            self.assertEqual(feature['geometry'],
                             item[GEOSPATIAL_FIELD]['geometry'])
            properties = feature['properties']
            self.assertEqual(properties['name'], item['name'])
            self.assertEqual(properties['description'], item['description'])
            self.assertEqual(properties['founded'], item['meta']['founded'])

        params['folderId'] = self._privateFolder['_id']
        response = self.request(path=path, method='POST', params=params,
                                user=self._user)
        self.assertStatus(response, 403)  # forbidden, write access denied

        newName = 'RTP'
        newItem = self.model('item').createItem(newName, self._creator,
                                                self._privateFolder)
        path = '/item/%s/geospatial' % newItem['_id']
        newGeometry = {
            'type': 'Point',
            'coordinates': [-78.863640, 35.899168]  # [longitude, latitude]
        }
        body = bson.json_util.dumps({'geometry': newGeometry})

        response = self.request(path=path, method='PUT', body=body,
                                type='application/json')
        self.assertStatus(response, 401)  # unauthorized

        response = self.request(path=path, method='PUT', body=body,
                                type='application/json', user=self._user)
        self.assertStatus(response, 403)  # forbidden, write access denied

        response = self.request(path=path, method='PUT', body=body,
                                type='application/json', user=self._creator)
        self.assertStatusOk(response)
        self.assertEqual(response.json['name'], newName)
        self.assertEqual(response.json[GEOSPATIAL_FIELD]['geometry'],
                         newGeometry)

        response = self.request(path=path, user=self._creator)
        self.assertStatusOk(response)
        self.assertEqual(response.json['name'], newName)
        self.assertEqual(response.json[GEOSPATIAL_FIELD]['geometry'],
                         newGeometry)

        # RDU
        point = {
            'type': 'Point',
            'coordinates': [-78.787996, 35.880079]
        }

        # Triangle
        polygon = {
            'type': 'Polygon',
            'coordinates': [[
                [-79.055844, 35.913200], [-78.898619, 35.994033],
                [-78.638179, 35.779590], [-79.055844, 35.913200]
            ]]  # no interior holes
        }

        path = '/item/geospatial'
        self.ensureRequiredParams(path=path, required=['q'])

        query = {
            'geo.geometry': {
                '$geoWithin': {
                    '$centerSphere': [
                        point['coordinates'],
                        0.0031357119  # radians ~ 20 kilometers
                    ]
                }
            }
        }
        params = {'q': bson.json_util.dumps(query)}
        self._test(path, params,
                   200, ['Durham', 'Raleigh'],
                   200, ['Durham', 'Raleigh', 'RTP'],
                   200, ['Durham', 'Raleigh'])

        path = '/item/geospatial/intersects'
        self.ensureRequiredParams(path=path, required=['field', 'geometry'])

        params = {
            'field': 'geometry',
            'geometry': bson.json_util.dumps(polygon)
        }
        self._test(path, params,
                   200, ['Chapel Hill', 'Durham', 'Raleigh'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh', 'RTP'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh'])

        path = '/item/geospatial/near'
        self.ensureRequiredParams(path=path, required=['field', 'geometry'])

        params = {
            'field': 'geometry',
            'geometry': bson.json_util.dumps(point)
        }
        self._test(path, params,
                   400, [],
                   400, [],
                   400, [])  # bad request, no index on field

        params['ensureIndex'] = True
        self._test(path, params,
                   403, [],  # forbidden, anonymous users cannot create indexes
                   200, ['Chapel Hill', 'Durham', 'Raleigh', 'RTP'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh'])

        del params['ensureIndex']
        self._test(path, params,
                   200, ['Chapel Hill', 'Durham', 'Raleigh'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh', 'RTP'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh'])

        params['minDistance'] = 10000  # meters
        self._test(path, params,
                   200, ['Chapel Hill', 'Durham', 'Raleigh'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh'])

        params['maxDistance'] = 20000  # meters
        self._test(path, params,
                   200, ['Durham', 'Raleigh'],
                   200, ['Durham', 'Raleigh'],
                   200, ['Durham', 'Raleigh'])

        del params['minDistance']
        self._test(path, params,
                   200, ['Durham', 'Raleigh'],
                   200, ['Durham', 'Raleigh', 'RTP'],
                   200, ['Durham', 'Raleigh'])

        path = '/item/geospatial/within'
        self.ensureRequiredParams(path=path, required=['field'])

        params = {
            'field': 'geometry',
            'geometry': bson.json_util.dumps(polygon)
        }
        self._test(path, params,
                   200, ['Chapel Hill', 'Durham', 'Raleigh'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh', 'RTP'],
                   200, ['Chapel Hill', 'Durham', 'Raleigh'])

        params = {
            'field': 'geometry',
            'center': bson.json_util.dumps(point),
            'radius': 20000  # meters
        }
        self._test(path, params,
                   200, ['Durham', 'Raleigh'],
                   200, ['Durham', 'Raleigh', 'RTP'],
                   200, ['Durham', 'Raleigh'])

    def _assertHasNames(self, items, names):
        """
        Helper to assert that items matching a geospatial search are exactly
        those with the given names.

        :param items: items matching a search.
        :type items: list[dict[str, unknown]]
        :param names: names of items that should match the search.
        :type names: list[str]
        """
        self.assertEqual(len(items), len(names))
        names = [item['name'] for item in items]
        self.assertHasKeys(names, names)

    def _test(self, path, params, publicStatus, publicNames, creatorStatus,
              creatorNames, userStatus, userNames):
        """
        Helper to test geospatial methods made by anonymous users, authenticated
        users with permissions to all folders, and authenticated users with
        permissions to only public folders.

        :param path: path of the API method.
        :type path: str
        :param params: parameters to the API call.
        :type params: dict[str, unknown]
        :param publicStatus: HTTP status returned when the API call is made by
                             an anonymous user.
        :type publicStatus: int
        :param publicNames: names of the items that are returned when the API
                            call is made by an anonymous user.
        :type publicNames: list[str]
        :param creatorStatus: HTTP status returned when the API call is made by
                              an authenticated user with permissions to all
                              folders.
        :type creatorStatus: int
        :param creatorNames: names of the items that are returned when the API
                             call is made by an authenticated user with
                             permissions to all folders.
        :type creatorNames: list[str]
        :param userStatus: HTTP status returned when the API call is made by
                           an authenticated user with permissions to only public
                           folders.
        :type userStatus: int
        :param userNames: names of the items that are returned when the API call
                          is made by an authenticated user with permissions to
                          only public folders.
        :type userNames: list[str]
        """
        triples = [(publicStatus, publicNames, None),
                   (creatorStatus, creatorNames, self._creator),
                   (userStatus, userNames, self._user)]

        for (status, names, user) in triples:
            response = self.request(path=path, params=params, user=user)
            self.assertStatus(response, status)

            if status == 200:
                self._assertHasNames(response.json, names)
