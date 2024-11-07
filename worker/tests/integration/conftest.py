import io
import pytest
import requests
import os
from .utilities import GirderSession
from girder_client import GirderClient


def pytest_addoption(parser):
    parser.addoption('--girder', action='store', default='http://127.0.0.1:8989/api/v1/',
                     help='Specify a different server to run against')


@pytest.fixture(scope='module')
def api_url(request):
    return request.config.getoption('--girder')


# TODO: test with admin and non-admin user - are there (should there be)
# differences between girder-worker functionality between the two?
@pytest.fixture(scope='module',
                params=[['admin', 'letmein']],
                ids=['admin'])
def session(request, api_url):
    username, password = request.param
    with GirderSession(base_url=api_url) as s:
        try:
            r = s.get('user/authentication', auth=(username, password))
        except requests.ConnectionError:
            raise Exception(
                'Unable to connect to %s.' % api_url)

        try:
            s.headers['Girder-Token'] = r.json()['authToken']['token']
        except KeyError:
            raise Exception(
                'Unable to login with user "%s", password "%s"' % (username, password))

        yield s


# TODO combine with session in some way?
@pytest.fixture(scope='module',
                params=[['admin', 'letmein']],
                ids=['admin'])
def girder_client(request, api_url):
    username, password = request.param
    client = GirderClient(apiUrl=api_url)
    client.authenticate(username, password)

    yield client


@pytest.fixture(scope='module')
def test_file(tmpdir_factory):
    path = tmpdir_factory.mktemp('test').join('test.txt')
    path.write('abc' * 65546)

    yield str(path)


@pytest.fixture(scope='module')
def private_folder(girder_client):
    me = girder_client.get('user/me')
    try:
        folder = next(
            girder_client.listFolder(
                me['_id'], parentFolderType='user', name='Private'))
    except StopIteration:
        raise Exception("User doesn't have a Private folder.")

    yield folder


@pytest.fixture(scope='module')
def test_file_in_girder(girder_client, private_folder, test_file):
    file = None
    try:
        size = os.path.getsize(test_file)
        with open(test_file) as f:
            file = girder_client.uploadFile(
                private_folder['_id'], f, 'test_file', size, parentType='folder')

        yield file
    finally:
        if file is not None:
            girder_client.delete('item/%s' % file['itemId'])


@pytest.fixture(scope='function')
def test_item(girder_client, private_folder):
    item = None
    try:
        item = girder_client.createItem(private_folder['_id'], 'test')
        yield item
    finally:
        if item is not None:
            girder_client.delete('item/%s' % item['_id'])


@pytest.fixture(scope='function')
def test_multi_file_item(girder_client, test_item):
    for i in range(3):
        girder_client.uploadFile(test_item['_id'], io.BytesIO(), 'test%d.txt' % i, 0)
    yield test_item


@pytest.fixture(scope='function')
def all_writable_tmpdir(tmpdir):
    """
    A temp directory that can be written to by anyone.
    """
    writable = tmpdir.mkdtemp()
    os.chmod(writable.strpath, 0o777)

    yield writable


# pytest hooks for ordering test items after they have been collected
# and ensuring tests marked with sanitycheck run first.
# pytest_runtest_makereport and pytest_runtest_setup are used to xfail
# all tests if any of the sanitychecks fail.
def pytest_collection_modifyitems(items):
    items.sort(key=lambda i: -1 if i.get_closest_marker('sanitycheck') else 1)


def pytest_runtest_makereport(item, call):
    if 'sanitycheck' in item.keywords:
        if call.excinfo is not None:
            session = item.parent.parent
            session._sanitycheckfailed = item


def pytest_runtest_setup(item):
    session = item.parent.parent
    sanitycheckfailed = getattr(session, '_sanitycheckfailed', None)
    if sanitycheckfailed is not None:
        pytest.xfail('previous test failed (%s)' % sanitycheckfailed.name)
