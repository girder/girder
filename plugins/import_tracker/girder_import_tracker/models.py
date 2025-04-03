from datetime import datetime

from bson.objectid import ObjectId

from girder.exceptions import ValidationException
from girder.models.model_base import Model


class AssetstoreImport(Model):
    """A model that tracks assetstore import events."""

    def initialize(self):
        self.name = 'assetstoreImport'

    def validate(self, doc):
        fields = {'name', 'started', 'assetstoreId', 'params'}
        missing_keys = fields - doc.keys()
        if missing_keys:
            raise ValidationException('Fields missing.', ','.join(missing_keys))

        return doc

    def createAssetstoreImport(self, assetstore, params):
        now = datetime.utcnow()
        record = self.save(
            {
                'name': now.isoformat(),
                'started': now,
                'assetstoreId': ObjectId(assetstore['_id']),
                'params': {k: v for k, v in sorted(params.items())},
            }
        )
        return record

    def markEnded(self, record, success=None):
        now = datetime.utcnow()
        record['ended'] = now
        if success is not None:
            record['success'] = success
        record = self.save(record)
        return record


class ImportTrackerCancelError(Exception):
    pass
