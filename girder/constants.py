#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

"""
Constants should be defined here.
"""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AccessType:
    """
    Represents the level of access granted to a user or group on an
    AccessControlledModel. Having a higher access level on a resource also
    confers all of the privileges of the lower levels.

    Semantically, READ access on a resource means that the user can see all
    the information pertaining to the resource, but cannot modify it.

    WRITE access usually means the user can modify aspects of the resource.

    ADMIN access confers total control; the user can delete the resource and
    also manage permissions for other users on it.
    """
    READ = 0
    WRITE = 1
    ADMIN = 2
