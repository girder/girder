import girder_client

GIRDER_URL = 'http://127.0.0.1/api/v1'
GIRDER_LOGIN = 'user'
GIRDER_API_KEY = 'API_KEY'

gc = girder_client.GirderClient(apiUrl=GIRDER_URL)
gc.authenticate(username=GIRDER_LOGIN, apiKey=GIRDER_API_KEY)

def handle_item(item, bc):
    bc = bc + (item['name'],)
    print '/'.join(bc)

def handle_folder(folder, bc):
    bc = bc + (folder['name'],)
    folders = gc.listFolder(folder['_id'], 'folder', limit=0)
    items = gc.listItem(folder['_id'], limit=0)
    for child in folders:
        handle_folder(child, bc)
    for item in items:
        handle_item(item, bc)

def handle_collection(collection):
    bc = ('collection', collection['name'])
    folders = gc.listFolder(collection['_id'], 'collection', limit=0)
    for folder in folders:
        handle_folder(folder, bc)

def handle_user(user):
    bc = ('user', user['email'])
    folders = gc.listFolder(user['_id'], 'user', limit=0)
    for folder in folders:
        handle_folder(folder, bc)

def main():
    users = gc.listUser(limit=0)
    for user in users:
        handle_user(user)
    collections = gc.listCollection(limit=0)
    for collection in collections:
        handle_collection(collection)

if __name__ == '__main__':
    main()
