import cherrypy
import pytest

from .utils import request


@pytest.fixture
def db(request):
    """
    Require a Mongo test database.

    Provides a Mongo test database named after the requesting test function. Mongo databases are
    created/destroyed based on the URI provided with the --mongo-uri option and tear-down
    semantics are handled by the --drop-db option.
    """
    from girder.models import _dbClients, getDbConnection
    from girder.models.model_base import _modelSingletons

    dbUri = request.config.getoption('--mongo-uri')
    dbName = 'girder_test_%s' % request.node.name
    dropDb = request.config.getoption('--drop-db')
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


@pytest.fixture
def server(db):
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
    from girder.utility.server import setup as setupServer

    girder.events.daemon = girder.events.AsyncEventsThread()

    server = setupServer(test=True)
    server.request = request

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
