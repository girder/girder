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
        self._indices = []
        self.initialize()

        assert type(self.name) == str

        self.collection = db_connection[db_cfg['database']][self.name]

        assert isinstance(self.collection, pymongo.collection.Collection)
        assert type(self._indices) == list

        [self.collection.ensure_index(index) for index in self._indices]

    def setIndexedFields(self, indices):
        """
        Subclasses should call this with a list of strings representing
        fields that should be indexed in the database if there are any. Otherwise,
        it is not necessary to call this method.
        """
        self._indices = indices

    def initialize(self):
        """
        Subclasses should override this and set the name of the collection as self.name.
        Also, they should set any
        """
        raise Exception('Must override initialize() in %s model'
                        % self.__class__.__name__)

    def find(self, query={}, offset=0, limit=50, sort=None, fields=None):
        """
        Search the collection by a set of parameters.
        @param query The search query (see general MongoDB docs for "find()")
        @param offset The offset into the results
        @param limit Maximum number of documents to return
        @param sort List of (key, direction) pairs specifying the sort order
        @param fields A mask (list of strings) for filtering result documents by key.
        """
        return self.collection.find(spec=query, fields=fields, skip=offset,
                                    limit=limit, sort=sort)

    def save(self, document):
        """
        Create or update a document in the collection
        """
        assert type(document) == dict

        document['_id'] = self.collection.save(document)
        return document

    def delete(self, document):
        """
        Delete an object from the collection; must have its _id set.
        """
        assert type(document) == dict
        assert document.has_key('_id')

        return self.collection.remove({'_id' : document['_id']})

    def load(self, id, objectId=True):
        """
        Fetch a single object from the database using its id.
        @param id The value for searching the _id field.
        @param objectId Whether the id should be coerced to an ObjectId.
        """
        if objectId:
            id = ObjectId(id)
        return self.collection.find_one({'_id' : id})

