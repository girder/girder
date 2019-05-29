# -*- coding: utf-8 -*-
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource
from girder.models.setting import Setting

from .settings import PluginSettings


class Sentry(Resource):
    def __init__(self):
        super(Sentry, self).__init__()
        self.resourceName = 'sentry'
        self.route('GET', ('dsn',), self.getDSN)

    @access.public
    @describeRoute(
        Description('Public url for getting the sentry dsn.')
    )
    def getDSN(self, params):
        dsn = Setting().get(PluginSettings.DSN)
        return {'sentry_dsn': dsn}
