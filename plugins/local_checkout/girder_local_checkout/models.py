import datetime

from bson.objectid import ObjectId

from girder.exceptions import ValidationException
from girder.models.model_base import Model


class CheckoutStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETE = 'complete'
    # Not all files could be copied, typically because of insufficient space.
    PARTIAL = 'partial'
    ERROR = 'error'


class Checkout(Model):
    """
    A folder-level checkout: a request that all S3 files within a folder be
    made local until a given expiration time.
    """

    def initialize(self):
        self.name = 'localCheckout'
        self.ensureIndices(['folderId', 'expires'])

    def validate(self, doc):
        for key in ('folderId', 'expires', 'days'):
            if key not in doc:
                raise ValidationException('Field missing.', key)
        return doc

    def createCheckout(self, folder, user, days):
        now = datetime.datetime.now(datetime.timezone.utc)
        return self.save({
            'folderId': folder['_id'],
            'userId': user['_id'] if user else None,
            'days': days,
            'created': now,
            'updated': now,
            'expires': now + datetime.timedelta(days=days),
            'status': CheckoutStatus.PENDING,
            'fileCount': 0,
            'localCount': 0,
            'bytes': 0,
            'message': '',
        })

    def findByFolder(self, folder):
        return self.findOne({'folderId': folder['_id']})


class CheckoutFile(Model):
    """
    A file that currently has a local copy.  This records where the file's
    data originally lived so that the file can be pointed back at it when the
    local copy is removed.
    """

    def initialize(self):
        self.name = 'localCheckoutFile'
        self.ensureIndices([
            ([('fileId', 1)], {'unique': True}),
            'expires',
            'checkoutIds',
            'original.relpath',
        ])

    def validate(self, doc):
        for key in ('fileId', 'original', 'localAssetstoreId', 'expires'):
            if key not in doc:
                raise ValidationException('Field missing.', key)
        return doc

    def findByFile(self, file):
        return self.findOne({'fileId': file['_id']})

    def addCheckout(self, record, checkout):
        """
        Associate a checkout with a file record, extending the record's
        expiration if the checkout lasts longer.
        """
        update = {'$addToSet': {'checkoutIds': checkout['_id']}}
        if checkout['expires'] > record['expires']:
            update['$set'] = {'expires': checkout['expires']}
            record['expires'] = checkout['expires']
        if checkout['_id'] not in record['checkoutIds']:
            record['checkoutIds'].append(checkout['_id'])
        self.update({'_id': record['_id']}, update, multi=False)
        return record

    def computeExpires(self, record):
        """
        Return the latest expiration of any checkout that still covers the
        record, or None if no checkout covers it any more.
        """
        ids = [ObjectId(i) for i in record.get('checkoutIds', [])]
        if not ids:
            return None
        latest = None
        for checkout in Checkout().find({'_id': {'$in': ids}}, fields=['expires']):
            if latest is None or checkout['expires'] > latest:
                latest = checkout['expires']
        return latest
