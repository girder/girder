import pymongo
import six

from girder.utility.model_importer import ModelImporter


class Record(dict):
    def __init__(self, modelName, plugin='_core', data=None, dirty=False):
        """
        This class represents a document in the database. This class inherits
        from ``dict`` and can be interacted with as such.

        :param modelName: The model that represents the collection that stores
            this document.
        :type modelName: str
        :param plugin: If this is part of a plugin, pass the plugin name.
        :type plugin: str
        :param data: Initial data to set on the record.
        :type data: dict or None
        :param dirty: Whether this document has outstanding changes that have
            not been persisted to the database.
        :type dirty: bool
        """
        dict.__init__(self, data or {})

        self.modelName = modelName
        self.plugin = plugin
        self.clearChanges()
        self._dirty = dirty
        self._model = None

    def clearChanges(self):
        self._changes = {
            'updated': {},
            'new': {},
            'removed': {}
        }

    @property
    def model(self):
        """
        Lazy loader for the model singleton that represents the collection for
        this record type.
        """
        if self._model is None:
            self._model = ModelImporter.model(self.modelName, self.plugin)
        return self._model

    @property
    def dirty(self):
        """
        Return whether or not this record is dirty (i.e. needs to be saved).
        """
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        self._dirty = value

    def save(self, *args, **kwargs):
        """
        Convenient alias for calling the model's ``save`` method on this record.
        All args and kwargs are the same.
        """
        if self.dirty:
            self.model.save(self, *args, **kwargs)
        return self

    def __setitem__(self, key, value):
        """
        Override the underlying dict's ``__setitem__`` method in order to allow
        minimal updates when persisting.
        """
        if key in self:
            if self[key] == value:
                return  # do not update, key is unchanged.
            self._changes['updated'][key] = True
            self.dirty = True
        else:
            self._changes['new'][key] = True
            self.dirty = True

        return dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self.dirty = True
        self._changes['removed'][key] = True
        return dict.__delitem__(self, key)

    def update(self, *args, **kwargs):
        """
        The normal ``dict.update`` does not internally call __setitem__, so we
        override it to do so. This method supports all the same argument and
        kwarg behaviors as ``dict.update``.
        """
        if args:
            if isinstance(args[0], dict):  # another dict
                for k, v in six.viewitems(args[0]):
                    self[k] = v
            else:  # iterable of pairs
                for k, v in iter(args[0]):
                    self[k] = v
        for k, v in six.viewitems(kwargs):  # kwargs
            self[k] = v

    def filter(self, *args, **kwargs):
        """
        Convenient alias for calling the model's ``filter`` method on this
        record. All args and kwargs are the same.
        """
        return self.model.filter(self, *args, **kwargs)


class RecordCursor(pymongo.cursor.Cursor):
    def __init__(self, modelName, plugin='_core', *args, **kwargs):
        """
        Wraps a ``pymongo.cursor.Cursor`` object so that documents returned
        from the cursor will be ``Record`` objects rather than raw dictionaries.
        All args and kwargs other than `modelName` and `plugin` are passed
        through to the underlying Cursor.

        :param modelName: The modelName field to use for returned Records.
        :type modelName: str
        :param plugin: The plugin field to use for returned Records.
        :type plugin: str
        """
        super(RecordCursor, self).__init__(*args, **kwargs)
        self.modelName = modelName
        self.plugin = plugin

    def __getitem__(self, index):
        """
        Pymongo's Cursor.__getitem__ can return either a single document as a
        dict, or a modified version of itself if a slice is being applied.
        """
        val = super(RecordCursor, self).__getitem__(index)
        if isinstance(val, dict):
            return Record(self.modelName, self.plugin, val)
        return val

    def next(self):
        """
        Overrides the iterator to return ``Record`` objects instead of raw
        dictionaries.
        """
        return Record(self.modelName, self.plugin,
                      super(RecordCursor, self).next())
