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
        self.route('GET', ('dsn',), self._getDsn)

    @access.public
    @describeRoute(
        Description('Public URL for getting the Sentry DSN.')
    )
    def _getDsn(self, params):
        dsn = Setting().get(PluginSettings.FRONTEND_DSN)
        return {'sentry_dsn': dsn}
