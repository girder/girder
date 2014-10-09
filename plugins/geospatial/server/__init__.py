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

from . geospatial import GeospatialItem


def load(info):
    geospatialItem = GeospatialItem()
    info['apiRoot'].item.route('POST', ('geospatial',),
                               geospatialItem.create)
    info['apiRoot'].item.route('GET', ('geospatial',),
                               geospatialItem.find)
    info['apiRoot'].item.route('GET', ('geospatial', 'intersects'),
                               geospatialItem.intersects)
    info['apiRoot'].item.route('GET', ('geospatial', 'near'),
                               geospatialItem.near)
    info['apiRoot'].item.route('GET', ('geospatial', 'within'),
                               geospatialItem.within)
    info['apiRoot'].item.route('GET', (':id', 'geospatial'),
                               geospatialItem.getGeospatial)
    info['apiRoot'].item.route('PUT', (':id', 'geospatial'),
                               geospatialItem.setGeospatial)
