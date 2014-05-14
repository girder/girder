#!/usr/bin/env python
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

import json

from tests import base

from server.features import Base


def setUpModule():
    base.enabledPlugins.append('geoJSON')
    base.startServer()


def tearDownModule():
    base.stopServer()


items = {
    'item1': {
        'description': 'description1',
        'meta': {
            'lat': 1,
            'lon': 2,
            'latitude': 3,
            'longitude': 4,
            'coord': {
                'lat': 5,
                'lon': 6
            },
            'pt': [7, 8]
        },
        'private': {
            'lat': 9,
            'lon': 10
        }
    },
    'item2': {
        'description': 'description2',
        'meta': {
            'lat': 11,
            'lon': 12,
            'latitude': 13,
            'longitude': 14,
            'coord': {
                'lat': 15,
                'lon': 16
            },
            'pt': [17, 18]
        },
        'private': {
            'lat': 19,
            'lon': 20
        }
    }
}


class PointsTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.user = self.model('user').createUser(
            email='me@mail.com',
            login='admin',
            firstName='first',
            lastName='last',
            password='password',
            admin=True
        )

        resp = self.request(
            path='/folder',
            method='GET',
            params={
                'parentType': 'user',
                'parentId': self.user['_id']
            }
        )
        self.assertStatusOk(resp)
        self.folderId = resp.json[0]['_id']

        for name in items:
            item = items[name]
            resp = self.request(
                path='/item',
                method='POST',
                params={
                    'name': name,
                    'description': item['description'],
                    'folderId': self.folderId
                },
                user=self.user
            )
            self.assertStatusOk(resp)

            resp = self.request(
                path='/item/{}/metadata'.format(resp.json['_id']),
                method='PUT',
                user=self.user,
                body=json.dumps(item['meta']),
                type='application/json'
            )
            self.assertStatusOk(resp)

            doc = self.model('item').load(resp.json['_id'], force=True)
            doc['private'] = item['private']
            self.model('item').save(doc)

    def _testGet(self, latitude, longitude):

        resp = self.request(
            path='/geojson/points',
            params={
                'q': json.dumps({
                    'folderId': {
                        '$oid': self.folderId
                    }
                }),
                'latitude': 'meta.' + str(latitude),
                'longitude': 'meta.' + str(longitude)
            }
        )
        self.assertStatusOk(resp)

        for feature in resp.json['features']:
            prop = feature['properties']
            name = prop['name']

            meta = dict(items[name]['meta'])
            meta['name'] = name
            meta['description'] = items[name]['description']
            meta['_id'] = prop['_id']

            self.assertEqual(meta, prop)

            lon, lat = feature['geometry']['coordinates']
            self.assertEqual(lon, Base.get(longitude, meta))
            self.assertEqual(lat, Base.get(latitude, meta))

    def testPointGet(self):
        self._testGet('latitude', 'longitude')
        self._testGet('lat', 'lon')
        self._testGet('coord.lat', 'coord.lon')
        self._testGet('pt.1', 'pt.0')

    def testInvalidAccessor(self):

        resp = self.request(
            path='/geojson/points',
            params={
                'q': json.dumps({
                    'folderId': {
                        '$oid': self.folderId
                    }
                }),
                'latitude': 'private.lat',
                'longitude': 'private.lon'
            }
        )
        self.assertStatus(resp, 402)

    def testInvalidSpec(self):

        resp = self.request(
            path='/geojson/points',
            params={
                'q': json.dumps({
                    'folderId': {
                        '$oid': self.folderId
                    }
                }),
                'latitude': 'meta.notakey'
            }
        )
        self.assertStatus(resp, 401)
