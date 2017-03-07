#!/usr/bin/env python
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
class PluginSettings:
    PROVIDERS_ENABLED = 'oauth.providers_enabled'

    GOOGLE_CLIENT_ID = 'oauth.google_client_id'
    GOOGLE_CLIENT_SECRET = 'oauth.google_client_secret'
    GOOGLE_STORE_TOKEN = 'oauth.google_store_token'

    GLOBUS_CLIENT_ID = 'oauth.globus_client_id'
    GLOBUS_CLIENT_SECRET = 'oauth.globus_client_secret'
    GLOBUS_STORE_TOKEN = 'oauth.globus_store_token'

    GITHUB_CLIENT_ID = 'oauth.github_client_id'
    GITHUB_CLIENT_SECRET = 'oauth.github_client_secret'
    GITHUB_STORE_TOKEN = 'oauth.github_store_token'

    LINKEDIN_CLIENT_ID = 'oauth.linkedin_client_id'
    LINKEDIN_CLIENT_SECRET = 'oauth.linkedin_client_secret'
    LINKEDIN_STORE_TOKEN = 'oauth.linkedin_store_token'

    BITBUCKET_CLIENT_ID = 'oauth.bitbucket_client_id'
    BITBUCKET_CLIENT_SECRET = 'oauth.bitbucket_client_secret'
    BITBUCKET_STORE_TOKEN = 'oauth.bitbucket_store_token'

    BOX_CLIENT_ID = 'oauth.box_client_id'
    BOX_CLIENT_SECRET = 'oauth.box_client_secret'
    BOX_STORE_TOKEN = 'oauth.box_store_token'
