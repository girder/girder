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

import collections

from .google import Google
from .globus import Globus
from .github import GitHub
from .linkedin import LinkedIn
from .bitbucket import Bitbucket


def addProvider(provider):
    idMap[provider.getProviderName()] = provider

idMap = collections.OrderedDict()


addProvider(Google)
addProvider(Globus)
addProvider(GitHub)
addProvider(LinkedIn)
addProvider(Bitbucket)
