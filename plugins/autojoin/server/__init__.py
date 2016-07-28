from girder import events
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter


@setting_utilities.validator('autojoin')
def validateSettings(doc):
    """
    Allow the autojoin setting key.
    """
    pass  # any value is valid


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
        if group:
            ModelImporter.model('group').addUser(group, user, rule['level'])


def load(info):
    events.bind('model.user.save.created', 'autojoin', userCreated)
