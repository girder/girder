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

"""
This module contains helper classes for transforming arbitrary objects into
geoJSON objects.  The intended usage is to iterate on a mongo cursor to
construct feature collections.  For example, a girder plugin can transform
an item query into a geoJSON object of point features.  Assuming items
are stored as follows:

    {
        "meta": {
            "lat": *,
            "lon": *,
            "someproperty": *
        }
    }

This module can be used as follows with cursor returned by a mongo query
over some girder items:

    >>> pointSpec = { \
            "latitude": "meta.lat", \
            "longitude": "meta.lon", \
            "keys": ["meta"], \
            "flatten": ["meta"] \
        }
    >>> collection = FeatureCollection(myPoints=pointSpec)
    >>> obj = features(myPoints=cursor)

The resulting object will contain an array of point features with properties
set to the item metadata as follows:

    {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        *,
                        *
                    ]
                },
                "type": "Feature",
                "properties": {
                    "lat": *,
                    "lon": *,
                    "someproperty": *
                }
            },
            ...
        ]
    }
"""


class GeoJSONException(Exception):
    """
    Base exception class for all errors raised by this module.
    """
    pass


class IteratorException(GeoJSONException):
    """
    This exception is raised when a method cannot iterate over
    an expected iterable argument.
    """
    pass


class AccessorException(GeoJSONException):
    """
    This exception is raised when an invalid accessor is encountered.
    """
    pass


class InvalidKeyException(GeoJSONException):
    """
    This exception is raised when trying to access an invalid property
    via an accessor.
    """
    pass


class AbstractMethodException(GeoJSONException):
    """
    This exception is raised when an abstract method or class is
    called.
    """
    pass


class BadSpecException(GeoJSONException):
    """
    This exception is raised by a feature class when it is passed
    an invalid spec object.
    """
    pass


class Base(object):
    """
    Base class for all classes in this module.
    """

    def __call__(self, *arg, **kw):  # pragma: no cover
        """
        The call method is used by subclasses to transform
        and argument or iterable into a specific geoJSON
        component.  It must be overriden by subclasses.
        """
        raise AbstractMethodException

    @classmethod
    def map(cls, func, data):
        """
        Call the method `func` on every element of the iterable
        `data`.  Returns a list of the returned results.
        """
        try:
            iter(data)
        except TypeError:
            raise IteratorException(
                "Expected an iterable but got a '%s'" % type(data)
            )
        return [func(d, i, data) for i, d in enumerate(data)]

    @classmethod
    def get(cls, acc, data):
        """
        Get a property of a data elemennt determined by an accessor.

        The data objects should implement the [] operator like a
        `dict` or `list`.

        The accessor can either be a string or an int.  If it is an
        int then `data[acc]` is returned.  If it is a string and
        the data type is a tuple or list, then it is coerced into
        an int.

        The accessor can also reference subobjects by using a '.'
        to seperate keys.  For example:

            >>> Base.get('a.b.1', {'a': {'b': [10, 11]}})
            11
        """
        if acc is None:
            return data
        if isinstance(acc, basestring):
            splt = acc.split('.')
            if len(splt) > 1:
                d = data
                for a in splt:
                    d = cls.get(a, d)
                return d

            if isinstance(data, list) or isinstance(data, tuple):
                try:
                    acc = int(acc)
                except ValueError:
                    pass

        try:
            value = data[acc]
        except TypeError:
            raise AccessorException(
                "Invalid data type '%s' for accessor '%s'" %
                (type(data), acc)
            )
        except (KeyError, IndexError):
            raise InvalidKeyException(
                "Property '%s' not found in data" % str(acc)
            )
        return value


class Position(Base):
    """
    This class formats GIS coordinates into a geoJSON position array.
    """
    def __init__(self, longitude=0, latitude=1, **kw):
        """
        Initialize the Position object with accessors to the longitude
        and latitude.
        """
        self.longitude = longitude
        self.latitude = latitude

    def __call__(self, data):
        """
        Convert an object to a geoJSON position array.
        """
        lon = self.get(self.longitude, data)
        lat = self.get(self.latitude, data)
        return (lon, lat)


# more geoJSON coordinate types to be implemented
class PositionArray(Position):
    """unimplemented"""
    pass


class LinearRing(PositionArray):
    """unimplemented"""
    pass


class MultiPositionArray(PositionArray):
    """unimplemented"""
    pass


class MultiLinearRing(LinearRing):
    """unimplemented"""
    pass


class Geometry(Base):
    """
    Base class for generating geoJSON geometries.
    """
    typeName = None    # geoJSON name for the geometry
    coordinate = None  # coordinate generating class

    def __init__(self, **kw):
        """
        Construct a Geometry object.  Keyword arguments are passed
        to the coordinate class associated with the geometry.
        """
        if self.coordinate is None:  # pragma: no cover
            raise AbstractMethodException

        self.coord = self.coordinate(**kw)

    def __call__(self, d, *args):
        """
        Convert an object into a geoJSON geometry.
        """
        if self.coordinate is None:  # pragma: no cover
            raise AbstractMethodException

        return {
            'coordinates': self.coord(d),
            'type': self.typeName
        }


class Point(Geometry):
    """
    A geoJSON Point geometry generator class.
    """
    typeName = 'Point'
    coordinate = Position


# more geoJSON geometries to be implemented
class LineString(Geometry):
    """unimplemented"""
    pass


class MultiPoint(Geometry):
    """unimplemented"""
    pass


class Polygon(Geometry):
    """unimplemented"""
    pass


class Feature(Base):
    """
    A base class for generating geoJSON features.
    """
    typeName = 'Feature'  # feature type string
    geometry = None       # geometry associated with this feature

    def __init__(self, keys=None, flatten=[], **kw):
        """
        Initialize the feature object.  Extra keyword arguments are passed
        to the associated geometry class.

        :param keys: The keys from the object to add as properties to the
                     geoJSON feature.  If this is parameter is None, then
                     all keys are used.
        :type keys: [str]
        :param flatten: An array of keys that map to objects that will be
                        used to extend the properties.  This is used to
                        flatten hierarchical objects into a single object.
        :type flatten: [str]
        """
        if self.geometry is None:  # pragma: no cover
            raise AbstractMethodException

        self._geometry = self.geometry(**kw)
        self.keys = keys
        self.flatten = flatten

    @classmethod
    def filter(cls, d, keys):
        """
        Return a copy of the object `d` with only the given keys.
        """
        return {k: d[k] for k in d if k in keys}

    @classmethod
    def flat(cls, d, key):
        """
        Remove `key` from `d` and extend it by the dictionary referenced
        by it.
        """
        d.update(d.pop(key, {}))
        return d

    def __call__(self, d, *arg):
        """
        Convert an object into a geoJSON feature.
        """
        if self.geometry is None:  # pragma: no cover
            raise AbstractMethodException

        keys = self.keys
        if keys is None:
            keys = d.keys()
        meta = self.filter(d, keys)

        for key in self.flatten:
            self.flat(meta, key)

        return {
            'type': self.typeName,
            'properties': meta,
            'geometry': self._geometry(d)
        }


class PointFeature(Feature):
    """
    A geoJSON point feature generator class.
    """
    geometry = Point


class FeatureCollection(Base):
    """
    A geoJSON feature collection generator class.
    """
    typeName = 'FeatureCollection'
    features = {  # dictionary of all known feature types
        'point': PointFeature
    }

    @classmethod
    def getFeatureClass(cls, name):
        """
        Get the actual class for a given feature name string.
        """
        try:
            return cls.features[name]
        except KeyError:  # pragma: no cover
            raise InvalidKeyException('Unknown feature type "%s"' % name)

    def __init__(self, **features):
        """
        Initialize a FeatureCollection object.
        :param features: A dictionary of specifications for feature
                         conversions.  Each key represents a named
                         specification that maps to a dictionary of
                         the form {'type': featureType, ...}.
                         Additional values in this dictionary are passed as
                         keyword arguments to the feature constructor.
        :type features: dict
        """
        self._features = {}
        for name in features:
            self.addFeatureSpec(name, features[name])

    def addFeatureSpec(self, name, spec):
        """
        Add a feature specification to the collection.
        """
        spec = dict(spec)
        typeName = spec.pop('type', None)
        featureCls = self.getFeatureClass(typeName)
        self._features[name] = featureCls(**spec)

    def __call__(self, **kw):
        """
        Convert one or more iterables into geoJSON feature collection.
        Iterable datasets should be passed as keyword arguments to
        this method.  The argument name must be a feature defined
        through the constructor or added later by addFeatureSpec.
        """
        features = []

        for specName in kw:
            feature = self._features[specName]
            features.extend(self.map(feature, kw[specName]))

        return {
            'type': self.typeName,
            'features': features
        }
