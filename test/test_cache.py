#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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
import mock
import pytest

from girder import _setupCache
from girder.constants import SettingKey
from girder.models.setting import Setting
from girder.utility import config
from girder.utility._cache import cache, requestCache


@pytest.fixture
def enabledCache():
    """
    Side effect fixture which enables and sets up predefined caches.
    """
    cfg = config.getConfig()
    cfg['cache']['enabled'] = True
    _setupCache()

    yield

    cfg['cache']['enabled'] = False
    _setupCache()


def testCachesAreAlwaysConfigured():
    assert cache.is_configured is True
    assert requestCache.is_configured is True


def testSettingsCache(db, enabledCache):
    setting = Setting()

    # 'foo' should be cached as the brand name
    setting.set(SettingKey.BRAND_NAME, 'foo')

    # change the brand name bypassing the cache via mongo
    returnedSetting = setting.findOne({'key': SettingKey.BRAND_NAME})
    returnedSetting['value'] = 'bar'

    # verify the cache still gives us the old brand name
    assert setting.get(SettingKey.BRAND_NAME) == 'foo'

    # change the brand name through .set (which updates the cache)
    setting.set(SettingKey.BRAND_NAME, 'bar')

    # verify retrieving gives us the new value
    with mock.patch.object(setting, 'findOne') as findOneMock:
        assert setting.get(SettingKey.BRAND_NAME) == 'bar'

        # findOne shouldn't be called since the cache is returning the setting
        findOneMock.assert_not_called()

    # unset the setting, invalidating the cache
    setting.unset(SettingKey.BRAND_NAME)

    # verify the database needs to be accessed to retrieve the setting now
    with mock.patch.object(setting, 'findOne') as findOneMock:
        setting.get(SettingKey.BRAND_NAME)

        findOneMock.assert_called_once()
