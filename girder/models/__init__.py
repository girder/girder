import logging
import pymongo
import pymongo.cursor
import urllib.parse

from girder.utility import config

_dbClients = {}
logger = logging.getLogger(__name__)


if not hasattr(pymongo.cursor.Cursor, 'count'):
    import warnings

    def _cursorCount(self, with_limit_and_skip=False):
        warnings.warn(
            'count is deprecated. Use Collection.count_documents instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        params = {}
        if with_limit_and_skip and getattr(self, '_limit', getattr(self, '_Cursor__limit', None)):
            params['limit'] = getattr(self, '_limit', getattr(self, '_Cursor__limit', None))
        if with_limit_and_skip and getattr(self, '_skip', getattr(self, '_Cursor__skip', None)):
            params['skip'] = getattr(self, '_skip', getattr(self, '_Cursor__skip', None))
        return getattr(self, '_collection', getattr(
            self, '_Cursor__collection', None)).count_documents(
                getattr(self, '_spec', getattr(self, '_Cursor__spec', None)), **params)

    pymongo.cursor.Cursor.count = _cursorCount


def getDbConfig():
    """Get the database configuration values from the cherrypy config."""
    cfg = config.getConfig()
    if 'database' in cfg:
        return cfg['database']
    else:
        return {}


def getDbConnection(uri=None, replicaSet=None, quiet=False, **kwargs):
    """
    Get a MongoClient object that is connected to the configured database.
    We lazy-instantiate a module-level singleton, the MongoClient objects
    manage their own connection pools internally. Any extra kwargs you pass to
    this method will be passed through to the MongoClient.

    :param uri: if specified, connect to this mongo db rather than the one in
                the config.
    :param replicaSet: if uri is specified, use this replica set.
    :param quiet: if true, don't log warnings and success.
    :type quiet: bool
    """
    global _dbClients

    origKey = (uri, replicaSet)
    if origKey in _dbClients:
        return _dbClients[origKey]

    dbConf = getDbConfig()

    if uri is None or uri == '':
        uri = dbConf.get('uri')
        replicaSet = dbConf.get('replica_set')

    clientOptions = {
        # This is the maximum time between when we fetch data from a cursor.
        # If it times out, the cursor is lost and we can't reconnect.  If it
        # isn't set, we have issues with replica sets when the primary goes
        # down.  This value can be overridden in the mongodb uri connection
        # string with the socketTimeoutMS.
        'socketTimeoutMS': 60000,
        'connectTimeoutMS': 20000,
        'serverSelectionTimeoutMS': 20000,
        'readPreference': 'secondaryPreferred',
        'replicaSet': replicaSet,
        'w': 'majority'
    }

    # All other options in the [database] section will be passed directly as
    # options to the mongo client
    for opt, val in dict(dbConf).items():
        if opt not in {'uri', 'replica_set'}:
            clientOptions[opt] = val

    # Finally, kwargs take precedence
    clientOptions.update(kwargs)
    # if the connection URI overrides any option, honor it above our own
    # settings.
    uriParams = urllib.parse.parse_qs(urllib.parse.urlparse(uri).query)
    for key in uriParams:
        if key in clientOptions:
            del clientOptions[key]

    if uri is None:
        dbUriRedacted = 'mongodb://localhost:27017/girder'
        if not quiet:
            logger.warning('WARNING: No MongoDB URI specified, using the default value')

        client = pymongo.MongoClient(dbUriRedacted, **clientOptions)
    else:
        parts = uri.split('@')
        if len(parts) == 2:
            dbUriRedacted = 'mongodb://' + parts[1]
        else:
            dbUriRedacted = uri

        client = pymongo.MongoClient(uri, **clientOptions)

    if not quiet:
        desc = ''
        if replicaSet:
            desc += ', replica set: %s' % replicaSet
        logger.info('Connecting to MongoDB: %s%s', dbUriRedacted, desc)

    # Make sure we can connect to the mongo server at startup
    client.server_info()

    _dbClients[origKey] = _dbClients[(uri, replicaSet)] = client

    return client
