from girder.utility import setting_utilities


class PluginSettings:
    DEFAULT_IMAGE = 'gravatar.default_image'


@setting_utilities.default(PluginSettings.DEFAULT_IMAGE)
def _defaultDefaultImage():
    return 'identicon'


@setting_utilities.validator(PluginSettings.DEFAULT_IMAGE)
def _validateDefaultImage(doc):
    # TODO should we update user collection to remove gravatar_baseUrl vals?
    pass
