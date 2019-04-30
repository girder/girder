# -*- coding: utf-8 -*-
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting

from . import constants


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', (), self.getSettings)
        self.route('GET', ('assets',), self.getAssets)

    @access.public
    @autoDescribeRoute(
        Description('Public url for getting the homepage properties.')
    )
    def getSettings(self):
        settings = Setting()
        return {
            constants.PluginSettings.MARKDOWN: settings.get(constants.PluginSettings.MARKDOWN),
            constants.PluginSettings.HEADER: settings.get(constants.PluginSettings.HEADER),
            constants.PluginSettings.SUBHEADER: settings.get(constants.PluginSettings.SUBHEADER),
            constants.PluginSettings.WELCOME_TEXT: settings.get(
                constants.PluginSettings.WELCOME_TEXT),
            constants.PluginSettings.LOGO: settings.get(constants.PluginSettings.LOGO),
        }

    @access.admin
    @autoDescribeRoute(
        Description('Return the folder IDs for uploaded asset content.')
    )
    def getAssets(self):
        return {
            # Keep MARKDOWN folder as 'Homepage Assets', for compatibility
            constants.PluginSettings.MARKDOWN: self._getAssetsFolder('Homepage Assets')['_id'],
            constants.PluginSettings.WELCOME_TEXT: self._getAssetsFolder('Welcome Text')['_id'],
            constants.PluginSettings.LOGO: self._getAssetsFolder('Logo')['_id'],
        }

    def _getAssetsFolder(self, folderName):
        """
        Get or create a public folder, in the private "Homepage Assets" collection.

        This makes the folder effectively "unlisted" as it can't be browsed to by normal users, but
        its content can still be downloaded directly.

        :param folderName: The name of the folder to get or create.
        :return: The new folder document.
        """
        collection = Collection().createCollection(
            constants.COLLECTION_NAME,
            public=False,
            reuseExisting=True
        )
        folder = Folder().createFolder(
            collection,
            folderName,
            parentType='collection',
            public=True,
            reuseExisting=True
        )
        return folder
