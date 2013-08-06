import pymongo
import cherrypy

from bson.objectid import ObjectId
from constants import AccessType

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
        Fetch a single object from the databse using its _id field.
        @param id The value for searching the _id field.
        @param [objectId=True] Whether the id(s) should be coerced to ObjectId(s).
        """
        if objectId and type(id) is not ObjectId:
            id = ObjectId(id)
        return self.collection.find_one({'_id' : id})


class AccessControlledModel(Model):
    """
    Any model that has access control requirements should inherit from
    this class. It enforces permission checking in the load() method
    and provides convenient methods for testing and requiring user permissions.
    It also provides methods for setting access control policies on the resource.
    """

    def _hasGroupAccess(self, perms, groupIds, level):
        """
        Private helper method for checking group access.
        """
        for groupAccess in perms:
            if groupAccess['id'] in groupIds and groupAccess['level'] >= level:
                return True

    def _hasUserAccess(self, perms, userId, level):
        """
        Private helper method for checking user-specific access.
        """
        for userAccess in perms:
            if userAccess['id'] == userId and userAccess['level'] >= level:
                return True
        return False

    def _setAccess(self, doc, id, entity, level, save):
        """
        Private helper for setting access on a resource.
        """
        assert entity == 'users' or entity == 'groups'
        if type(id) is not ObjectId:
            id = ObjectId(id)

        if not doc.has_key('access'):
            doc['access'] = {'groups' : [], 'users' : []}
        if not doc['access'].has_key(entity):
            doc['access'][entity] = []

        # First remove any existing permission level for this entity.
        doc['access'][entity][:] = [perm for perm in doc['access'][entity]
                                    if perm['id'] != id]

        # Now add in the new level for this entity unless we are removing access.
        if level is not None:
            doc['access'][entity].append({
                'id' : id,
                'level' : level
                })

        if save:
            doc = self.save(doc)

        return doc

    def setPublic(self, doc, public, save=True):
        """
        Set the flag for public read access on the object.
        @param doc The document to update permissions on.
        @param public Flag for public read access (bool)
        @param [save=True] Whether to save the object to the database afterward.
                           Set this to False if you want to wait to save the
                           document for performance reasons.
        """
        assert type(public) is bool

        doc['public'] = public

        if save:
            doc = self.save(doc)

        return doc

    def setGroupAccess(self, doc, group, level, save=True):
        """
        Set group-level access on the resource.
        @param doc The resource document to set access on.
        @param who The group to grant or remove access to.
        @param level Set to an AccessType or set to None to remove access for the group.
        @param [save=True] Whether to save the object to the database afterward.
                            Set this to False if you want to wait to save the
                            document for performance reasons.
        """
        return self._setAccess(doc, group['_id'], 'groups', level, save)

    def setUserAccess(self, doc, user, level, save=True):
        """
        Set user-level access on the resource.
        @param doc The resource document to set access on.
        @param group The user to grant or remove access to.
        @param level Set to an AccessType or set to None to remove access for the user.
        @param [save=True] Whether to save the object to the database afterward.
                            Set this to False if you want to wait to save the
                            document for performance reasons.
        """
        return self._setAccess(doc, user['_id'], 'users', level, save)

    def hasAccess(self, doc, user=None, level=AccessType.READ):
        """
        This method looks through the object's permission set and determines
        whether the user has the given permission level on the object.
        @param obj The document to check permission on.
        @param user The user to check against.
        @param level The access level
        """
        if user is None:
            # Short-circuit the case of anonymous users
            return level == AccessType.READ and doc.has_key('public') and doc['public'] == True
        elif user['admin']:
            # Short-circuit the case of admins
            return True
        else:
            # Short-circuit the case of public resources
            if level == AccessType.READ and doc.has_key('public') and doc['public'] == True:
                return True

            # If all that fails, descend into real permission checking.
            if doc.has_key('access'):
                perms = doc['access']
                if user.has_key('groups') and perms.has_key('groups') and\
                  self._hasGroupAccess(perms['groups'], user['groups'], level):
                    return True
                elif perms.has_key('users') and\
                  self._hasUserAccess(perms['users'], user['_id'], level):
                    return True

            return False

    def requireAccess(self, doc, user=None, level=AccessType.READ):
        """
        This wrapper just provides a standard way of throwing an
        access denied exception if the access check fails.
        """
        if not self.hasAccess(doc, user, level):
            if level == AccessType.READ:
                perm = 'Read'
            elif level == AccessType.WRITE:
                perm = 'Write'
            else:
                perm = 'Admin'
            raise AccessException("%s access denied for %s." % (perm, self.name))

    def load(self, id, level, user=None, objectId=True, force=False):
        """
        We override Model.load to also do permission checking.
        @param level The required access type for the object
        @param [force=False] If you explicity want to circumvent access
                             checking on this resource, set this to True.
        """
        doc = Model.load(self, id=id, objectId=objectId)

        if not force:
            self.requireAccess(doc, user, level)

        return doc

class AccessException(Exception):
    """
    Represents denial of access to a resource.
    """
    def __init__(self, message):
        # TODO log the error
        Exception.__init__(self, message)
