# -*- coding: utf-8 -*-
import pytest

from girder.models.setting import Setting
from girder_sentry.settings import PluginSettings
from pytest_girder.assertions import assertStatusOk

TEST_DSN = 'http://www.foo.bar'
DSN = PluginSettings.DSN


@pytest.mark.plugin('sentry')
def testEmptyInitSentryDSN(server):
    assert Setting().get(DSN) == ''


@pytest.mark.plugin('sentry')
def testSetSentryDSN(server):
    Setting().set(DSN, TEST_DSN)
    assert Setting().get(DSN) == TEST_DSN


@pytest.mark.plugin('sentry')
def testGetSentryDSN(server):
    Setting().set(DSN, TEST_DSN)

    resp = server.request('/sentry/dsn')
    assertStatusOk(resp)
    assert resp.json['sentry_dsn'] == TEST_DSN
