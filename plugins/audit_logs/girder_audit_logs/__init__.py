import cherrypy
import datetime
import logging
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
