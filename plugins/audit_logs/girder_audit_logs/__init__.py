import cherrypy
import datetime
import logging
import six
from girder import auditLogger
from girder.models.model_base import Model
from girder.api.rest import getCurrentUser
from girder.plugin import GirderPlugin


class Record(Model):
    def initialize(self):
        self.name = 'audit_log_record'

    def validate(self, doc):
        return doc


class _AuditLogDatabaseHandler(logging.Handler):
    def handle(self, record):
        user = getCurrentUser()

        # Null characters may not be stored as MongoDB Object keys
        # RFC3986 technically allows such characters to be encoded in the query string, and 'params'
        # also contains data from form bodies, which may contain arbitrary field names
        if record.msg == 'rest.request' and any(
            '\x00' in paramKey
            for paramKey in six.viewkeys(record.details['params'])
        ):
            record.details['params'] = {
                paramKey.replace('\x00', ''): paramValue
                for paramKey, paramValue in six.viewitems(record.details['params'])
            }

        Record().save({
            'type': record.msg,
            'details': record.details,
            'ip': cherrypy.request.remote.ip,
            'userId': user and user['_id'],
            'when': datetime.datetime.utcnow()
        }, triggerEvents=False)


class AuditLogsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Audit logging'

    def load(self, info):
        auditLogger.addHandler(_AuditLogDatabaseHandler())
