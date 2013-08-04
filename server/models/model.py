from bson.objectid import ObjectId
from . import db_connection, db_cfg

import pymongo

class Model():
    """
    Model base class. Models are responsible for abstracting away the
    persistence layer. Each collection in the database should have its own
    model. Methods that deal with database interaction belong in the
    model layer.
    """

    def __init__(self):
        self.name = None
        self.initialize()

        assert self.name is not None

        self.collection = getattr(getattr(db_connection, db_cfg['database']), self.name)

        assert isinstance(self.collection, pymongo.collection.Collection)

    def initialize(self):
        """
        Subclasses should override this and set the name of the collection as self.name.
        """
        raise Exception('Must override initialize() in %s model'
                        % self.__class__.__name__)

    def find(self, obj):
        """
        Search the collection
        """
        # TODO
        pass

    def save(self, obj):
        """
        Create or update an object in the collection.
        """
        # TODO
        pass

    def delete(self, obj):
        """
        Delete an object from the collection; must have its _id set.
        """
        # TODO
        pass

    def load(self, id):
        """
        Fetch a single object from the database using its id.
        """
        return self.collection.find_one({'_id' : ObjectId(id)})
