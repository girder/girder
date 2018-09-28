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


class PluginSettings(object):
    LICENSES = 'item_licenses.licenses'


class PluginSettingsDefaults(object):
    defaults = {
        PluginSettings.LICENSES: [
            {
                # Selected open source licenses from:
                # - https://github.com/ufal/public-license-selector/tree/57e31db
                'category': 'Code Licenses',
                'licenses': [
                    {
                        'name': 'Affero General Public License 3 (AGPL-3.0)'
                    },
                    {
                        'name': 'Apache License 2'
                    },
                    {
                        'name': 'The BSD 2-Clause "Simplified" or "FreeBSD" '
                                'License'
                    },
                    {
                        'name': 'The BSD 3-Clause "New" or "Revised" License '
                                '(BSD)'
                    },
                    {
                        'name': 'Common Development and Distribution License '
                                '(CDDL-1.0)'
                    },
                    {
                        'name': 'Eclipse Public License 1.0 (EPL-1.0)'
                    },
                    {
                        'name': 'GNU General Public License 2 or later '
                                '(GPL-2.0)'
                    },
                    {
                        'name': 'GNU General Public License 3 (GPL-3.0)'
                    },
                    {
                        'name': 'GNU Library or "Lesser" General Public '
                                'License 2.1 or later (LGPL-2.1)'
                    },
                    {
                        'name': 'GNU Library or "Lesser" General Public '
                                'License 3.0 (LGPL-3.0)'
                    },
                    {
                        'name': 'The MIT License (MIT)'
                    },
                    {
                        'name': 'Mozilla Public License 2.0'
                    }
                    ]
            },
            {
                # Licenses from:
                # - http://creativecommons.org/licenses/
                #
                # Names match those from:
                # https://github.com/ufal/public-license-selector/tree/57e31db
                'category': 'Content Licenses',
                'licenses': [
                    {
                        'name': 'Public Domain Dedication (CC Zero)'
                    },
                    {
                        'name': 'Creative Commons Attribution (CC-BY)'
                    },
                    {
                        'name': 'Creative Commons Attribution-ShareAlike '
                                '(CC-BY-SA)'
                    },
                    {
                        'name': 'Creative Commons Attribution-NoDerivs '
                                '(CC-BY-ND)'
                    },
                    {
                        'name': 'Creative Commons Attribution-NonCommercial '
                                '(CC-BY-NC)'
                    },
                    {
                        'name': 'Creative Commons Attribution-NonCommercial-'
                                'ShareAlike (CC-BY-NC-SA)'
                    },
                    {
                        'name': 'Creative Commons Attribution-NonCommercial-'
                                'NoDerivs (CC-BY-NC-ND)'
                    },
                    {
                        'name': 'Public Domain Mark (PD)'
                    },
                    {
                        'name': 'All Rights Reserved'
                    }
                    ]
            }
            ]
    }
