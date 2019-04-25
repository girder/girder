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

from ..constants import AssetstoreType
from ..exceptions import NoAssetstoreAdapter
from .filesystem_assetstore_adapter import FilesystemAssetstoreAdapter
from .gridfs_assetstore_adapter import GridFsAssetstoreAdapter
from .s3_assetstore_adapter import S3AssetstoreAdapter


_assetstoreTable = {
    AssetstoreType.FILESYSTEM: FilesystemAssetstoreAdapter,
    AssetstoreType.GRIDFS: GridFsAssetstoreAdapter,
    AssetstoreType.S3: S3AssetstoreAdapter
}


def getAssetstoreAdapter(assetstore, instance=True):
    """
    This is a factory method that will return the appropriate assetstore adapter
    for the specified assetstore. The returned object will conform to
    the interface of the AbstractAssetstoreAdapter.

    :param assetstore: The assetstore document used to instantiate the adapter.
    :type assetstore: dict
    :param instance: Whether to return an instance of the adapter or the class.
        If you are performing validation, set this to False to avoid throwing
        unwanted exceptions during instantiation.
    :type instance: bool
    :returns: An adapter descending from AbstractAssetstoreAdapter
    """
    storeType = assetstore['type']

    cls = _assetstoreTable.get(storeType)
    if cls is None:
        raise NoAssetstoreAdapter('No AssetstoreAdapter for type: %s.' % storeType)

    if instance:
        return cls(assetstore)
    else:
        return cls


def setAssetstoreAdapter(storeType, cls):

    """
    This updates the internal assetstore adapter table with either a new entry,
    or a modification to an existing entry. Subsequent calls to
    getAssetstoreAdapter() will return the modified class (or instance thereof),
    allowing for dynamic updating of assetstore behavior at runtime.

    :param storeType: The assetstore type to create/modify.
    :type storeType: enum | any
    :param cls: The new assetstore adapter class to install in the table. This
        should be an adapter descending from AbstractAssetstoreAdapter.
    :type cls: AbstractAssetstoreAdapter
    """
    _assetstoreTable[storeType] = cls


def removeAssetstoreAdapter(storeType):
    del _assetstoreTable[storeType]


def fileIndexFields():
    """
    This will return a set of all required index fields from all of the
    different assetstore types.
    """
    return list(set(
        FilesystemAssetstoreAdapter.fileIndexFields() +
        GridFsAssetstoreAdapter.fileIndexFields() +
        S3AssetstoreAdapter.fileIndexFields()
    ))
