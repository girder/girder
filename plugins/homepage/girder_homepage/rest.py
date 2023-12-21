from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting

from . import constants
from .settings import PluginSettings


class Homepage(Resource):
    def __init__(self):
        super().__init__()
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
            PluginSettings.MARKDOWN: settings.get(PluginSettings.MARKDOWN),
            PluginSettings.HEADER: settings.get(PluginSettings.HEADER),
            PluginSettings.SUBHEADER: settings.get(PluginSettings.SUBHEADER),
            PluginSettings.WELCOME_TEXT: settings.get(PluginSettings.WELCOME_TEXT),
            PluginSettings.LOGO: settings.get(PluginSettings.LOGO),
        }

    @access.admin
    @autoDescribeRoute(
        Description('Return the folder IDs for uploaded asset content.')
    )
    def getAssets(self):
        return {
            # Keep MARKDOWN folder as 'Homepage Assets', for compatibility
            PluginSettings.MARKDOWN: self._getAssetsFolder('Homepage Assets')['_id'],
            PluginSettings.WELCOME_TEXT: self._getAssetsFolder('Welcome Text')['_id'],
            PluginSettings.LOGO: self._getAssetsFolder('Logo')['_id'],
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
