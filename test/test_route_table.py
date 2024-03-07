import pytest

from girder.constants import GIRDER_ROUTE_ID
from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.settings import SettingKey


@pytest.mark.parametrize('value,err', [
    ({}, r'Girder root must be routable\.$'),
    ({'other': '/some_route'}, r'Girder root must be routable\.$'),
    ({
        GIRDER_ROUTE_ID: '/some_route',
        'other': '/some_route'
    }, r'Routes must be unique\.$'),
    ({
        GIRDER_ROUTE_ID: '/',
        'other': 'route_without_a_leading_slash'
    }, r'Routes must begin with a forward slash\.$')
])
def testRouteTableValidationFailure(value, err, db):
    with pytest.raises(ValidationException, match=err):
        Setting().validate({
            'key': SettingKey.ROUTE_TABLE,
            'value': value
        })


@pytest.mark.parametrize('value', [
    {
        GIRDER_ROUTE_ID: '/',
    }
])
def testRouteTableValidationSuccess(value, db):
    Setting().validate({
        'key': SettingKey.ROUTE_TABLE,
        'value': value
    })


@pytest.fixture
def routeTableReconfig(db):
    Setting().set(SettingKey.ROUTE_TABLE, {
        GIRDER_ROUTE_ID: '/',
        'has_webroot': '/has_webroot'
    })
