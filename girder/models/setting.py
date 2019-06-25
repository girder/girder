# -*- coding: utf-8 -*-
import pymongo

from .model_base import Model
from girder import logprint
from girder.exceptions import ValidationException
from girder.settings import SettingDefault
from girder.utility import setting_utilities
from girder.utility._cache import cache


class Setting(Model):
    """
    This model represents server-wide configuration settings as key/value pairs.
    """

    def initialize(self):
        self.name = 'setting'
        # We had been asking for an index on key, like so:
        #   self.ensureIndices(['key'])
        # We really want the index to be unique, which could be done:
        #   self.ensureIndices([('key', {'unique': True})])
        # We can't do it here, as we have to update and correct older installs,
        # so this is handled in the reconnect method.

    def reconnect(self):
        """
        Reconnect to the database and rebuild indices if necessary.  If a
        unique index on key does not exist, make one, first discarding any
        extant index on key and removing duplicate keys if necessary.
        """
        super(Setting, self).reconnect()
        try:
            indices = self.collection.index_information()
        except pymongo.errors.OperationFailure:
            indices = []
        hasUniqueKeyIndex = False
        presentKeyIndices = []
        for index in indices:
            if indices[index]['key'][0][0] == 'key':
                if indices[index].get('unique'):
                    hasUniqueKeyIndex = True
                    break
                presentKeyIndices.append(index)
        if not hasUniqueKeyIndex:
            for index in presentKeyIndices:
                self.collection.drop_index(index)
            duplicates = self.collection.aggregate([{
                '$group': {'_id': '$key',
                           'key': {'$first': '$key'},
                           'ids': {'$addToSet': '$_id'},
                           'count': {'$sum': 1}}}, {
                '$match': {'count': {'$gt': 1}}}])
            for duplicate in duplicates:
                logprint.warning(
                    'Removing duplicate setting with key %s.' % (
                        duplicate['key']))
                # Remove all of the duplicates.  Keep the item with the lowest
                # id in Mongo.
                for duplicateId in sorted(duplicate['ids'])[1:]:
                    self.collection.delete_one({'_id': duplicateId})
            self.collection.create_index('key', unique=True)

    def validate(self, doc):
        """
        This method is in charge of validating that the setting key is a valid
        key, and that for that key, the provided value is valid. It first
        allows plugins to validate the setting, but if none of them can, it
        assumes it is a core setting and does the validation here.
        """
        key = doc['key']
        validator = setting_utilities.getValidator(key)
        if validator:
            validator(doc)
        else:
            raise ValidationException('Invalid setting key "%s".' % key, 'key')

        return doc

    @cache.cache_on_arguments()
    def _get(self, key):
        """
        This method is so built in caching decorators can be used without specifying
        custom logic for dealing with the default kwarg of self.get.
        """
        return self.findOne({'key': key})

    def get(self, key):
        """
        Retrieve a setting by its key.

        :param key: The key identifying the setting.
        :type key: str
        """
        setting = self._get(key)

        if setting is None:
            return self.getDefault(key)
        else:
            return setting['value']

    def set(self, key, value):
        """
        Save a setting. If a setting for this key already exists, this will
        replace the existing value.

        :param key: The key identifying the setting.
        :type key: str
        :param value: The object to store for this setting.
        :returns: The document representing the saved Setting.
        """
        setting = self.findOne({'key': key})
        if setting is None:
            setting = {
                'key': key,
                'value': value
            }
        else:
            setting['value'] = value

        setting = self.save(setting)

        self._get.set(setting, self, key)

        return setting

    def unset(self, key):
        """
        Remove the setting for this key. If no such setting exists, this is
        a no-op.

        :param key: The key identifying the setting to be removed.
        :type key: str
        """
        self._get.invalidate(self, key)
        for setting in self.find({'key': key}):
            self.remove(setting)

    def getDefault(self, key):
        """
        Retrieve the system default for a value.

        :param key: The key identifying the setting.
        :type key: str
        :returns: The default value if the key is present in both SettingKey
            and referenced in SettingDefault; otherwise None.
        """
        if key in SettingDefault.defaults:
            return SettingDefault.defaults[key]
        else:
            fn = setting_utilities.getDefaultFunction(key)

            if callable(fn):
                return fn()
        return None
