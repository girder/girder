import six

from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.file import File
from girder.utility import setting_utilities


class PluginSettings(object):
    MARKDOWN = 'homepage.markdown'

    HEADER = 'homepage.header'
    SUBHEADER = 'homepage.subheader'

    WELCOME_TEXT = 'homepage.welcome_text'

    LOGO = 'homepage.logo'


@setting_utilities.default(PluginSettings.MARKDOWN)
def _defaultMarkdown():
    return ''


@setting_utilities.default(PluginSettings.HEADER)
def _defaultHeader():
    return 'Girder'


@setting_utilities.default(PluginSettings.SUBHEADER)
def _defaultSubheader():
    return 'Data management platform'


@setting_utilities.default(PluginSettings.WELCOME_TEXT)
def _defaultWelcomeText():
    return 'Welcome to Girder!'


@setting_utilities.default(PluginSettings.LOGO)
def _defaultLogo():
    return None


@setting_utilities.validator({
    PluginSettings.MARKDOWN,
    PluginSettings.HEADER,
    PluginSettings.SUBHEADER,
    PluginSettings.WELCOME_TEXT
})
def _validateStrings(doc):
    if not isinstance(doc['value'], six.string_types):
        raise ValidationException('The setting is not a string', 'value')


@setting_utilities.validator(PluginSettings.LOGO)
def _validateLogo(doc):
    try:
        logoFile = File().load(doc['value'], level=AccessType.READ, user=None, exc=True)
    except ValidationException as e:
        # Invalid ObjectId, or non-existent document
        raise ValidationException(str(e), 'value')
    except AccessException:
        raise ValidationException('Logo must be publicly readable', 'value')

    # Store this field natively as an ObjectId
    doc['value'] = logoFile['_id']
