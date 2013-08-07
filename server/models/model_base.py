import cherrypy
import importlib
import pymongo

from bson.objectid import ObjectId
from constants import AccessType

from . import db_cfg, db_connection

class ModelImporter(object):
    """
    Any class that wants to have convenient model importing semantics
    should extend this class.
    """
    def __init__(self):
        self._requiredModels = []

    def requireModels(self, modelList):
        """
        Subclasses should call this to instantiate models members on themselves.
        :param modelList: The list of models that should be instantiated as members.
        For example, if the returned list contains 'user', it will set self.userModel.
        The values in the list should either be strings (e.g. 'user') or if necessary
        due to naming conventions, a 2-tuple of the form ('model_module_name', 'ModelClassName').
        :type modelList: list of str
        """
        assert type(modelList) is list

        for model in modelList:
            if type(model) is str:
                # Default transform is e.g. 'user' -> 'User()'
                modelName = model
                className = model[0].upper() + model[1:]
            elif type(model) is tuple:
                # Custom class name e.g. 'some_thing' -> 'SomeThing()'
                modelName = model[0]
                className = model[1]
            else:
                raise Exception('Required models should be strings or tuples.')

            if hasattr(self, '%sModel' % modelName): # we already have this model
                continue

            try:
                imported = importlib.import_module('models.%s' % modelName)
            except ImportError:
                raise Exception('Could not load model module "%s"' % modelName)

            try:
                constructor = getattr(imported, className)
            except AttributeError:
                raise Exception('Incorrect model class name "%s" for model "%s"' %
                                (className, modelName))
            setattr(self, '%sModel' % modelName, constructor())


class Model(ModelImporter):
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

        if cherrypy.config['server']['mode'] == 'testing':
            dbName = '%s_test' % db_cfg['database']
        else:
            dbName = db_cfg['database']
        self.collection = db_connection[dbName][self.name]

        assert isinstance(self.collection, pymongo.collection.Collection)
        assert type(self._indices) == list

        # TODO maybe this shouldn't be here if it's slow. This ctor gets called a lot.
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
        :param query: The search query (see general MongoDB docs for "find()")
        :type query: dict
        :param offset: The offset into the results
        :type offset: int
        :param limit: Maximum number of documents to return
        :type limit: int
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :param fields: A mask for filtering result documents by key.
        :type fields: List of strings
        :returns: A pymongo database cursor.
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
        :param id: The value for searching the _id field.
        :type id: string or ObjectId
        :param objectId: Whether the id should be coerced to ObjectId type.
        :type objectId: bool
        :returns: The matching document, or None.
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
        :param doc: The document to update permissions on.
        :type doc: dict
        :param public: Flag for public read access.
        :type public: bool
        :param save: Whether to save the object to the database afterward.
                     Set this to False if you want to wait to save the
                     document for performance reasons.
        :type save: bool
        :returns: The updated resource document.
        """
        assert type(public) is bool

        doc['public'] = public

        if save:
            doc = self.save(doc)

        return doc

    def setGroupAccess(self, doc, group, level, save=True):
        """
        Set group-level access on the resource.
        :param doc: The resource document to set access on.
        :type doc: dict
        :param group: The group to grant or remove access to.
        :type group: dict
        :param level: What level of access the group should have. Set to None
                      to remove all access for this group.
        :type level: AccessType or None
        :param save: Whether to save the object to the database afterward.
                     Set this to False if you want to wait to save the
                     document for performance reasons.
        :type save: bool
        :returns: The updated resource document.
        """
        return self._setAccess(doc, group['_id'], 'groups', level, save)

    def setUserAccess(self, doc, user, level, save=True):
        """
        Set user-level access on the resource.
        :param doc: The resource document to set access on.
        :type doc: dict
        :param user: The user to grant or remove access to.
        :type user: dict
        :param level: What level of access the user should have. Set to None
                      to remove all access for this user.
        :type level: AccessType or None
        :param save: Whether to save the object to the database afterward.
                     Set this to False if you want to wait to save the
                     document for performance reasons.
        :type save: bool
        :returns: The modified resource document.
        """
        return self._setAccess(doc, user['_id'], 'users', level, save)

    def hasAccess(self, doc, user=None, level=AccessType.READ):
        """
        This method looks through the object's permission set and determines
        whether the user has the given permission level on the object.
        :param doc: The document to check permission on.
        :type doc: dict
        :param user: The user to check against.
        :type user: dict
        :param level: The access level.
        :type level: AccessType
        :returns: The updated resource document.
        """
        if user is None:
            # Short-circuit the case of anonymous users
            return level == AccessType.READ and doc.get('public', False) == True
        elif user['admin']:
            # Short-circuit the case of admins
            return True
        else:
            # Short-circuit the case of public resources
            if level == AccessType.READ and doc.get('public', False) == True:
                return True

            # If all that fails, descend into real permission checking.
            if doc.has_key('access'):
                perms = doc['access']
                if self._hasGroupAccess(perms.get('groups', []), user.get('groups', []), level):
                    return True
                elif self._hasUserAccess(perms.get('users', []), user['_id'], level):
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

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True, force=False):
        """
        We override Model.load to also do permission checking.
        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicity want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        doc = Model.load(self, id=id, objectId=objectId)

        if not force and doc is not None:
            self.requireAccess(doc, user, level)

        return doc

class AccessException(Exception):
    """
    Represents denial of access to a resource.
    """
    def __init__(self, message):
        # TODO log the error
        Exception.__init__(self, message)

class ValidationException(Exception):
    """
    Represents validation failure in the model layer.
    """
    def __init__(self, message):
        # TODO log the error
        Exception.__init__(self, message)
