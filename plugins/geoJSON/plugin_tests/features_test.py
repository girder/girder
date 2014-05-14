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

import unittest

from server.features import *


class TestBase(unittest.TestCase):

    def test_map(self):

        base = Base()

        a = base.map(lambda *arg: arg[0], xrange(4))
        self.assertEqual(a, list(xrange(4)))

        a = base.map(lambda *arg: arg[1], xrange(4))
        self.assertEqual(a, list(xrange(4)))

        a = base.map(lambda *arg: arg[0] == arg[2][arg[1]], xrange(4))
        self.assertEqual(a, [True] * 4)

        d = {'a': 0, 'b': '0', 'c': {}}
        a = base.map(lambda *arg: arg[0], d)
        self.assertEqual(sorted(a), ['a', 'b', 'c'])

        a = base.map(lambda *arg: arg[1], d)
        self.assertEqual(a, list(xrange(3)))

        self.assertRaises(
            IteratorException,
            base.map, lambda *arg: arg[0], 1
        )

    def test_get(self):

        base = Base()

        d = {
            'e': 1,
            'c': 10,
            'd': False,
            'k': -1.1,
            'z': 'A string'
        }
        for k in d:
            self.assertEqual(base.get(k, d), d[k])

        l = [1, 10, False, -1.1, 'A string']
        for i in xrange(len(l)):
            self.assertEqual(base.get(i, l), l[i])
            self.assertEqual(base.get(str(i), l), l[i])

        self.assertRaises(
            AccessorException,
            base.get, 'a', l
        )

        self.assertRaises(
            InvalidKeyException,
            base.get, 'not a key', d
        )

        d = {
            'a': {
                'b': {
                    'c': 1,
                    'd': 2
                },
                'c': 10,
                'd': 11
            },
            'b': 20,
            'c': 21,
            'd': 22,
            'aaa': {
                'b': 30,
                'c': 31,
                'd': 32,
                'f': [41, 42, {'1': 50}]
            }
        }
        self.assertEqual(base.get('b', d), 20)
        self.assertEqual(base.get('a.c', d), 10)
        self.assertEqual(base.get('a.b.c', d), 1)
        self.assertEqual(base.get('aaa.b', d), 30)
        self.assertEqual(base.get('aaa.f.1', d), 42)
        self.assertEqual(base.get('aaa.f.2.1', d), 50)
        self.assertEqual(base.get(None, d), d)


class TestPosition(unittest.TestCase):

    def testCall(self):

        pos1 = Position()
        pos2 = Position(longitude='lon', latitude='lat')
        pos3 = Position(longitude='longitude', latitude='latitude')
        pos4 = Position(longitude=2, latitude=1)

        a = (1.4, -10.1)
        self.assertEqual(pos1(a), a)

        o = {'lon': 1.4, 'lat': -10.1}
        self.assertEqual(pos2(o), a)

        o = {'latitude': -10.1, 'longitude': 1.4}
        self.assertEqual(pos3(o), a)

        o = [0, -10.1, 1.4]
        self.assertEqual(pos4(o), a)


class TestGeometryBase(unittest.TestCase):

    def setUp(self):
        self.positions = [
            (0, 0),
            (0, 1),
            (1, 0),
            (1, 1)
        ]
        self.specs = [
            {},
            {'latitude': 'latitude', 'longitude': 'longitude'},
            {'latitude': 'lat', 'longitude': 'lon'}
        ]
        self.meta = {
            'private': [0, 1],
            'a': 'a',
            'b': 2,
            'c': {
                'a': 4,
                'c': [1, 2],
                'zzz': 'a'
            },
            'd': {
                'z': 1
            }
        }
        self.flat = {
            'a': 4,
            'b': 2,
            'c': [1, 2],
            'z': 1,
            'zzz': 'a'
        }
        self.filters = [
            [],
            ['a', 'b', 'c'],
            ['a']
        ]

    def fromSpec(self, spec):
        if spec == {}:
            return self.positions[:]
        return [
            {
                spec['longitude']: p[0],
                spec['latitude']: p[1]
            } for p in self.positions
        ]


class TestPoint(TestGeometryBase):

    def test_point(self):

        for spec in self.specs:

            point = Point(**spec)
            data = self.fromSpec(spec)
            i = 0

            for d in data:
                obj = point(d)

                self.assertEqual(sorted(obj.keys()), ['coordinates', 'type'])
                self.assertEqual(obj['type'], point.typeName)
                self.assertEqual(obj['coordinates'], self.positions[i])
                i += 1


class TestFeatureBase(unittest.TestCase):

    def testFilter(self):

        obj = {
            'a': 1,
            'b': 2,
            'c': 3
        }
        keys = ['a', 'c']
        self.assertEqual(Feature.filter(obj, keys).keys(), keys)

    def testFlat(self):

        obj = {
            'a': 1,
            'b': 2,
            'c': {
                'a': 3,
                'd': 4
            }
        }
        out = {
            'a': 3,
            'b': 2,
            'd': 4
        }
        self.assertEqual(Feature.flat(obj, 'c'), out)


class TestPointFeature(TestGeometryBase):

    def test_pointFeature(self):

        feature1 = PointFeature(latitude='point.1', longitude='point.0')
        feature2 = PointFeature(latitude='y', longitude='x')
        for pt in self.positions:
            inObj = dict(self.meta)
            inObj['point'] = pt

            obj = feature1(inObj)

            self.assertEqual(obj['geometry']['coordinates'], pt)
            self.assertEqual(obj['properties'], inObj)

            inObj = dict(self.meta)
            inObj['y'] = pt[1]
            inObj['x'] = pt[0]

            obj = feature2(inObj)

            self.assertEqual(obj['geometry']['coordinates'], pt)
            self.assertEqual(obj['properties'], inObj)


class TestFeatureCollection(unittest.TestCase):

    def setUp(self):

        self.data = [
            {
                'meta': {
                    'a': 1,
                    'b': 2,
                    'lat': 0,
                    'lon': 0
                },
                'style1': (0, 0),
                'style2': {
                    'x': 0,
                    'y': 0
                }
            },
            {
                'meta': {
                    'a': 3,
                    'b': 4,
                    'lat': 0,
                    'lon': 1
                },
                'style1': (1, 0),
                'style2': {
                    'x': 1,
                    'y': 0
                }
            },
            {
                'meta': {
                    'a': 5,
                    'b': 6,
                    'lat': 1,
                    'lon': 1
                },
                'style1': (1, 1),
                'style2': {
                    'x': 1,
                    'y': 1
                }
            }
        ]
        self.specs = [
            {
                'latitude': 'style1.1',
                'longitude': 'style1.0'
            },
            {
                'latitude': 'style2.y',
                'longitude': 'style2.x'
            },
            {
                'latitude': 'meta.lat',
                'longitude': 'meta.lon'
            }
        ]

    def testEmptyFeature(self):
        coll = FeatureCollection()
        self.assertEqual(coll(), {
            'type': coll.typeName,
            'features': []
        })

    def testBasicPoints(self):
        data = self.data[:]
        out = None
        for spec in self.specs:
            spec = dict(spec)
            spec['type'] = 'point'
            coll = FeatureCollection(points=spec)
            obj = coll(points=data)

            if out is None:
                self.assertEqual(len(obj['features']), len(data))
                for i, feature in enumerate(obj['features']):
                    self.assertEqual(feature['properties'], data[i])
                out = obj
            else:
                self.assertEqual(obj, out)

    def testCustomPoints(self):
        data = self.data[:]
        out = None
        for spec in self.specs:
            spec = dict(spec)
            spec['type'] = 'point'
            spec['flatten'] = ['meta']
            spec['keys'] = ['meta']
            coll = FeatureCollection(points=spec)
            obj = coll(points=data)

            if out is None:
                self.assertEqual(len(obj['features']), len(data))
                for i, feature in enumerate(obj['features']):
                    self.assertEqual(feature['properties'], data[i]['meta'])
                out = obj
            else:
                self.assertEqual(obj, out)


if __name__ == '__main__':
    unittest.main()
