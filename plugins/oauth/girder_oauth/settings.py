from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings:
    PROVIDERS_ENABLED = 'oauth.providers_enabled'
    IGNORE_REGISTRATION_POLICY = 'oauth.ignore_registration_policy'

    GOOGLE_CLIENT_ID = 'oauth.google_client_id'
    GOOGLE_CLIENT_SECRET = 'oauth.google_client_secret'

    GLOBUS_CLIENT_ID = 'oauth.globus_client_id'
    GLOBUS_CLIENT_SECRET = 'oauth.globus_client_secret'

    GITHUB_CLIENT_ID = 'oauth.github_client_id'
    GITHUB_CLIENT_SECRET = 'oauth.github_client_secret'

    LINKEDIN_CLIENT_ID = 'oauth.linkedin_client_id'
    LINKEDIN_CLIENT_SECRET = 'oauth.linkedin_client_secret'

    BITBUCKET_CLIENT_ID = 'oauth.bitbucket_client_id'
    BITBUCKET_CLIENT_SECRET = 'oauth.bitbucket_client_secret'

    MICROSOFT_CLIENT_ID = 'oauth.microsoft_client_id'
    MICROSOFT_CLIENT_SECRET = 'oauth.microsoft_client_secret'
    MICROSOFT_TENANT_ID = 'oauth.microsoft_tenant_id'

    BOX_CLIENT_ID = 'oauth.box_client_id'
    BOX_CLIENT_SECRET = 'oauth.box_client_secret'

    CILOGON_CLIENT_ID = 'oauth.cilogon_client_id'
    CILOGON_CLIENT_SECRET = 'oauth.cilogon_client_secret'


@setting_utilities.default(PluginSettings.PROVIDERS_ENABLED)
def _defaultProvidersEnabled():
    return []


@setting_utilities.default(PluginSettings.IGNORE_REGISTRATION_POLICY)
def _defaultIgnoreRegistrationPolicy():
    return False


@setting_utilities.default({
    PluginSettings.GOOGLE_CLIENT_ID,
    PluginSettings.GLOBUS_CLIENT_ID,
    PluginSettings.GITHUB_CLIENT_ID,
    PluginSettings.LINKEDIN_CLIENT_ID,
    PluginSettings.BITBUCKET_CLIENT_ID,
    PluginSettings.MICROSOFT_CLIENT_ID,
    PluginSettings.BOX_CLIENT_ID,
    PluginSettings.CILOGON_CLIENT_ID,
    PluginSettings.GOOGLE_CLIENT_SECRET,
    PluginSettings.GLOBUS_CLIENT_SECRET,
    PluginSettings.GITHUB_CLIENT_SECRET,
    PluginSettings.LINKEDIN_CLIENT_SECRET,
    PluginSettings.BITBUCKET_CLIENT_SECRET,
    PluginSettings.MICROSOFT_CLIENT_SECRET,
    PluginSettings.BOX_CLIENT_SECRET,
    PluginSettings.CILOGON_CLIENT_SECRET,
    PluginSettings.MICROSOFT_TENANT_ID,
})
def _defaultOtherSettings():
    return ''


@setting_utilities.validator(PluginSettings.PROVIDERS_ENABLED)
def _validateProvidersEnabled(doc):
    if not isinstance(doc['value'], (list, tuple)):
        raise ValidationException('The enabled providers must be a list.', 'value')


@setting_utilities.validator(PluginSettings.IGNORE_REGISTRATION_POLICY)
def _validateIgnoreRegistrationPolicy(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('Ignore registration policy setting must be boolean.', 'value')


@setting_utilities.validator({
    PluginSettings.GOOGLE_CLIENT_ID,
    PluginSettings.GLOBUS_CLIENT_ID,
    PluginSettings.GITHUB_CLIENT_ID,
    PluginSettings.LINKEDIN_CLIENT_ID,
    PluginSettings.BITBUCKET_CLIENT_ID,
    PluginSettings.MICROSOFT_CLIENT_ID,
    PluginSettings.BOX_CLIENT_ID,
    PluginSettings.CILOGON_CLIENT_ID,
    PluginSettings.GOOGLE_CLIENT_SECRET,
    PluginSettings.GLOBUS_CLIENT_SECRET,
    PluginSettings.GITHUB_CLIENT_SECRET,
    PluginSettings.LINKEDIN_CLIENT_SECRET,
    PluginSettings.BITBUCKET_CLIENT_SECRET,
    PluginSettings.MICROSOFT_CLIENT_SECRET,
    PluginSettings.BOX_CLIENT_SECRET,
    PluginSettings.CILOGON_CLIENT_SECRET,
    PluginSettings.MICROSOFT_TENANT_ID,
})
def _validateOtherSettings(doc):
    pass
