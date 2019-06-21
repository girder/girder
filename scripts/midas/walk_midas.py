import pydas

MIDAS_URL = 'http://127.0.0.1'
MIDAS_LOGIN = 'user@example.com'
MIDAS_API_KEY = 'API_KEY'

token = pydas.login(email=MIDAS_LOGIN, api_key=MIDAS_API_KEY, url=MIDAS_URL)
mc = pydas.session.communicator


def handle_item(item, bc):
    bc = bc + (item['name'],)
    print('/'.join(bc))


def handle_folder(folder, bc):
    bc = bc + (folder['name'],)
    children = mc.folder_children(token, folder['folder_id'])
    folders = children['folders']
    items = children['items']
    for child in folders:
        handle_folder(child, bc)
    for item in items:
        handle_item(item, bc)


def handle_community(community):
    bc = ('collection', community['name'])
    children = mc.get_community_children(community['community_id'], token)
    folders = children['folders']
    for folder in folders:
        handle_folder(folder, bc)


def handle_user(user):
    bc = ('user', user['email'])
    user_folder = mc.folder_get(token, user['folder_id'])
    children = mc.folder_children(token, user_folder['folder_id'])
    for folder in children['folders']:
        handle_folder(folder, bc)


def main():
    users = mc.list_users(limit=0)
    for user in users:
        handle_user(user)
    communities = mc.list_communities(token)
    for community in communities:
        handle_community(community)


if __name__ == '__main__':
    main()
