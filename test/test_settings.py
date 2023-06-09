import os

from girder.models.setting import Setting
from girder.settings import SettingDefault, SettingKey


def testSettingEnvironmentOverrideJson(db):
    Setting().set(SettingKey.API_KEYS, False)
    assert Setting().get(SettingKey.API_KEYS) is False

    os.environ['GIRDER_SETTING_CORE_API_KEYS'] = 'true'
    assert Setting().get(SettingKey.API_KEYS) is True

    del os.environ['GIRDER_SETTING_CORE_API_KEYS']


def testSettingEnvironmentOverrideString(db):
    assert Setting().get(SettingKey.BRAND_NAME) == SettingDefault.defaults[SettingKey.BRAND_NAME]

    Setting().set(SettingKey.BRAND_NAME, 'db brand name')
    os.environ['GIRDER_SETTING_CORE_BRAND_NAME'] = 'env brand name'
    assert Setting().get(SettingKey.BRAND_NAME) == 'env brand name'

    del os.environ['GIRDER_SETTING_CORE_BRAND_NAME']
    assert Setting().get(SettingKey.BRAND_NAME) == 'db brand name'
