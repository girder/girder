"""
Tests for the core.show_download setting.

Since this setting purely drives UI, these tests only ensure validation is correct.
"""
import pytest

from girder.exceptions import ValidationException

from girder.models.setting import Setting
from girder.settings import SettingKey


class TestShowDownloadSetting:
    """Tests for the core.show_download setting validation."""

    def testSettingDefaultIsAll(self, db):
        assert Setting().getDefault(SettingKey.SHOW_DOWNLOAD) == 'all'

    def testSettingValidationValid(self, db):
        test_pairs = [
            ('all', 'all'),
            ('user', 'user'),
            ('admin', 'admin'),
            ('none', 'none'),
            ('ALL', 'all'),
        ]
        for pair in test_pairs:
            Setting().set(SettingKey.SHOW_DOWNLOAD, pair[0])
            assert Setting().get(SettingKey.SHOW_DOWNLOAD) == pair[1]

    def testSettingValidationInvalid(self, db):
        for invalid in [1, True, 'true', None, [], {}]:
            with pytest.raises(ValidationException):
                Setting().set(SettingKey.SHOW_DOWNLOAD, invalid)
