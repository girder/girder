# -*- coding: utf-8 -*-
import unittest.mock
import pytest

from girder import _setupCache
from girder.models.setting import Setting
from girder.settings import SettingKey
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
    with unittest.mock.patch.object(setting, 'findOne') as findOneMock:
        assert setting.get(SettingKey.BRAND_NAME) == 'bar'

        # findOne shouldn't be called since the cache is returning the setting
        findOneMock.assert_not_called()

    # unset the setting, invalidating the cache
    setting.unset(SettingKey.BRAND_NAME)

    # verify the database needs to be accessed to retrieve the setting now
    with unittest.mock.patch.object(setting, 'findOne') as findOneMock:
        setting.get(SettingKey.BRAND_NAME)

        findOneMock.assert_called_once()
