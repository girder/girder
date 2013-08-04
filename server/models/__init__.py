import pymongo
import cherrypy
from bson.objectid import ObjectId

# We setup our global database connection
db_cfg = cherrypy.config['database']

if db_cfg['user'] == '':
    _db_uri = 'mongodb://%s:%d' % (db_cfg['host'], db_cfg['port'])
    _db_uri_redacted = _db_uri
else:
    _db_uri = 'mongodb://%s:%s@%s:%d' % (db_cfg['user'], db_cfg['password'],
                                         db_cfg['host'], db_cfg['port'])
    _db_uri_redacted = 'mongodb://%s@%s:%d' % (db_cfg['user'],
                                               db_cfg['host'], db_cfg['port'])

db_connection = pymongo.MongoClient(_db_uri)

print "Connected to MongoDB: %s" % _db_uri_redacted

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

        self.collection = db_connection[db_cfg['database']][self.name]

        assert isinstance(self.collection, pymongo.collection.Collection)

    def initialize(self):
        """
        Subclasses should override this and set the name of the collection as self.name.
        """
        raise Exception('Must override initialize() in %s model'
                        % self.__class__.__name__)

    def find(self, params = None, offset = 0, limit = 50):
        """
        Search the collection by a set of parameters.
        """
        # TODO
        pass

    def save(self, obj):
        """
        Create or update an object in the collection. If obj is a list,
        inserts all of the documents. If it is a single record, simply calls save()
        to either update or insert.
        """
        if type(obj) == list:
            return self.collection.insert(obj)
        elif type(obj) == dict:
            return self.collection.save(obj)
        else:
            raise Exception('Model.save() should be passed a list or dict.')

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

