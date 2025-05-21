import logging

import celery

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import TokenScope
from girder.api.rest import Resource
from girder_worker.app import app

logger = logging.getLogger(__name__)


class Worker(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'worker'
        self.route('GET', ('status',), self.getWorkerStatus)

    @autoDescribeRoute(
        Description('Get worker status and task information.')
        .notes('Return -1 if the broker is inaccessible.')
    )
    @access.user(scope=TokenScope.DATA_READ)
    def getWorkerStatus(self):
        result = {}
        conn = app.connection_for_read()
        try:
            conn.ensure_connection(max_retries=1)
        except celery.exceptions.OperationalError:
            logger.exception(f'Broker ({app.conf.broker_url}) is inaccessible.')
            return -1

        status = app.control.inspect()
        result['report'] = status.report()
        result['stats'] = status.stats()
        result['ping'] = status.ping()
        result['active'] = status.active() or {}
        result['reserved'] = status.reserved() or {}
        return result
