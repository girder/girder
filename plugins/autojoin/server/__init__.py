from girder import events

KEY = 'autojoin'


def validateSettings(event):
    if event.info['key'] == KEY:
        event.preventDefault().stopPropagation()


def load(info):
    events.bind('model.setting.validate', 'autojoin', validateSettings)
