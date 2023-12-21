"""
This script migrates data from Midas to Girder.

It can migrate users, collections (communities in Midas), folders, items and
files (bitstreams in Midas).

It can optionally perform multiple operations in parallel to speed up the
migration (see N_JOBS).

It records its progress to a local SQLite database. If the migration fails for
any reason, it can be restarted and the script will skip entities that have
already been migrated.

Since Midas users do not have a username, only an email address, the script will
generate a username based on the first and last name of the user. When
duplicates exist, or when the username is too short, numbers will be appended.

Users are assigned new passwords that are randomly generated. These are logged
to stdout. The random password generation is seeded with the username so that
multiple runs of the script will generate the same password for a given user.

Large migrations are difficult and take a while. Failures are to be expected.
"""

from functools import wraps
from joblib import Parallel, delayed
import girder_client
import logging
import os
import pydas
import random
import requests
import sqlite3
import string
import tempfile
import threading
import time

# Configuration

MIDAS_URL = 'http://127.0.0.1'
MIDAS_LOGIN = 'user@girder.test'
MIDAS_API_KEY = 'API_KEY'

GIRDER_URL = 'http://127.0.0.1/api/v1'
GIRDER_LOGIN = 'user'
GIRDER_API_KEY = 'API_KEY'

DRY_RUN = False
MIGRATE_USERS = True
MIGRATE_COLLECTIONS = True
MIGRATE_FILES = True
MIGRATE_METADATA = True
MIGRATE_DB = 'migrate.db'
N_JOBS = 4

# Include or exclude specific resources by breadcrumb path
# e.g. 'collection/COPD/Asthma Phantom Images'

TO_MIGRATE = [
]

NOT_TO_MIGRATE = [
]

# Logging configuration

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(message)s',
    datefmt='%H:%M:%S',
)

logger = logging.getLogger('migrate')
logger.setLevel(logging.DEBUG)

# SQLite functions

conn = sqlite3.connect(MIGRATE_DB, check_same_thread=False)
conn.execute(
    'create table if not exists migrated '
    '(type text, id int, primary key (type, id));')
conn.execute(
    'create table if not exists created '
    '(type text, id int, newId text, primary key (type, id));')

db_lock = threading.Lock()


def synchronized(lock):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with lock:
                return f(*args, **kwargs)
        return wrapper
    return decorator


@synchronized(db_lock)
def migrated(type, id):
    cursor = conn.cursor()
    cursor.execute(
        'select 1 from migrated where type = ? and id = ?;', (type, id))
    result = cursor.fetchone() is not None
    if result:
        logger.info('DONE %s %s' % (type, id))
    return result


@synchronized(db_lock)
def set_migrated(type, id):
    conn.execute(
        'insert into migrated (type, id) values (?, ?);', (type, id))
    conn.commit()


@synchronized(db_lock)
def created(type, id):
    cursor = conn.cursor()
    cursor.execute(
        'select newId from created where type = ? and id = ?;', (type, id))
    row = cursor.fetchone()
    return row and {'_id': row[0]}


@synchronized(db_lock)
def set_created(type, id, newId):
    conn.execute(
        'insert into created (type, id, newId) values (?, ?, ?);',
        (type, id, newId))
    conn.commit()


# Helper functions

def delete_default_folders(user):
    folders = gc.listFolder(user['_id'], 'user')
    for folder in folders:
        gc.delete('folder/%s' % folder['_id'])


def generate_login(user, seen):
    for i in range(1000):
        login = '%s.%s' % (user['firstname'], user['lastname'])
        login = login.lower().encode('ascii', 'ignore')
        login = ''.join(x for x in login if x in string.ascii_letters + '.')
        if i:
            login += str(i)
        if len(login) >= 4 and login not in seen:
            break
    return login


def generate_password(length, seed):
    r = random.Random(seed)
    alphabet = string.ascii_letters + string.digits
    return ''.join(r.choice(alphabet) for _ in range(length))


def write_temp_file(iter_content):
    length = 0
    f = tempfile.NamedTemporaryFile(delete=False)
    for chunk in iter_content:
        if chunk:
            f.write(chunk)
            length += len(chunk)
    f.close()
    return f.name, length


def breadcrumb(name, bc, extra=''):
    logger.info('%9s: %s %s' % (name, '/'.join(bc), extra))


def skip(bc):
    bc = '/'.join(bc)
    for item in NOT_TO_MIGRATE:
        if len(bc) < len(item):
            continue
        n = len(item)
        if bc[:n] == item[:n]:
            return True
    if not any(TO_MIGRATE):
        return False
    for item in TO_MIGRATE:
        n = min(len(bc), len(item))
        if bc[:n] == item[:n]:
            return False
    return True


# Migration code

def lookup_resource(bc):
    path = '/' + '/'.join(bc)
    try:
        return gc.resourceLookup(path)
    except requests.HTTPError:
        return None


def get_or_create(type, id, timestamp, bc, func, args):
    newObj = created(type, id)
    if newObj:
        return newObj
    try:
        newObj = func(*args)
    except requests.HTTPError:
        newObj = lookup_resource(bc)
        if not newObj:
            raise
    gc.setResourceTimestamp(newObj['_id'], type, created=timestamp)
    set_created(type, id, newObj['_id'])
    return newObj


def handle_file(item, newItem, bc):
    if migrated('file', item['item_id']):
        return
    n = 3
    for i in range(n):
        path = None
        try:
            filename, iter_content = mc.download_item(item['item_id'], token)
            path, length = write_temp_file(iter_content)
            if not DRY_RUN:
                breadcrumb('File', bc, '[%d bytes]' % length)
                with open(path, 'rb') as f:
                    gc.uploadFile(
                        newItem['_id'], f, filename, length)
            set_migrated('file', item['item_id'])
            return
        except requests.HTTPError as e:
            logger.exception(e.response.text)
            if i == n - 1:
                raise
            breadcrumb('RETRY', bc)
            time.sleep(1)
        finally:
            if path:
                os.remove(path)


def handle_item(item, parent, depth, bc):
    if migrated('item', item['item_id']):
        return
    bc = bc + (item['name'],)
    if skip(bc):
        breadcrumb('SKIP', bc)
        return
    breadcrumb('Item', bc)
    if not DRY_RUN:
        func, args = gc.createItem, (
            parent['_id'],
            item['name'],
            item['description'],
            True,  # reuseExisting
        )
        newItem = get_or_create(
            'item', item['item_id'], item['date_creation'], bc, func, args)
    else:
        newItem = None
    if MIGRATE_FILES:
        handle_file(item, newItem, bc)
    if MIGRATE_METADATA:
        try:
            metadata = mc.get_item_metadata(item['item_id'], token)
        except pydas.exceptions.InvalidPolicy:
            # "The item must have at least one revision to have metadata"
            metadata = None
        if metadata:
            metadata = {x['qualifier']: x['value'] for x in metadata}
            breadcrumb('Metadata', bc, '[%d keys]' % len(metadata))
            if not DRY_RUN:
                gc.addMetadataToItem(newItem['_id'], metadata)
    set_migrated('item', item['item_id'])


def handle_folder(folder, parent, parentType, depth, bc):
    if migrated('folder', folder['folder_id']):
        return
    bc = bc + (folder['name'],)
    if skip(bc):
        breadcrumb('SKIP', bc)
        return
    breadcrumb('Folder', bc)
    if not DRY_RUN:
        func, args = gc.createFolder, (
            parent['_id'],
            folder['name'],
            folder['description'],
            parentType,
            int(folder['privacy_status']) == 0,
        )
        newFolder = get_or_create(
            'folder', folder['folder_id'], folder['date_creation'],
            bc, func, args)
    else:
        newFolder = None
    children = mc.folder_children(token, folder['folder_id'])
    folders = children['folders']
    items = children['items']
    for child in folders:
        handle_folder(child, newFolder, 'folder', depth + 1, bc)
    # create items in parallel
    Parallel(n_jobs=N_JOBS, backend='threading')(
        delayed(handle_item)(item, newFolder, depth + 1, bc) for item in items)
    set_migrated('folder', folder['folder_id'])


def handle_community(community):
    if migrated('community', community['community_id']):
        return
    bc = ('collection', community['name'])
    if skip(bc):
        breadcrumb('SKIP', bc)
        return
    breadcrumb('Community', bc)
    if not DRY_RUN:
        func, args = gc.createCollection, (
            community['name'],
            community['description'],
            int(community['privacy']) == 0,
        )
        newCollection = get_or_create(
            'collection', community['community_id'], community['creation'],
            bc, func, args)
    else:
        newCollection = None
    children = mc.get_community_children(community['community_id'], token)
    folders = children['folders']
    for folder in folders:
        handle_folder(folder, newCollection, 'collection', 1, bc)
    set_migrated('community', community['community_id'])


def handle_user(user, args):
    if migrated('user', user['user_id']):
        return
    bc = ('user', args[0])
    if skip(bc):
        breadcrumb('SKIP', bc)
        return
    breadcrumb('User', bc)
    if not DRY_RUN:
        func = gc.createUser
        newUser = get_or_create(
            'user', user['user_id'], user['creation'], bc, func, args)
    else:
        newUser = None
    user_folder = mc.folder_get(token, user['folder_id'])
    children = mc.folder_children(token, user_folder['folder_id'])
    for folder in children['folders']:
        handle_folder(folder, newUser, 'user', 1, bc)
    set_migrated('user', user['user_id'])


def migrate_users():
    seen = set()
    users = mc.list_users(limit=0)
    to_create = []
    for user in users:
        email = user['email']
        first = user['firstname']
        last = user['lastname']
        password = generate_password(12, email)
        admin = bool(int(user['admin']))
        login = generate_login(user, seen)
        seen.add(login)
        logger.info('%s,%s,%s' % (email, login, password))
        args = (login, email, first, last, password, admin)
        to_create.append((user, args))
    # create users in parallel
    Parallel(n_jobs=N_JOBS, backend='threading')(
        delayed(handle_user)(user, args) for user, args in to_create)


def migrate_collections():
    communities = mc.list_communities(token)
    for community in communities:
        handle_community(community)


def login():
    global token, mc, gc  # TODO - not global
    token = pydas.login(email=MIDAS_LOGIN, api_key=MIDAS_API_KEY, url=MIDAS_URL)
    mc = pydas.session.communicator
    gc = girder_client.GirderClient(apiUrl=GIRDER_URL)
    gc.authenticate(username=GIRDER_LOGIN, apiKey=GIRDER_API_KEY)


def main():
    login()
    if MIGRATE_USERS:
        migrate_users()
    if MIGRATE_COLLECTIONS:
        migrate_collections()


if __name__ == '__main__':
    while True:
        try:
            main()
            break
        except pydas.exceptions.InvalidToken:
            time.sleep(1)
