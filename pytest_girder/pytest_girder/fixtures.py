import cherrypy
import hashlib
import mock
import mongomock
import os
import pytest
import shutil

from .utils import MockSmtpReceiver, request as restRequest


@pytest.fixture(autouse=True)
def bcrypt():
    """
    Mock out bcrypt password hashing to avoid unnecessary testing bottlenecks.
    """
    with mock.patch('bcrypt.hashpw') as hashpw:
        hashpw.side_effect = lambda x, y: x
        yield hashpw


@pytest.fixture
def db(request):
    """
    Require a Mongo test database.

    Provides a Mongo test database named after the requesting test function. Mongo databases are
    created/destroyed based on the URI provided with the --mongo-uri option and tear-down
    semantics are handled by the --drop-db option.
    """
    from girder.models import _dbClients, getDbConnection, pymongo
    from girder.models.model_base import _modelSingletons
    from girder.external import mongodb_proxy

    mockDb = request.config.getoption('--mock-db')
    dbUri = request.config.getoption('--mongo-uri')
    dbName = 'girder_test_%s' % hashlib.md5(request.node.name.encode('utf8')).hexdigest()
    dropDb = request.config.getoption('--drop-db')
    executable_methods = mongodb_proxy.EXECUTABLE_MONGO_METHODS
    realMongoClient = pymongo.MongoClient

    if mockDb:
        mongodb_proxy.EXECUTABLE_MONGO_METHODS = set()
        pymongo.MongoClient = mongomock.MongoClient

    connection = getDbConnection(uri='%s/%s' % (dbUri, dbName), quiet=False)

    # Force getDbConnection from models to return our connection
    _dbClients[(None, None)] = connection

    if dropDb == 'pre':
        connection.drop_database(dbName)

    for model in _modelSingletons:
        model.reconnect()

    yield connection

    if dropDb == 'post':
        connection.drop_database(dbName)

    connection.close()

    if mockDb:
        mongodb_proxy.EXECUTABLE_MONGO_METHODS = executable_methods
        pymongo.MongoClient = realMongoClient


@pytest.fixture
def server(db, request):
    """
    Require a CherryPy embedded server.

    Provides a started CherryPy embedded server with a request method for performing
    local requests against it. Note: this fixture requires the db fixture.
    """
    # The event daemon cannot be restarted since it is a threading.Thread object, however
    # all references to girder.events.daemon are a singular global daemon due to its side
    # effect on import. We have to hack around this by creating a unique event daemon
    # each time we startup the server and assigning it to the global.
    import girder.events
    from girder.constants import ROOT_DIR
    from girder.utility import plugin_utilities
    from girder.utility.server import setup as setupServer

    oldPluginDir = plugin_utilities.getPluginDir

    girder.events.daemon = girder.events.AsyncEventsThread()

    if request.node.get_marker('testPlugins'):
        # Load plugins from the test path
        path = os.path.join(ROOT_DIR, 'tests', 'test_plugins')

        plugin_utilities.getPluginDir = mock.Mock(return_value=path)
        plugins = request.node.get_marker('testPlugins').args[0]
    else:
        plugins = []

    server = setupServer(test=True, plugins=plugins)
    server.request = restRequest

    cherrypy.server.unsubscribe()
    cherrypy.config.update({'environment': 'embedded',
                            'log.screen': False})
    cherrypy.engine.start()

    yield server

    cherrypy.engine.unsubscribe('start', girder.events.daemon.start)
    cherrypy.engine.unsubscribe('stop', girder.events.daemon.stop)
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    cherrypy.tree.apps = {}
    plugin_utilities.getPluginDir = oldPluginDir


@pytest.fixture
def smtp(db, server):
    """
    Provides a mock SMTP server for testing.
    """
    # TODO strictly speaking, this does not depend on the server itself, but does
    # depend on the events daemon, which is currently managed by the server fixture.
    # We should sort this out so that the daemon is its own fixture rather than being
    # started/stopped via the cherrypy server lifecycle.
    from girder.constants import SettingKey
    from girder.models.setting import Setting

    receiver = MockSmtpReceiver()
    receiver.start()

    host, port = receiver.address
    Setting().set(SettingKey.SMTP_HOST, host)
    Setting().set(SettingKey.SMTP_PORT, port)

    yield receiver

    receiver.stop()


@pytest.fixture
def admin(db):
    """
    Require an admin user.

    Provides a user with the admin flag set to True.
    """
    from girder.models.user import User
    u = User().createUser(email='admin@email.com', login='admin', firstName='Admin',
                          lastName='Admin', password='password', admin=True)

    yield u

    User().remove(u)


@pytest.fixture
def user(db, admin):
    """
    Require a user.

    Provides a regular user with no additional privileges. Note this fixture requires
    the admin fixture since an administrative user must exist before a regular user can.
    """
    from girder.models.user import User
    u = User().createUser(email='user@email.com', login='user', firstName='user',
                          lastName='user', password='password', admin=False)

    yield u

    User().remove(u)


@pytest.fixture
def fsAssetstore(db, request):
    """
    Require a filesystem assetstore. Its location will be derived from the test function name.
    """
    from girder.constants import ROOT_DIR
    from girder.models.assetstore import Assetstore

    name = '_'.join((
        request.node.module.__name__,
        request.node.cls.__name__ if request.node.cls else '',
        request.node.name))

    path = os.path.join(ROOT_DIR, 'tests', 'assetstore', name)

    if os.path.isdir(path):
        shutil.rmtree(path)

    yield Assetstore().createFilesystemAssetstore(name=name, root=path)

    if os.path.isdir(path):
        shutil.rmtree(path)


__all__ = ('admin', 'bcrypt', 'db', 'fsAssetstore', 'server', 'user', 'smtp')
