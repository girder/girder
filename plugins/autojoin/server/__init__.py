from girder import events
from girder.utility.model_importer import ModelImporter

def validateSettings(event):
    """
    Allow the autojoin setting key.
    """
    if event.info['key'] == 'autojoin':
        event.preventDefault().stopPropagation()


def userCreated(event):
    """
    Check auto join rules when a new user is created. If a match is found,
    add the user to the group with the specified access level.
    """
    user = event.info
    email = user.get('email').lower()
    rules = ModelImporter.model('setting').get('autojoin', [])
    for rule in rules:
        if rule['pattern'].lower() not in email:
            continue
        group = ModelImporter.model('group').load(rule['groupId'], force=True)
        ModelImporter.model('group').addUser(group, user, rule['level'])


def load(info):
    events.bind('model.setting.validate', 'autojoin', validateSettings)
    events.bind('model.user.save.created', 'autojoin', userCreated)
