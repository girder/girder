"""
Tests for the core.ui_style and core.ui_header_nav_label settings.

These settings drive the look of the web client. They are validated on the
server and exposed through the public settings endpoint, which is what the
client reads at startup to pick a style.
"""
import pytest

from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.settings import SettingKey
from pytest_girder.assertions import assertStatusOk


class TestUiStyleSetting:
    def testSettingDefaultIsClassic(self, db):
        assert Setting().getDefault(SettingKey.UI_STYLE) == 'classic'
        assert Setting().get(SettingKey.UI_STYLE) == 'classic'

    def testSettingValidationValid(self, db):
        for value, expected in [
            ('classic', 'classic'),
            ('htk', 'htk'),
            ('HTK', 'htk'),
            ('Classic', 'classic'),
        ]:
            Setting().set(SettingKey.UI_STYLE, value)
            assert Setting().get(SettingKey.UI_STYLE) == expected

    def testSettingValidationInvalid(self, db):
        for invalid in [1, True, 'modern', '', None, [], {}]:
            with pytest.raises(ValidationException):
                Setting().set(SettingKey.UI_STYLE, invalid)


class TestUiHeaderNavLabelSetting:
    def testSettingDefaultIsBlank(self, db):
        assert Setting().getDefault(SettingKey.UI_HEADER_NAV_LABEL) == ''
        assert Setting().get(SettingKey.UI_HEADER_NAV_LABEL) == ''

    def testSettingValidationValid(self, db):
        for value, expected in [
            ('Image Explorer', 'Image Explorer'),
            ('  Browse  ', 'Browse'),
            ('', ''),
        ]:
            Setting().set(SettingKey.UI_HEADER_NAV_LABEL, value)
            assert Setting().get(SettingKey.UI_HEADER_NAV_LABEL) == expected

    def testSettingValidationInvalid(self, db):
        for invalid in [1, True, None, [], {}]:
            with pytest.raises(ValidationException):
                Setting().set(SettingKey.UI_HEADER_NAV_LABEL, invalid)


def testUiSettingsArePublic(server):
    resp = server.request(path='/system/public_settings', method='GET')
    assertStatusOk(resp)
    assert resp.json[SettingKey.UI_STYLE] == 'classic'
    assert resp.json[SettingKey.UI_HEADER_NAV_LABEL] == ''

    Setting().set(SettingKey.UI_STYLE, 'htk')
    Setting().set(SettingKey.UI_HEADER_NAV_LABEL, 'Browse')
    resp = server.request(path='/system/public_settings', method='GET')
    assertStatusOk(resp)
    assert resp.json[SettingKey.UI_STYLE] == 'htk'
    assert resp.json[SettingKey.UI_HEADER_NAV_LABEL] == 'Browse'
