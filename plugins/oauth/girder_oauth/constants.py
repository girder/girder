# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################


# Constants representing the setting keys for this plugin
class PluginSettings(object):
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

    BOX_CLIENT_ID = 'oauth.box_client_id'
    BOX_CLIENT_SECRET = 'oauth.box_client_secret'
