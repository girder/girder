from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.utility.model_importer import ModelImporter
from .constants import PluginSettings


# For more information on adding new resources to the Web API, see:
# http://girder.readthedocs.io/en/latest/plugin-development.html#adding-a-new-resource-type-to-the-web-api
class {{ cookiecutter.plugin_camel_case }}(Resource):
    def __init__(self):
        super({{ cookiecutter.plugin_camel_case }}, self).__init__()
        self.resourceName = '{{ cookiecutter.plugin_name }}'

        self.route('GET', ('item_metadata',), self.getItemMetadata)

    # For more information on adding routes to the Web API, see:
    # http://girder.readthedocs.io/en/latest/plugin-development.html#adding-a-new-route-to-the-web-api
    @access.public
    @autoDescribeRoute(
        Description('Retrieve item metadata value.'))
    def getItemMetadata(self, params):
        settingModel = ModelImporter.model('setting')
        return settingModel.get(PluginSettings.ITEM_METADATA)
